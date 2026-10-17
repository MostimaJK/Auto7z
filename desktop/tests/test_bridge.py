"""Real 7-Zip integration except the explicitly labelled cancellation fixture."""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('bridge', ROOT / 'desktop/backend/bridge.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='auto7z-fluent-test-')
        self.path = Path(self.temp.name)
        self.events = []
        self.bridge = bridge.Bridge(self.events.append, self.path / 'config/settings.json')
        self.bridge.settings['path_7z'] = str(ROOT / '7z.exe')
        self.bridge.settings['path_rar'] = ''

    def tearDown(self):
        self.bridge.shutdown()
        self.temp.cleanup()

    def archive(self, name='資料 空格.zip', content=None):
        path = self.path / name
        with zipfile.ZipFile(path, 'w') as z:
            for key, value in (content or {'文件.txt': 'hello'}).items():
                z.writestr(key, value)
        return path

    def add(self, paths, all_files=False):
        self.bridge.add([str(p) for p in paths], all_files)
        self.bridge.thread.join(10)
        self.assertFalse(self.bridge.scanning)

    def run_batch(self, **kwargs):
        self.bridge.start(**kwargs)
        self.bridge.thread.join(20)
        self.assertFalse(self.bridge.busy)

    def test_batch_failure_retry_skips_success_and_preserves_output(self):
        good = self.archive()
        bad = self.path / 'bad.zip'; bad.write_bytes(b'broken')
        self.add([good, bad])
        self.run_batch()
        a, b = self.bridge.rows
        self.assertEqual((a['status'], b['status']), ('success', 'failed'))
        output = a['output']
        self.archive('bad.zip')
        self.run_batch()
        self.assertEqual(a['output'], output)
        self.assertEqual(b['status'], 'success')
        self.assertEqual(self.bridge.total, 1)
        self.assertEqual(self.bridge.completed, 1)

    def test_queue_order_drives_real_execution_and_remove_preserves_files(self):
        self.add([self.archive('first.zip'), self.archive('second.zip'), self.archive('third.zip')])
        ids = [r['id'] for r in self.bridge.rows][::-1]
        self.bridge.dispatch('reorder', {'ids': ids})
        self.events.clear()
        self.run_batch()
        active = [e['data']['current'] for e in self.events if e.get('event') == 'state' and e['data']['current']]
        self.assertEqual(list(dict.fromkeys(active)), ids)
        sources = [Path(r['source']) for r in self.bridge.rows]
        outputs = [Path(r['output']) for r in self.bridge.rows]
        self.bridge.dispatch('remove', {'ids': ids})
        self.assertEqual(self.bridge.rows, [])
        self.assertTrue(all(p.exists() for p in sources + outputs))

    def test_requeue_renamed_file_can_extract_without_losing_result(self):
        self.add([self.archive('disguised.data')], True)
        self.run_batch(mode='rename', extension='.zip')
        row = self.bridge.rows[0]
        renamed = row['archive']
        self.bridge.dispatch('requeue', {'ids': [row['id']]})
        self.assertEqual(row['status'], 'pending')
        self.run_batch(mode='extract')
        output = row['output']
        self.assertEqual(row['status'], 'success', row['detail'])
        self.assertEqual((Path(output) / '文件.txt').read_text(), 'hello')
        self.bridge.dispatch('requeue', {'ids': [row['id']]})
        self.assertEqual(row['archive'], renamed)
        self.assertEqual(row['output'], output)
        self.assertTrue(Path(output).is_dir())

    def test_queue_edits_validate_ids_and_reject_active_jobs(self):
        self.add([self.archive('one.zip'), self.archive('two.zip')])
        ids = [r['id'] for r in self.bridge.rows]
        for invalid in [None, [ids[0]], [ids[0], ids[0]], [ids[0], 'unknown'], [[ids[0]], ids[1]]]:
            with self.assertRaises(ValueError):
                self.bridge.dispatch('reorder', {'ids': invalid})
            self.assertEqual([r['id'] for r in self.bridge.rows], ids)
        with self.assertRaises(ValueError):
            self.bridge.dispatch('requeue', {'ids': ['unknown']})
        self.bridge.busy = True
        try:
            for op in ['reorder', 'remove', 'requeue']:
                with self.assertRaises(ValueError):
                    self.bridge.dispatch(op, {'ids': ids})
        finally:
            self.bridge.busy = False

    def test_restore_partial_retry_uses_renamed_archive(self):
        disguised = self.archive('偽裝.png', {'bad.zip': b'broken'})
        self.add([disguised], True)
        self.run_batch(mode='restore', extension='.zip')
        row = self.bridge.rows[0]
        self.assertEqual(row['status'], 'partial')
        self.assertTrue(Path(row['archive']).is_file())
        previous = row['output']
        self.run_batch(mode='restore', extension='.zip')
        self.assertEqual(row['status'], 'partial')
        self.assertTrue(row['detail'].startswith('bad.zip:'))
        self.assertNotEqual(row['output'], previous)
        self.assertTrue(Path(previous).is_dir())

    def test_folder_scan_dedup_secondary_volumes_and_unicode(self):
        first = self.archive('data.zip.001')
        for name in ('data.zip.002', 'a.part02.rar', 'a.r00', 'a.z01', 'notes.txt'):
            (self.path / name).write_bytes(b'data')
        (self.path / 'a.part01.rar').write_bytes(b'data')
        self.add([self.path, first])
        self.assertEqual({Path(r['source']).name for r in self.bridge.rows}, {'data.zip.001', 'a.part01.rar'})

    def test_actual_split_archive_and_password_candidates(self):
        source = self.path / 'private.txt'; source.write_text('private content' * 1000)
        packed = self.path / 'split.7z'
        subprocess.run([str(ROOT / '7z.exe'), 'a', '-v100b', '-psecret', '-mhe=on', str(packed), str(source)], check=True, stdout=subprocess.DEVNULL)
        self.add([self.path])
        self.run_batch(passwords=['wrong', 'secret'])
        self.assertEqual(len(self.bridge.rows), 1)
        row = self.bridge.rows[0]
        self.assertEqual(row['status'], 'success', row['detail'])
        self.assertEqual((Path(row['output']) / 'private.txt').read_text(), source.read_text())
        self.assertNotIn('secret', json.dumps(self.events))

    def test_rename_collision_preserves_both_files(self):
        source = self.path / 'photo.png'; source.write_bytes(b'keep')
        other = self.path / 'photo.zip'; other.write_bytes(b'other')
        self.add([source], True)
        self.run_batch(mode='rename', extension='.zip')
        self.assertEqual(self.bridge.rows[0]['status'], 'failed')
        self.assertEqual(source.read_bytes(), b'keep')
        self.assertEqual(other.read_bytes(), b'other')

    def test_real_long_path_extraction_and_successful_rename(self):
        folder = self.path
        for i in range(5):
            folder /= ('長路徑' + str(i)) * 12
        folder.mkdir(parents=True)
        source = folder / '中文 長檔名.zip'
        with zipfile.ZipFile(source, 'w') as z:
            z.writestr('result.txt', 'long path')
        self.assertGreater(len(str(source)), 260)
        self.add([source])
        self.run_batch()
        row = self.bridge.rows[0]
        self.assertEqual(row['status'], 'success', row['detail'])
        self.assertEqual((Path(row['output']) / 'result.txt').read_text(), 'long path')
        self.bridge.dispatch('remove', {'ids': [row['id']]})
        disguised = self.path / 'unchanged.data'; disguised.write_bytes(b'keep')
        self.add([disguised], True)
        self.run_batch(mode='rename', extension='.zip')
        self.assertEqual(self.bridge.rows[0]['status'], 'success')
        self.assertEqual(disguised.with_suffix('.zip').read_bytes(), b'keep')

    def test_settings_atomic_separate_and_validation(self):
        self.bridge.dispatch('save', {**self.bridge.settings, 'theme': 'dark'})
        self.assertEqual(json.loads(self.bridge.config.read_text())['theme'], 'dark')
        with self.assertRaises(ValueError):
            self.bridge.dispatch('save', {'max_recursion_depth': 0})
        self.assertEqual(json.loads(self.bridge.config.read_text())['theme'], 'dark')

    def test_tool_metadata_and_path_checks(self):
        reply = self.bridge.dispatch('init', {})
        self.assertTrue(reply['tools']['bundled_7z_exists'])
        self.assertEqual(Path(reply['tools']['bundled_7z']), ROOT / '7z.exe')
        checked = self.bridge.dispatch('check_tools', {'path_7z': str(ROOT / '7z.exe'), 'path_rar': str(self.path / 'missing.exe')})
        self.assertEqual(checked, {'path_7z': True, 'path_rar': False})
        self.assertFalse(self.bridge.dispatch('check_tools', {'path_7z': str(self.path)})['path_7z'])

    def test_custom_and_compound_extension_rename_and_invalid_paths(self):
        source = self.path / 'original.data'; source.write_bytes(b'preserve content')
        self.add([source], True)
        for invalid in ['.zip/../other', '.tar..gz', '.', '.a b']:
            with self.assertRaises(ValueError):
                self.bridge.start(mode='rename', extension=invalid)
            self.assertTrue(source.is_file())
        self.run_batch(mode='rename', extension='.custom7')
        renamed = source.with_suffix('.custom7')
        self.assertEqual(renamed.read_bytes(), b'preserve content')
        self.bridge.dispatch('remove', {'ids': [self.bridge.rows[0]['id']]})
        compound = self.path / 'already.tar.gz'; compound.write_bytes(b'keep')
        self.add([compound], True)
        self.run_batch(mode='rename', extension='.tar.gz')
        self.assertEqual(self.bridge.rows[0]['archive'], str(compound))
        self.assertEqual(compound.read_bytes(), b'keep')

    def test_real_progress_reaches_frontend_events_without_becoming_batch_percent(self):
        source = self.archive('progress.zip', {'data.txt': 'content' * 1000000})
        self.add([source])
        self.run_batch()
        progress = [event['data'] for event in self.events if event.get('event') == 'progress']
        self.assertTrue(any(event['percent'] is not None for event in progress), progress)
        self.assertEqual(self.bridge.completed, 1)
        self.assertEqual(self.bridge.rows[0]['status'], 'success')
        self.assertEqual(self.bridge.state()['progress']['archive'], 'progress.zip')

    def test_element_settings_directory_is_isolated(self):
        with patch.dict(os.environ, {'AUTO7Z_CONFIG_DIR': str(self.path / 'element-settings')}):
            other = bridge.Bridge(self.events.append)
            self.assertEqual(other.config, self.path / 'element-settings/settings.json')
            other.dispatch('save', {**other.settings, 'theme': 'dark'})
            self.assertTrue(other.config.is_file())
            self.assertFalse(self.bridge.config.exists())

    def test_cancellation_fixture_waits_for_real_owned_subprocess(self):
        # Simulated extractor workload, but actual child process/cancellation lifecycle.
        good = self.archive('good.zip')
        slow = self.archive('slow.zip')
        self.add([good, slow])
        original = bridge.Engine.extract
        def extract(engine, source):
            if Path(source).name == 'slow.zip':
                engine._run([sys.executable, '-c', 'import time; time.sleep(30)'])
            return original(engine, source)
        with patch.object(bridge.Engine, 'extract', extract):
            self.bridge.start()
            until = time.time() + 10
            while self.bridge.current != '2' and time.time() < until:
                time.sleep(.02)
            self.bridge.dispatch('cancel', {})
            self.bridge.thread.join(5)
        self.assertFalse(self.bridge.busy)
        self.assertEqual([r['status'] for r in self.bridge.rows], ['success', 'cancelled'])
        self.assertTrue(Path(self.bridge.rows[0]['output']).exists())

    def test_protocol_eof_exits_cleanly(self):
        process = subprocess.run([sys.executable, str(ROOT / 'desktop/backend/bridge.py')],
                                 input=json.dumps({'id': 1, 'op': 'init'})+'\n', text=True, capture_output=True, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        reply = json.loads(process.stdout)
        self.assertTrue(reply['ok'])

    def test_scan_cancellation_keeps_already_added_files(self):
        files = [self.archive(f'file{i}.zip') for i in range(10)]
        def slow_scan(folder, stop=None):
            for path in files:
                time.sleep(.03)
                yield path
        with patch.object(bridge.Bridge, 'walk_files', staticmethod(slow_scan)):
            self.bridge.add([str(self.path)])
            until = time.time() + 5
            while not self.bridge.rows and time.time() < until:
                time.sleep(.01)
            self.bridge.dispatch('cancel', {})
            self.bridge.thread.join(5)
        self.assertFalse(self.bridge.scanning)
        self.assertGreater(len(self.bridge.rows), 0)
        self.assertLess(len(self.bridge.rows), 10)

    def test_protocol_literal_utf8_native_paths(self):
        source = self.archive()
        request = {'id': 7, 'op': 'add', 'args': {'paths': [str(source)]}}
        process = subprocess.Popen([sys.executable, str(ROOT / 'desktop/backend/bridge.py')],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   encoding='utf-8')
        try:
            process.stdin.write(json.dumps(request, ensure_ascii=False)+'\n')
            process.stdin.flush()
            while True:
                message = json.loads(process.stdout.readline())
                if message.get('event') == 'state' and not message['data']['scanning']:
                    self.assertEqual(message['data']['rows'][0]['source'], str(source))
                    break
        finally:
            process.stdin.close()
            process.wait(timeout=10)
            process.stdout.close()
        self.assertEqual(process.returncode, 0)

    @unittest.skipUnless(os.name == 'nt', 'Windows job lifecycle')
    def test_abrupt_backend_exit_kills_only_owned_descendants(self):
        import ctypes
        from ctypes import wintypes as w
        code = (
            f"import sys,subprocess,time; sys.path.insert(0,{str(ROOT / 'desktop/backend')!r}); "
            "from bridge import own_process_job; job=own_process_job(); "
            "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
            "print(child.pid,flush=True); time.sleep(30)"
        )
        owner = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, text=True)
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.restype = w.HANDLE
        api.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        api.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        api.CloseHandle.argtypes = [w.HANDLE]
        child_handle = None
        try:
            pid = int(owner.stdout.readline())
            child_handle = api.OpenProcess(0x00100000, False, pid)
            self.assertTrue(child_handle)
            owner.kill(); owner.wait(timeout=5)
            self.assertEqual(api.WaitForSingleObject(child_handle, 5000), 0)
            self.assertIsNone(unrelated.poll())
        finally:
            if owner.poll() is None:
                owner.kill(); owner.wait()
            owner.stdout.close()
            unrelated.kill(); unrelated.wait()
            if child_handle:
                api.CloseHandle(child_handle)


if __name__ == '__main__':
    unittest.main()

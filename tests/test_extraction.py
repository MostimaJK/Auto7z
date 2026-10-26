import os
import subprocess
import sys
import tempfile
import tarfile
import threading
import time
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path

from extraction import Engine, Cancelled

ROOT = Path(__file__).resolve().parents[1]


WINRAR = next((str(p) for p in (ROOT / "WinRAR.exe", Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "WinRAR/WinRAR.exe") if p.is_file()), "")


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="auto7z-tests-")
        self.folder = Path(self.temp.name)
        self.engine = Engine(str(ROOT / "tools/7zip/7z.exe"), WINRAR)

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, name, contents):
        path = self.folder / name
        with zipfile.ZipFile(path, "w") as archive:
            for key, value in contents.items():
                archive.writestr(key, value)
        return path

    def test_cleanup_options_are_independent_and_preserve_other_files(self):
        import io
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, 'w') as z:
            z.writestr('leaf.txt', 'keep result')
        for delete_inner in (False, True):
            for delete_source in (False, True):
                source = self.archive(f'cleanup-{delete_inner}-{delete_source}.zip', {'nested.zip': inner.getvalue(), 'notes.txt': 'keep me'})
                self.engine.delete_inner = delete_inner
                self.engine.delete_source = delete_source
                result = self.engine.process(source)
                self.assertEqual(result.status, 'success', result.detail)
                self.assertEqual(source.exists(), not delete_source)
                self.assertEqual((Path(result.output) / 'nested.zip').exists(), not delete_inner)
                self.assertEqual((Path(result.output) / 'nested/leaf.txt').read_text(), 'keep result')
                self.assertEqual((Path(result.output) / 'notes.txt').read_text(), 'keep me')

    def test_source_cleanup_retains_partial_failed_cancelled_and_changed_sources(self):
        self.engine.delete_source = True
        partial = self.archive('partial.zip', {'broken.zip': b'broken'})
        self.assertEqual(self.engine.process(partial).status, 'partial')
        self.assertTrue(partial.is_file())
        bad = self.folder / 'bad.zip'; bad.write_bytes(b'broken')
        self.assertEqual(self.engine.process(bad).status, 'failed')
        self.assertTrue(bad.is_file())
        source = self.archive('cancel.zip', {'leaf.txt': 'keep'})
        extract = self.engine.extract
        def cancel_after_extract(path):
            output = extract(path); self.engine.cancel(); return output
        with patch.object(self.engine, 'extract', cancel_after_extract):
            result = self.engine.process(source)
        self.assertEqual(result.status, 'cancelled')
        self.assertTrue(source.is_file())
        self.engine.cancelled.clear()
        changed = self.archive('changed.zip', {'leaf.txt': 'keep'})
        def change_after_extract(path):
            output = extract(path)
            with open(path, 'ab') as stream: stream.write(b'changed')
            return output
        with patch.object(self.engine, 'extract', change_after_extract):
            result = self.engine.process(changed)
        self.assertEqual(result.status, 'partial')
        self.assertTrue(changed.is_file())
        self.assertTrue(Path(result.output).is_dir())

    def test_real_split_cleanup_and_restore_preserve_family_names(self):
        payload = self.folder / 'payload.bin'; payload.write_bytes(os.urandom(4096))
        packed = self.folder / 'split.7z'
        subprocess.run([str(ROOT / 'tools/7zip/7z.exe'), 'a', '-v1k', str(packed), str(payload)], check=True, stdout=subprocess.DEVNULL)
        volumes = sorted(self.folder.glob('split.7z.*'))
        unrelated = self.folder / 'split.7z.other'; unrelated.write_text('keep')
        self.engine.delete_source = True
        result = self.engine.process(volumes[0], '.zip')
        self.assertEqual(result.status, 'success', result.detail)
        self.assertFalse(any(path.exists() for path in volumes))
        self.assertEqual((Path(result.output) / payload.name).read_bytes(), payload.read_bytes())
        self.assertEqual(unrelated.read_text(), 'keep')

    def test_cleanup_rejects_incomplete_family_and_keeps_outputs_on_delete_failure(self):
        source = self.archive('source.zip', {'leaf.txt': 'keep'})
        self.engine.delete_source = True
        with patch.object(self.engine, 'remove_archive', side_effect=PermissionError('locked')):
            result = self.engine.process(source)
        self.assertEqual(result.status, 'partial')
        self.assertTrue(source.is_file())
        self.assertEqual((Path(result.output) / 'leaf.txt').read_text(), 'keep')
        one = self.folder / 'family.7z.001'; one.write_bytes(b'one')
        three = self.folder / 'family.7z.003'; three.write_bytes(b'three')
        with self.assertRaises(ValueError):
            self.engine.archive_snapshot(one)
        self.assertTrue(one.is_file() and three.is_file())

    def test_real_7z_reports_attempt_progress_without_inventing_completion(self):
        events = []
        self.engine.progress = events.append
        source = self.archive('progress.zip', {'data.txt': 'archive progress ' * 1000000})
        result = self.engine.process(source)
        self.assertEqual(result.status, 'success', result.detail)
        self.assertIsNone(events[0]['percent'])
        measured = [event for event in events if event['percent'] is not None]
        self.assertTrue(measured, events)
        self.assertTrue(all(0 <= event['percent'] <= 100 and event['archive'] == source.name and event['tool'] == '7z' for event in measured))
        self.assertEqual((Path(result.output) / 'data.txt').stat().st_size, 17000000)

    def test_existing_compound_extension_is_not_duplicated(self):
        content = self.folder / 'value.txt'; content.write_text('compound extension')
        source = self.folder / 'compound.tar.gz'
        with tarfile.open(source, 'w:gz') as archive:
            archive.add(content, arcname='value.txt')
        result = self.engine.process(source, '.tar.gz')
        self.assertEqual(result.status, 'success', result.detail)
        self.assertEqual(result.archive, str(source))
        self.assertTrue(source.is_file())
        self.assertFalse((self.folder / 'compound.tar.tar.gz').exists())
        self.assertEqual(next(Path(result.output).rglob('value.txt')).read_text(), 'compound extension')

    def test_progress_stream_handles_split_frames_and_out_of_range_values(self):
        # Synthetic output protocol; real child process, not real extraction.
        events = []
        self.engine.progress = events.append
        script = "import sys,time; sys.stdout.write('\\r 12'); sys.stdout.flush(); time.sleep(.12); sys.stdout.write('% done'); sys.stdout.flush(); time.sleep(.12); sys.stdout.write('\\r 999% bad\\r 42% done'); sys.stdout.flush(); time.sleep(.12)"
        code, output = self.engine._run([sys.executable, '-c', script, '-bsp1'], self.folder)
        self.assertEqual(code, 0)
        self.assertEqual([event['percent'] for event in events], [12, 42])
        self.assertIn('999%', output)

    def test_plain_unicode_output_and_existing_folder_preserved(self):
        archive = self.archive("中文 空格.zip", {"文檔.txt": "hello"})
        existing = archive.with_suffix("")
        existing.mkdir()
        (existing / "original.txt").write_text("keep")
        result = self.engine.process(archive)
        self.assertEqual(result.status, "success", result.detail)
        self.assertEqual((Path(result.output) / "文檔.txt").read_text(), "hello")
        self.assertEqual((existing / "original.txt").read_text(), "keep")
        self.assertTrue(archive.exists())

    def test_nested_keep_processes_each_once(self):
        third = self.archive("third.zip", {"value.txt": "leaf"})
        second = self.archive("second.zip", {"third.zip": third.read_bytes()})
        first = self.archive("first.zip", {"second.zip": second.read_bytes()})
        result = self.engine.process(first)
        output = Path(result.output)
        self.assertEqual(result.status, "success", result.detail)
        self.assertTrue((output / "second.zip").exists())
        self.assertEqual((output / "second/third/value.txt").read_text(), "leaf")
        self.assertFalse((output / "second_1").exists())

    def test_depth_is_actual_nesting_and_siblings_not_counted_as_depth(self):
        leaf = self.archive("leaf.zip", {"value.txt": "leaf"})
        parent = self.archive("parent.zip", {f"leaf{i}.zip": leaf.read_bytes() for i in range(8)})
        self.engine.depth = 2
        result = self.engine.process(parent)
        self.assertEqual(result.status, "success", result.detail)
        self.engine.depth = 1
        result = self.engine.process(parent)
        self.assertEqual(result.status, "partial")
        self.assertIn("上限", result.detail)

    def test_corrupt_inner_is_partial_and_preserved(self):
        archive = self.archive("parent.zip", {"bad.zip": b"broken", "good.txt": b"valid"})
        self.engine.delete_inner = True
        result = self.engine.process(archive)
        self.assertEqual(result.status, "partial")
        self.assertTrue((Path(result.output) / "bad.zip").exists())

    def test_password_retry_and_header_encryption(self):
        source = self.folder / "secret.txt"
        source.write_text("private data")
        archive = self.folder / "encrypted.7z"
        subprocess.run([str(ROOT / "tools/7zip/7z.exe"), "a", "-psecret", "-mhe=on", str(archive), str(source)],
                       check=True, stdout=subprocess.DEVNULL)
        self.engine.passwords = ["wrong", "secret"]
        result = self.engine.process(archive)
        self.assertEqual(result.status, "success", result.detail)
        self.assertEqual((Path(result.output) / "secret.txt").read_text(), "private data")
        self.assertEqual(self.engine.preferred_password, "secret")
        self.assertFalse(list(self.folder.glob(".auto7z-*")))

    def test_wrong_password_failure_and_rename_restored(self):
        source = self.folder / "secret.txt"
        source.write_text("private")
        archive = self.folder / "disguised.png"
        subprocess.run([str(ROOT / "tools/7zip/7z.exe"), "a", "-t7z", "-psecret", str(archive), str(source)],
                       check=True, stdout=subprocess.DEVNULL)
        self.engine.passwords = ["wrong"]
        result = self.engine.process(archive, ".7z")
        self.assertEqual(result.status, "failed")
        self.assertTrue(archive.exists())
        self.assertFalse(archive.with_suffix(".7z").exists())
        self.assertFalse(list(self.folder.glob(".auto7z-*")))

    def test_no_total_duration_timeout(self):
        code, output = self.engine._run([sys.executable, "-c", "import time; time.sleep(5.5); print('done')"])
        self.assertEqual(code, 0)
        self.assertIn("done", output)

    def test_cancel_only_owned_process(self):
        unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        timer = threading.Timer(0.4, self.engine.cancel)
        timer.start()
        try:
            with self.assertRaises(Cancelled):
                self.engine._run([sys.executable, "-c", "import time; time.sleep(30)"])
            self.assertIsNone(unrelated.poll())
        finally:
            timer.join()
            unrelated.kill()
            unrelated.wait()

    def test_idle_timeout_opt_in(self):
        self.engine.idle_timeout = 1
        with self.assertRaises(TimeoutError):
            self.engine._run([sys.executable, "-c", "import time; time.sleep(30)"], self.folder)

    @unittest.skipUnless(WINRAR, "WinRAR is optional and not redistributed")
    def test_winrar_unicode_space_path_and_no_password(self):
        archive = self.archive("中文 文件.zip", {"文檔.txt": b"contents"})
        self.engine.mode = "winrar"
        result = self.engine.process(archive)
        self.assertEqual(result.status, "success", result.detail)
        self.assertEqual((Path(result.output) / "文檔.txt").read_bytes(), b"contents")

    def test_auto_only_requires_one_engine(self):
        self.engine.tools["winrar"] = ""
        result = self.engine.process(self.archive("data.zip", {"data.txt": "data"}))
        self.assertEqual(result.status, "success", result.detail)

    def test_no_password_skips_redundant_listing(self):
        with patch.object(self.engine, "_encrypted", side_effect=AssertionError("Unnecessary precheck")):
            result = self.engine.process(self.archive("plain.zip", {"data.txt": "data"}))
        self.assertEqual(result.status, "success", result.detail)

    def test_safe_cleanup_refuses_user_directory(self):
        keep = self.folder / "keep"
        keep.mkdir()
        with self.assertRaises(ValueError):
            self.engine._discard(keep, self.folder)
        self.assertTrue(keep.exists())


if __name__ == "__main__":
    unittest.main()

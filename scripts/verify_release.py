"""Verify exact release assets and exercise the packaged backend without dev Python."""
import hashlib
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'desktop/package.json').read_text())['version']
OUTPUT = ROOT / 'release' / VERSION


def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def exercise_backend(app, folder):
    resources = app / 'resources'
    folder.mkdir(parents=True)
    plain = folder / '繁體中文 批次.zip'
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, 'w') as archive:
        archive.writestr('leaf.txt', 'nested release verification')
    with zipfile.ZipFile(plain, 'w') as archive:
        archive.writestr('inner.zip', inner.getvalue())
    secret = folder / 'secret.txt'; secret.write_text('encrypted release verification')
    encrypted = folder / 'encrypted.7z'
    subprocess.run([str(resources / '7z.exe'), 'a', '-psecret', '-mhe=on', str(encrypted), str(secret)], check=True, stdout=subprocess.DEVNULL)
    broken = folder / 'broken.zip'; broken.write_bytes(b'broken archive')
    env = dict(os.environ, AUTO7Z_CONFIG_DIR=str(folder / 'config'))
    process = subprocess.Popen([str(resources / 'auto7z-engine.exe')], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, encoding='utf-8', env=env,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    replies = queue.Queue(); events = []
    def read():
        for line in process.stdout:
            replies.put(json.loads(line))
        replies.put(None)
    threading.Thread(target=read, daemon=True).start()
    sequence = 0
    def wait_until(predicate):
        while True:
            message = replies.get(timeout=30)
            if message is None:
                raise RuntimeError('Backend exited: ' + process.stderr.read())
            events.append(message)
            if predicate(message): return message
    def rpc(op, args=None):
        nonlocal sequence
        sequence += 1
        process.stdin.write(json.dumps(dict(id=sequence, op=op, args=args or {})) + '\n'); process.stdin.flush()
        reply = wait_until(lambda message: message.get('id') == sequence)
        assert reply['ok'], reply
        return reply.get('data')
    def idle_state():
        # State may have arrived before the RPC acknowledgement.
        for event in reversed(events):
            if event.get('event') == 'state':
                state = event['data']
                if not state['busy'] and not state['scanning']: return state
                break
        return wait_until(lambda message: message.get('event') == 'state' and not message['data']['busy'] and not message['data']['scanning'])['data']
    try:
        init = rpc('init')
        rpc('save', dict(init['settings'], path_7z=str(resources / '7z.exe'), path_rar=''))
        rpc('add', dict(paths=[str(plain), str(encrypted), str(broken)])); idle_state()
        rpc('start', dict(passwords=['wrong', 'secret'])); state = idle_state()
        assert [row['status'] for row in state['rows']] == ['success', 'success', 'failed'], state
        first = state['rows'][0]['output']
        assert (Path(first) / 'inner/leaf.txt').read_text() == 'nested release verification'
        assert (Path(state['rows'][1]['output']) / 'secret.txt').read_text() == secret.read_text()
        with zipfile.ZipFile(broken, 'w') as archive: archive.writestr('fixed.txt', 'retry')
        rpc('start'); state = idle_state()
        assert state['total'] == 1 and all(row['status'] == 'success' for row in state['rows']), state
        assert state['rows'][0]['output'] == first
        assert any(event.get('event') == 'progress' and event['data']['percent'] is not None for event in events)
        original_outputs = [Path(row['output']) for row in state['rows']]
        ids = [row['id'] for row in state['rows']][::-1]
        rpc('reorder', dict(ids=ids)); state = idle_state()
        assert [row['id'] for row in state['rows']] == ids
        rpc('requeue', dict(ids=[ids[0]])); state = idle_state()
        assert state['rows'][0]['status'] == 'pending'
        assert state['rows'][0]['output'] == str(original_outputs[2])
        rpc('start'); state = idle_state()
        assert state['total'] == 1 and state['rows'][0]['status'] == 'success'
        assert (Path(state['rows'][0]['output']) / 'fixed.txt').read_text() == 'retry'
        rpc('remove', dict(ids=ids)); state = idle_state()
        assert not state['rows'] and all(path.is_dir() for path in original_outputs)
        assert all(path.is_file() for path in [plain, encrypted, broken])
        return dict(batch_success=2, expected_failure=1, retry_success=1, nested_content=True,
                    multi_password=True, queue_reorder=True, explicit_requeue=True, clear_preserves_files=True)
    finally:
        process.stdin.close()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait(); raise
        assert process.returncode == 0


def main():
    manifest = json.loads((OUTPUT / 'build-manifest.json').read_text())
    for line in (OUTPUT / 'SHA256SUMS.txt').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert digest(OUTPUT / name) == expected, name
    archive = OUTPUT / f'Auto7z-v{VERSION}-Windows-x64-Portable.zip'
    with zipfile.ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == set(manifest['files'])
        assert not any('settings.json' in name or 'WinRAR' in name or 'PyQt' in name for name in bundle.namelist())
        with tempfile.TemporaryDirectory(prefix='auto7z-release-verify-') as temporary:
            folder = Path(temporary); bundle.extractall(folder)
            for name, expected in manifest['files'].items(): assert digest(folder / name) == expected
            portable_result = exercise_backend(folder / 'Auto7z', folder / 'portable-test')
    single = OUTPUT / f'Auto7z-v{VERSION}-Windows-x64-Single.exe'
    cache = Path(os.environ['LOCALAPPDATA']) / 'Auto7z/Runtime' / f"{VERSION}-{manifest['payload_sha256'][:16]}"
    existed = cache.exists(); started = time.perf_counter()
    children = [subprocess.Popen([str(single), '--verify']) for _ in range(2)]
    for child in children: assert child.wait(timeout=60) == 0
    prepare_seconds = time.perf_counter() - started
    times = {name: (cache / name).stat().st_mtime_ns for name in manifest['files']}
    subprocess.run([str(single), '--verify'], check=True, timeout=30)
    assert all((cache / name).stat().st_mtime_ns == stamp for name, stamp in times.items())
    for name, expected in manifest['files'].items(): assert digest(cache / name) == expected
    damaged = cache / 'Auto7z/README.txt'
    original = damaged.read_bytes()
    repair = Path(str(cache) + '-repair')
    try:
        damaged.write_bytes(original + b'\nverification-only cache damage\n')
        subprocess.run([str(single), '--verify'], check=True, timeout=30)
        for name, expected in manifest['files'].items(): assert digest(repair / name) == expected
        stamp = (repair / 'Auto7z/Auto7z.exe').stat().st_mtime_ns
        subprocess.run([str(single), '--verify'], check=True, timeout=30)
        assert (repair / 'Auto7z/Auto7z.exe').stat().st_mtime_ns == stamp
        assert damaged.read_bytes() != original  # original modified cache was preserved
    finally:
        damaged.write_bytes(original)
    with tempfile.TemporaryDirectory(prefix='auto7z-single-verify-') as temporary:
        single_result = exercise_backend(cache / 'Auto7z', Path(temporary) / 'single-test')
    result = dict(version=VERSION, checksum_assets=True, exact_allowlist=True,
                  portable=portable_result, single=single_result, single_cache_preexisted=existed,
                  concurrent_prepare_seconds=round(prepare_seconds, 3), warm_cache_unchanged=True,
                  damaged_cache_preserved=True, repaired_cache_reused=True)
    report = ROOT / 'artifacts/v7-release-validation.json'; report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()

"""Package an allowlisted portable ZIP and verified self-extracting EXE."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def package():
    version = json.loads((ROOT / 'desktop/package.json').read_text())['version']
    output = ROOT / 'release' / version
    output.mkdir(parents=True, exist_ok=True)
    native = ROOT / 'desktop/src-tauri/target/release'
    resources = ROOT / 'desktop/src-tauri/resources'
    files = {'Auto7z.exe': native / 'auto7z.exe', 'README.txt': ROOT / 'docs/DISTRIBUTION.txt'}
    # Never include user configuration, WinRAR, demo files or stale target files.
    for name in ['auto7z-engine.exe', '7z.exe', '7z.dll', 'LICENSE', 'THIRD_PARTY_NOTICES.md']:
        files['resources/' + name] = resources / name
    for name in ['7-Zip.txt', 'Python.txt', 'GPL-3.0.txt', 'LGPL-3.0.txt', 'PyInstaller.txt', 'JavaScript-dependencies.txt', 'Rust-dependencies.txt']:
        files['resources/licenses/' + name] = resources / 'licenses' / name
    for path in files.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    archive_path = output / f'Auto7z-v{version}-Windows-x64-Portable.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, 'Auto7z/' + name)
    manifest = {'version': version, 'payload_sha256': sha256(archive_path),
                'files': {'Auto7z/' + name: sha256(path) for name, path in sorted(files.items())}}
    source = (ROOT / 'scripts/SingleLauncher.cs').read_text(encoding='utf-8')
    checks = ',\n'.join('{@"' + name + '", "' + digest + '"}' for name, digest in manifest['files'].items())
    source = source.replace('__VERSION__', version).replace('__PAYLOAD_SHA__', manifest['payload_sha256']).replace('__FILES__', checks)
    single = output / f'Auto7z-v{version}-Windows-x64-Single.exe'
    compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    with tempfile.TemporaryDirectory(prefix='auto7z-launcher-') as temp:
        script = Path(temp) / 'SingleLauncher.cs'
        script.write_text(source, encoding='utf-8-sig')
        subprocess.run([str(compiler), '/nologo', '/optimize+', '/target:winexe', '/platform:x64',
                        '/reference:System.Windows.Forms.dll', '/reference:System.IO.Compression.dll',
                        '/reference:System.IO.Compression.FileSystem.dll', '/win32icon:' + str(ROOT / 'assets/Auto7z.ico'),
                        '/resource:' + str(archive_path) + ',Payload.zip', '/out:' + str(single), str(script)], check=True)
    artifacts = [single, archive_path]
    setup = native / 'bundle/nsis' / f'Auto7z_{version}_x64-setup.exe'
    if setup.is_file():
        target = output / f'Auto7z-v{version}-Windows-x64-Setup.exe'
        shutil.copy2(setup, target); artifacts.append(target)
    (output / 'SHA256SUMS.txt').write_text(''.join(f'{sha256(path)}  {path.name}\n' for path in artifacts), encoding='utf-8')
    (output / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'version': version, 'assets': [str(path) for path in artifacts]}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--package-only', action='store_true')
    if parser.parse_args().package_only:
        package()
    else:
        subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'desktop/scripts/build.ps1')], cwd=ROOT, check=True)

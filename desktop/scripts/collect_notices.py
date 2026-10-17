"""Collect installed production JS licenses and locked Rust crate licenses for local bundles."""
import json
import os
from pathlib import Path
import tomllib

desktop = Path(__file__).resolve().parents[1]
target = desktop / 'src-tauri/resources/licenses'
target.mkdir(parents=True, exist_ok=True)
chunks = []
lock = json.loads((desktop / 'package-lock.json').read_text(encoding='utf-8'))
for name, entry in sorted(lock['packages'].items()):
    if not name or entry.get('dev'):
        continue
    folder = desktop / name
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.name.lower().startswith(('license', 'licence', 'notice', 'copying')))
    chunks.append(f"\n{'=' * 72}\n{name} {entry.get('version', '')} ({entry.get('license', 'see package')})\n")
    chunks.extend(p.read_text(encoding='utf-8', errors='replace') for p in files)
(target / 'JavaScript-dependencies.txt').write_text('\n'.join(chunks), encoding='utf-8')

lock_path = desktop / 'src-tauri/Cargo.lock'
if lock_path.exists():
    crates = tomllib.loads(lock_path.read_text(encoding='utf-8'))['package']
    registry = Path(os.environ.get('CARGO_HOME', str(Path.home() / '.cargo'))) / 'registry/src'
    chunks = []
    for item in crates:
        if 'source' not in item:
            continue
        folders = list(registry.glob(f"*/{item['name']}-{item['version']}"))
        chunks.append(f"\n{'=' * 72}\n{item['name']} {item['version']}\n")
        for folder in folders:
            manifest = tomllib.loads((folder / 'Cargo.toml').read_text(encoding='utf-8'))
            chunks.append('License: ' + manifest.get('package', {}).get('license', 'see crate source'))
            for p in sorted(folder.iterdir()):
                if p.is_file() and p.name.lower().startswith(('license', 'licence', 'notice', 'copying')):
                    chunks.append(p.read_text(encoding='utf-8', errors='replace'))
    (target / 'Rust-dependencies.txt').write_text('\n'.join(chunks), encoding='utf-8')
print('Collected JS and Rust notices')

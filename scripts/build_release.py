"""以獨立環境建立 Windows 單檔與資料夾版；不收錄 WinRAR、密碼或使用者設定。"""
import argparse, subprocess, sys, shutil, zipfile, hashlib, json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--version',default='6.1.0');args=parser.parse_args()
release=root/'release';release.mkdir(exist_ok=True)
for mode in ('onedir','onefile'):
    name='Auto7z' if mode=='onedir' else 'Auto7z-Single'
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed',f'--{mode}','--name',name,'--icon',str(root/'Auto7z.ico'),'--distpath',str(root/'dist'),'--workpath',str(root/'build'/mode),'--specpath',str(root/'build'),
             '--add-binary',f'{root / "7z.exe"};.','--add-binary',f'{root / "7z.dll"};.','--add-data',f'{root / "Auto7z.ico"};.','--add-data',f'{root / "licenses"};licenses','--add-data',f'{root / "LICENSE"};.','--add-data',f'{root / "THIRD_PARTY_NOTICES.md"};.']
    for module in ('PyQt5.QtWebEngineWidgets','PyQt5.QtQml','PyQt5.QtQuick','PyQt5.QtMultimedia','PyQt5.QtSql','tkinter','numpy','scipy','matplotlib','progress_preview'):
        command += ['--exclude-module',module]
    command.append(str(root/'main.py'));subprocess.run(command,cwd=root,check=True)
    if mode=='onefile':
        shutil.copy2(root/'dist'/f'{name}.exe',release/f'Auto7z-v{args.version}-Windows-x64-Single.exe')
    else:
        bundle=root/'dist'/name
        for file in ('README.md','LICENSE','THIRD_PARTY_NOTICES.md'):
            shutil.copy2(root/file,bundle/file)
        shutil.copytree(root/'licenses',bundle/'licenses',dirs_exist_ok=True)
        with zipfile.ZipFile(release/f'Auto7z-v{args.version}-Windows-x64-Portable.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for p in bundle.rglob('*'):
                if p.is_file():archive.write(p,Path('Auto7z')/p.relative_to(bundle))
lines=[]
for p in sorted(release.iterdir()):
    if p.suffix in ('.exe','.zip'):lines.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}')
(release/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')

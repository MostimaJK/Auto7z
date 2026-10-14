"""收錄所用 Python 執行環境與已安裝依賴的原始授權文件。"""
import sys,shutil,importlib.metadata
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'licenses';out.mkdir(exist_ok=True)
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.is_file():shutil.copy2(python_license,out/'Python.txt')
for distribution in importlib.metadata.distributions():
 name=distribution.metadata['Name']
 for file in distribution.files or []:
  if '.dist-info/' in str(file) and Path(file).name.lower().startswith(('license','copying','notice')):
   source=Path(distribution.locate_file(file));target=out/'dependencies'/name/Path(file)
   if source.is_file():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)

for file in out.rglob("*"):
 if file.is_file():
  text=file.read_text(encoding="utf-8");file.write_text("\n".join(line.rstrip() for line in text.splitlines()).rstrip()+"\n",encoding="utf-8")

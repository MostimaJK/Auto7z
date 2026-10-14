"""以實際 C++ EXE 驗證解壓，不使用 Python 引擎代替。"""
import os,json,subprocess,sys,tempfile,zipfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXE=Path(sys.argv.pop(1)).resolve() if len(sys.argv)>1 else ROOT/'Auto7zCpp/dist/Auto7zCpp.exe'
WINRAR = next((str(p) for p in (ROOT/"WinRAR.exe",Path(os.environ.get("ProgramFiles","C:/Program Files"))/"WinRAR/WinRAR.exe") if p.is_file()), "")
class ParityTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def archive(self,name,data):
  p=self.folder/name
  with zipfile.ZipFile(p,'w') as z:
   for k,v in data.items():z.writestr(k,v)
  return p
 def run_engine(self,source,**options):
  config={'path_7z':str(ROOT/'7z.exe'),'path_rar':'','sources':[str(source)],**options}
  inp=self.folder/'request.json';out=self.folder/'response.json';inp.write_text(json.dumps(config),encoding='utf-8')
  subprocess.run([str(EXE),'--engine',str(inp),str(out)],check=True,timeout=45)
  return json.loads(out.read_text(encoding='utf-8'))[0]
 def test_unicode_collision_and_original_preserved(self):
  archive=self.archive('中文 空格.zip',{'文檔.txt':'hello'});old=archive.with_suffix('');old.mkdir();(old/'keep').write_text('keep')
  r=self.run_engine(archive);self.assertEqual(r['status'],'success',r);self.assertEqual((Path(r['output'])/'文檔.txt').read_text(),'hello');self.assertTrue((old/'keep').exists());self.assertTrue(archive.exists())
 def test_recursive_keep_and_depth(self):
  leaf=self.archive('leaf.zip',{'value.txt':'leaf'});parent=self.archive('parent.zip',{'leaf.zip':leaf.read_bytes()})
  r=self.run_engine(parent);self.assertEqual(r['status'],'success',r);self.assertTrue((Path(r['output'])/'leaf.zip').exists());self.assertEqual((Path(r['output'])/'leaf/value.txt').read_text(),'leaf')
  r=self.run_engine(parent,depth=1);self.assertEqual(r['status'],'partial',r)
 def test_corrupt_inner_preserved_and_successful_inner_deleted(self):
  leaf=self.archive('leaf.zip',{'value':'leaf'});parent=self.archive('parent.zip',{'bad.zip':b'broken','leaf.zip':leaf.read_bytes()})
  r=self.run_engine(parent,delete_inner=True);self.assertEqual(r['status'],'partial',r);self.assertTrue((Path(r['output'])/'bad.zip').exists());self.assertFalse((Path(r['output'])/'leaf.zip').exists())
 def test_encrypted_password_retry_and_cleanup(self):
  f=self.folder/'secret.txt';f.write_text('private');archive=self.folder/'secret.7z'
  subprocess.run([str(ROOT/'7z.exe'),'a','-psecret','-mhe=on',str(archive),str(f)],check=True,stdout=subprocess.DEVNULL)
  r=self.run_engine(archive,passwords=['wrong','secret']);self.assertEqual(r['status'],'success',r);self.assertEqual((Path(r['output'])/'secret.txt').read_text(),'private');self.assertFalse(list(self.folder.glob('.auto7z-*')))
 def test_failed_rename_restored_and_partial_retry_source(self):
  f=self.folder/'secret.txt';f.write_text('private');archive=self.folder/'disguised.png'
  subprocess.run([str(ROOT/'7z.exe'),'a','-t7z','-psecret',str(archive),str(f)],check=True,stdout=subprocess.DEVNULL)
  r=self.run_engine(archive,passwords=['wrong'],extension='.7z');self.assertEqual(r['status'],'failed',r);self.assertTrue(archive.exists());self.assertFalse(archive.with_suffix('.7z').exists())
  parent=self.archive('partial.png',{'bad.zip':b'broken'});r=self.run_engine(parent,extension='.zip');self.assertEqual(r['status'],'partial');self.assertTrue(Path(r['archive']).exists());r2=self.run_engine(r['archive']);self.assertEqual(r2['status'],'partial');self.assertNotEqual(r['output'],r2['output'])
 @unittest.skipUnless(WINRAR,"WinRAR is optional and not redistributed")
 def test_winrar_compatibility(self):
  archive=self.archive('中文 文件.zip',{'內容.txt':'hello'});r=self.run_engine(archive,path_rar=WINRAR,mode='winrar');self.assertEqual(r['status'],'success',r)
if __name__=='__main__':unittest.main()

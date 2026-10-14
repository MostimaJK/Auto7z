import os
import subprocess
import sys
import tempfile
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
        self.engine = Engine(str(ROOT / "7z.exe"), WINRAR)

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, name, contents):
        path = self.folder / name
        with zipfile.ZipFile(path, "w") as archive:
            for key, value in contents.items():
                archive.writestr(key, value)
        return path

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
        subprocess.run([str(ROOT / "7z.exe"), "a", "-psecret", "-mhe=on", str(archive), str(source)],
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
        subprocess.run([str(ROOT / "7z.exe"), "a", "-t7z", "-psecret", str(archive), str(source)],
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

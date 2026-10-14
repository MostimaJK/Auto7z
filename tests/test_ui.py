"""Run in the project's Qt5 environment. Uses native Qt rendering and events."""
import os
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "windows" if os.name == "nt" else "offscreen")
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from main import MainWindow, load_settings, DEFAULT_SETTINGS


class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="auto7z-ui-")
        self.window = MainWindow()
        self.window.show()
        self.panel = self.window.extractor_interface
        self.app.processEvents()

    def tearDown(self):
        for panel in (self.window.extractor_interface, self.window.all_in_one_interface):
            self.panel = panel
            if panel.running:
                panel.cancel()
                self.wait_finished()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def wait_finished(self):
        deadline = time.monotonic() + 20
        while self.panel.running and time.monotonic() < deadline:
            QTest.qWait(30)
        self.assertFalse(self.panel.running, "Worker did not stop")

    def test_success_and_failure_rows_retained_and_retry_skips_success(self):
        archive = Path(self.temp.name) / "good.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("file.txt", "data")
        bad = Path(self.temp.name) / "broken.zip"
        bad.write_bytes(b"corrupt")
        self.panel.txt_rar_path.clear()
        self.panel.add_files_to_list([str(archive), str(bad)])
        QTest.mouseClick(self.panel.btn_start, Qt.LeftButton)
        self.assertTrue(self.panel.running)
        self.assertFalse(self.panel.btn_clear.isEnabled())
        self.assertFalse(self.panel.list_widget.isEnabled())
        self.wait_finished()
        self.assertEqual(self.panel.list_widget.count(), 2)
        self.assertEqual([r.status for r in self.panel.results], ["success", "failed"])
        self.assertIn("失敗 1", self.panel.progress_label.text())
        QTest.mouseClick(self.panel.btn_start, Qt.LeftButton)
        self.wait_finished()
        self.assertFalse((Path(self.temp.name) / "good_1").exists())
        item = self.panel.list_widget.item(0)
        self.panel.list_widget.remove_selected_item(item)
        self.assertEqual(self.panel.file_paths, [str(bad)])
        self.panel.clear_queue()
        self.assertEqual(self.panel.results, [])

    def test_nondefault_pages_load_on_demand_and_navigation_works(self):
        self.assertIsNone(self.window.all_in_one_interface._content)
        self.assertIsNone(self.window.changer_interface._content)
        self.assertIsNone(self.window.settings_interface._content)
        self.window.switchTo(self.window.all_in_one_interface)
        QTest.qWait(250)
        self.assertIsNotNone(self.window.all_in_one_interface._content)
        self.assertIsNone(self.window.settings_interface._content)
        self.window.switchTo(self.window.extractor_interface)
        QTest.qWait(250)
        self.assertIs(self.window.stackedWidget.currentWidget(), self.window.extractor_interface)

    def test_fixed_apple_layout_and_clear_resets_completed_state(self):
        for panel in (self.window.extractor_interface, self.window.all_in_one_interface):
            self.assertEqual(panel.progress_bar.visualStyle(), "apple")
            self.assertFalse(hasattr(panel, "combo_progress_style"))
            self.assertFalse(hasattr(panel, "btn_progress_preview"))
            panel.handle_progress(100, "文件隊列處理結束")
            panel.show_activity("目前活動")
            panel.detail.append("結果")
            panel.detail.show()
            panel.btn_open.setEnabled(True)
            panel.clear_queue()
            self.assertEqual(panel.progress_bar.value(), 0)
            self.assertEqual(panel.percent_label.text(), "0%")
            self.assertTrue(panel.activity_label.isHidden())
            self.assertTrue(panel.detail.isHidden())
            self.assertFalse(panel.btn_open.isEnabled())
            self.assertEqual(panel.progress_label.text(), "準備就緒")

    def test_settings_migrate_old_short_timeouts_and_validate(self):
        settings = Path(self.temp.name) / "settings.json"
        settings.write_text('{"timeout_7z_precheck":3,"timeout_no_password":5,"max_recursion_depth":"oops"}', encoding="utf-8")
        with patch("main.SETTINGS_FILE", str(settings)):
            loaded = load_settings()
        self.assertEqual(loaded["timeout_7z_precheck"], 30)
        self.assertEqual(loaded["idle_timeout_seconds"], 0)
        self.assertEqual(loaded["max_recursion_depth"], DEFAULT_SETTINGS["max_recursion_depth"])

    def test_all_in_one_partial_retry_uses_restored_archive_path(self):
        archive = Path(self.temp.name) / "disguised.png"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("bad.zip", b"invalid")
        self.panel = self.window.all_in_one_interface
        self.window.switchTo(self.panel)
        self.panel.txt_rar_path.clear()
        self.panel.add_files_to_list([str(archive)])
        self.panel.start()
        self.wait_finished()
        self.assertEqual(self.panel.results[0].status, "partial")
        self.assertTrue(archive.with_suffix(".zip").exists())
        self.panel.start()
        self.wait_finished()
        self.assertEqual(len(self.panel.results), 1)
        self.assertEqual(self.panel.results[0].source, str(archive))
        self.assertEqual(self.panel.results[0].status, "partial")
        self.assertTrue((Path(self.temp.name) / "disguised_1").exists())


if __name__ == "__main__":
    unittest.main()

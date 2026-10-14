import os
import unittest
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if os.name == "nt" else "offscreen")
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from animated_progress import AnimatedProgressBar
from progress_preview import ProgressPreviewDialog


class ProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_classic_styles_are_static_and_glow_animation_preserves_value(self):
        bar = AnimatedProgressBar()
        bar.resize(400, 42)
        bar.setValue(64)
        bar.setBusy(True)
        bar.show()
        self.app.processEvents()
        try:
            for style in bar.STYLES:
                bar.setVisualStyle(style)
                first = bar.grab().toImage()
                QTest.qWait(250)
                if style in bar.PALETTES:
                    self.assertTrue(bar._timer.isActive())
                    # Tiny adjacent frames can quantize to identical alpha values.
                    # Compare the high/low breathing phases instead of wall-clock timing.
                    bar._phase = .9
                    first = bar.grab().toImage()
                    bar._phase = 2.7
                    self.assertNotEqual(first, bar.grab().toImage())
                else:
                    self.assertEqual(first, bar.grab().toImage())
                    self.assertFalse(bar._timer.isActive())
                self.assertEqual(bar.value(), 64)
                bar.setIndeterminate(True)
                first = bar.grab().toImage()
                QTest.qWait(250)
                self.assertNotEqual(first, bar.grab().toImage())
                self.assertEqual(bar.value(), 64)
                bar.setIndeterminate(False)
            bar.setAnimated(False)
            self.assertFalse(bar._timer.isActive())
            first = bar.grab().toImage()
            QTest.qWait(150)
            self.assertEqual(first, bar.grab().toImage())
            bar.setAnimated(True)
            bar.hide()
            self.assertFalse(bar._timer.isActive())
        finally:
            bar.close()
            bar.deleteLater()

    def test_preview_controls_are_separate_from_task_progress(self):
        task_bar = AnimatedProgressBar()
        task_bar.setValue(20)
        dialog = ProgressPreviewDialog()
        dialog.show()
        self.app.processEvents()
        try:
            dialog.slider.setValue(85)
            self.assertEqual([bar.value() for bar in dialog.bars], [85] * len(dialog.bars))
            self.assertEqual(task_bar.value(), 20)
            dialog.color_combo.setCurrentIndex(1)
            dialog.surface_combo.setCurrentIndex(2)
            self.assertEqual(dialog.selected_bar.visualStyle(), "burgundy")
            self.assertEqual(dialog.selected_bar._surface, "dark")
            self.assertIn("深色適配", dialog.selected_label.text())
            dialog.glow_combo.setCurrentIndex(0)
            self.assertFalse(dialog.selected_bar._timer.isActive())
            dialog.unknown_check.setChecked(True)
            self.assertFalse(dialog.slider.isEnabled())
            self.assertNotIn("85%", dialog.value_label.text())
            dialog.animation_check.setChecked(False)
            self.assertTrue(all(not bar._timer.isActive() for bar in dialog.bars))
        finally:
            dialog.close()
            dialog.deleteLater()
            task_bar.deleteLater()

    def test_every_style_updates_immediately_without_interpolation(self):
        bar = AnimatedProgressBar()
        for style in bar.STYLES:
            bar.setVisualStyle(style)
            for value in (0, 20, 80, 100, 0):
                bar.setValue(value)
                self.assertEqual(bar.displayedValue(), value)
                self.assertEqual(bar.value(), value)
        bar.deleteLater()

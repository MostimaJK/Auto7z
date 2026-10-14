import os
import sys
import time
import json
import traceback
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QLocale, QTranslator, QLibraryInfo, QEvent
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QFileDialog, QMenu, QAction, QMessageBox)
from PyQt5.QtGui import QPainter, QPen, QColor, QCursor
from qfluentwidgets import (MSFluentWindow, SubtitleLabel, PushButton, ComboBox,
                            LineEdit, ListWidget, FluentIcon, InfoBar,
                            BodyLabel, PrimaryPushButton, CardWidget,
                            SpinBox, SwitchButton, ScrollArea,
                            StrongBodyLabel, NavigationItemPosition)


def install_traditional_translations():
    """載入 Qt 與 Fluent 內建控件的繁體中文；保持翻譯器存活。"""
    app = QApplication.instance()
    if app is None or hasattr(app, "_auto7z_translators"):
        return
    from qfluentwidgets import FluentTranslator
    qt_translator = QTranslator(app)
    qt_translator.load("qtbase_zh_TW", QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    fluent_translator = FluentTranslator(QLocale("zh_TW"), app)
    app.installTranslator(qt_translator)
    app.installTranslator(fluent_translator)
    app._auto7z_translators = (qt_translator, fluent_translator)


# ═══════════════════════════════════════════════════════════════
#  全局異常鉤子
# ═══════════════════════════════════════════════════════════════
def global_exception_hook(exc_type, exc_value, exc_tb):
    tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"[FATAL] {tb_str}", flush=True)
    QMessageBox.critical(None, "程序異常", f"發生未捕獲的異常：\n\n{tb_str}")
    sys.exit(1)

sys.excepthook = global_exception_hook


# ═══════════════════════════════════════════════════════════════
#  日誌 & 配置
# ═══════════════════════════════════════════════════════════════
def log(msg, level="INFO"):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}", flush=True)


SETTINGS_FILE = os.path.join(os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
                             else os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULT_SETTINGS = {
    "timeout_7z_precheck": 30,
    "max_recursion_depth": 20,
    "path_7z": "",
    "path_rar": "",
    "delete_after_extract": False,
    "idle_timeout_seconds": 0,
    "settings_version": 2,
}


def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            if not isinstance(data, dict):
                raise ValueError("設置格式必須爲對象")
            merged.update(data)
            # Old total-duration settings no longer govern extraction.
            if data.get("settings_version", 1) < 2:
                merged["timeout_7z_precheck"] = 30
                merged["idle_timeout_seconds"] = 0
            for key, lower, upper in (("timeout_7z_precheck", 3, 300),
                                      ("idle_timeout_seconds", 0, 86400),
                                      ("max_recursion_depth", 1, 100)):
                value = merged.get(key)
                if not isinstance(value, int) or isinstance(value, bool):
                    value = DEFAULT_SETTINGS[key]
                merged[key] = max(lower, min(upper, value))
            for key in ("path_7z", "path_rar"):
                if not isinstance(merged[key], str):
                    merged[key] = ""
            if not isinstance(merged["delete_after_extract"], bool):
                merged["delete_after_extract"] = False
            merged["settings_version"] = 2
            for key in ("timeout_no_password", "timeout_rar_no_password",
                        "timeout_7z_extract", "timeout_rar_extract"):
                merged.pop(key, None)
            return merged
    except Exception as e:
        log(f"加載設置失敗: {e}", "WARN")
    return DEFAULT_SETTINGS.copy()


def save_settings(settings_dict):
    import tempfile
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False,
                                         dir=os.path.dirname(SETTINGS_FILE), suffix=".json") as f:
            temporary = f.name
            json.dump(settings_dict, f, indent=4, ensure_ascii=False)
        os.replace(temporary, SETTINGS_FILE)
        log("設置已保存", "OK")
        return True
    except Exception as e:
        log(f"保存設置失敗: {e}", "ERROR")
        return False
    finally:
        if temporary and os.path.exists(temporary):
            try:
                os.remove(temporary)
            except OSError as error:
                log(f"臨時設置文件清理失敗: {error}", "WARN")


# ═══════════════════════════════════════════════════════════════
#  路徑查找
# ═══════════════════════════════════════════════════════════════
def find_7z_path():
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, "7z.exe")
        if os.path.exists(p): return p
    for folder in (os.path.dirname(sys.executable), os.path.dirname(os.path.abspath(__file__))):
        candidate = os.path.join(folder, "7z.exe")
        if os.path.isfile(candidate):
            return candidate
    for p in ["C:\\Program Files\\7-Zip\\7z.exe",
              "C:\\Program Files (x86)\\7-Zip\\7z.exe"]:
        if os.path.exists(p): return p
    return ""


def find_rar_path():
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, "WinRAR.exe")
        if os.path.exists(p): return p
    for folder in (os.path.dirname(sys.executable), os.path.dirname(os.path.abspath(__file__))):
        candidate = os.path.join(folder, "WinRAR.exe")
        if os.path.isfile(candidate):
            return candidate
    for p in ["C:\\Program Files\\WinRAR\\WinRAR.exe",
              "C:\\Program Files (x86)\\WinRAR\\WinRAR.exe"]:
        if os.path.exists(p): return p
    return ""


def get_effective_settings():
    s = load_settings()
    if not s["path_7z"]:
        s["path_7z"] = find_7z_path()
    if not s["path_rar"]:
        s["path_rar"] = find_rar_path()
    return s


# --- 1. 拖拽區域 ---
class DragDropArea(QWidget):
    filesDropped = pyqtSignal(list)

    def __init__(self, text="將文件拖拽到此處，或點擊選擇文件", parent=None):
        super().__init__(parent=parent)
        self.text = text
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self.is_drag_over = False
        self.click_callback = None

        self.label = SubtitleLabel(self.text, self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)

    def resizeEvent(self, event):
        self.label.setGeometry(0, 0, self.width(), self.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.is_drag_over:
            pen = QPen(QColor("#1765CC"), 2, Qt.DashLine)
            painter.setBrush(QColor("#E8F0FE"))
        else:
            pen = QPen(QColor("#738399"), 1.5, Qt.DashLine)
            painter.setBrush(QColor("#F1F5FC"))
        painter.setPen(pen)
        painter.drawRoundedRect(5, 5, self.width() - 10, self.height() - 10, 12, 12)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            self.is_drag_over = True
            self.update()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()

    def dragLeaveEvent(self, event):
        self.is_drag_over = False
        self.update()

    def dropEvent(self, event):
        self.is_drag_over = False
        self.update()
        urls = event.mimeData().urls()
        file_paths = [url.toLocalFile() for url in urls if os.path.isfile(url.toLocalFile())]
        if file_paths:
            event.accept()
            self.filesDropped.emit(file_paths)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_drag_over = False
            self.update()
            if self.click_callback:
                self.click_callback()


# --- 2. 右鍵列表 ---
class RightClickListWidget(ListWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.parent_widget = parent
        self.setStyleSheet("""
            ListWidget {
                border: 1px solid #e0e0e0; border-radius: 8px; padding: 5px;
                background-color: #ffffff;
            }
            QListWidget::item {
                padding: 10px; border-radius: 6px; margin-bottom: 2px;
            }
            QListWidget::item:hover { background-color: #f3f3f3; }
            QListWidget::item:selected { background-color: #E8F0FE; color: #1F2937; }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls if os.path.isfile(url.toLocalFile())]
        if paths and self.parent_widget and hasattr(self.parent_widget, 'add_files_to_list'):
            event.accept()
            self.parent_widget.add_files_to_list(paths)

    def show_context_menu(self, pos: QPoint):
        item = self.itemAt(pos)
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background-color: #f3f3f3; border: 1px solid #cccccc; border-radius: 8px; padding: 4px; }\n"
            "QMenu::item { padding: 8px 24px 8px 20px; background-color: transparent; border-radius: 4px; }\n"
            "QMenu::item:selected { background-color: #e5e5e5; color: #000000; }")
        if item:
            menu.addAction(QAction('❌ 移除該文件', menu,
                                   triggered=lambda: self.remove_selected_item(item)))
        if self.count() > 0:
            menu.addAction(QAction('🗑️ 清空所有文件', menu,
                                   triggered=self.clear_all_items))
        if not menu.isEmpty():
            menu.exec_(QCursor.pos())

    def remove_selected_item(self, item):
        if item:
            text = item.data(Qt.UserRole) or item.text()
            if self.parent_widget and hasattr(self.parent_widget, 'file_paths') and text in self.parent_widget.file_paths:
                self.parent_widget.file_paths.remove(text)
            self.takeItem(self.row(item))

    def clear_all_items(self):
        if self.parent_widget and hasattr(self.parent_widget, 'file_paths'):
            self.parent_widget.file_paths.clear()
        self.clear()


from worker import ExtractionWorker
from extraction_panel import ExtractionPanel, COLORS


# --- 功能一：改後綴 ---
class ExtensionChangerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("ExtensionChangerWidget")
        self.file_paths = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(18)

        title = SubtitleLabel("一鍵修改文件擴展名", self)
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #202020;")
        layout.addWidget(title)

        self.drag_area = DragDropArea("🗂️ 將文件拖拽到此處，或點擊批量選擇", self)
        self.drag_area.filesDropped.connect(self.add_files_to_list)
        self.drag_area.click_callback = self.import_files
        layout.addWidget(self.drag_area)

        layout.addWidget(BodyLabel("待處理文件列表 (右鍵可移除)：", self))
        self.list_widget = RightClickListWidget(self)
        layout.addWidget(self.list_widget)

        control_card = CardWidget(self)
        card_layout = QHBoxLayout(control_card)
        card_layout.setContentsMargins(15, 12, 15, 12)

        self.combo_ext = ComboBox(self)
        self.combo_ext.addItems([".zip", ".rar", ".7z", ".tar", ".gz", ".png", ".mp4"])
        self.combo_ext.setMinimumWidth(110)

        self.btn_clear = PushButton(FluentIcon.DELETE, "清空列表", self)
        self.btn_clear.clicked.connect(self.list_widget.clear_all_items)

        self.btn_action = PrimaryPushButton(FluentIcon.UPDATE, "開始一鍵修改", self)
        self.btn_action.clicked.connect(self.change_extensions)

        card_layout.addWidget(BodyLabel("目標擴展名：", self))
        card_layout.addWidget(self.combo_ext)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.btn_clear)
        card_layout.addStretch()
        card_layout.addWidget(self.btn_action)
        layout.addWidget(control_card)

    def add_files_to_list(self, files):
        for f in files:
            if f not in self.file_paths:
                self.file_paths.append(f)
                self.list_widget.addItem(f)

    def import_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇文件", "", "All Files (*)")
        if files:
            self.add_files_to_list(files)

    def change_extensions(self):
        if not self.file_paths:
            InfoBar.warning("提示", "請先導入文件！", duration=2000, parent=self)
            return
        target_ext = self.combo_ext.currentText()
        success_count = 0
        remaining = []
        for file_path in list(self.file_paths):
            if os.path.exists(file_path):
                base, _ = os.path.splitext(file_path)
                new_path = base + target_ext
                try:
                    if os.path.normcase(new_path) == os.path.normcase(file_path):
                        success_count += 1
                        continue
                    counter = 1
                    while os.path.exists(new_path):
                        new_path = f"{base}_{counter}{target_ext}"
                        counter += 1
                    os.rename(file_path, new_path)
                    success_count += 1
                except Exception as e:
                    log(f"重命名失敗: {e}", "ERROR")
                    remaining.append(file_path)
            else:
                remaining.append(file_path)
        notice = InfoBar.warning if remaining else InfoBar.success
        notice("處理結果", f"成功 {success_count} 個；未成功 {len(remaining)} 個。", duration=3000, parent=self)
        self.list_widget.clear_all_items()
        self.add_files_to_list(remaining)


class AutoExtractorWidget(ExtractionPanel):
    def __init__(self, parent=None):
        super().__init__(parent, DragDropArea, RightClickListWidget,
                         load_settings, get_effective_settings)


class AllInOneWidget(ExtractionPanel):
    def __init__(self, parent=None):
        super().__init__(parent, DragDropArea, RightClickListWidget,
                         load_settings, get_effective_settings, all_in_one=True)


# --- 功能四：設置界面 ---
class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingsWidget")
        self.settings = load_settings()
        self._spinboxes = {}
        self.init_ui()

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = ScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(18)

        # ── 標題 ──
        header_row = QHBoxLayout()
        title = SubtitleLabel("程序設置", self)
        title.setStyleSheet("font-size: 22px; font-weight: 600; color: #202020;")
        header_row.addWidget(title)
        header_row.addStretch()
        version_label = BodyLabel("v6.1.0", self)
        version_label.setStyleSheet("color: #526174; font-size: 13px;")
        header_row.addWidget(version_label)
        layout.addLayout(header_row)

        desc = BodyLabel("修改設置後請點擊下方「保存設置」按鈕使其生效。", self)
        desc.setStyleSheet("color: #526174; margin-bottom: 6px;")
        layout.addWidget(desc)

        # ═══════════════════════════════════════════════
        #  分組1：超時設置
        # ═══════════════════════════════════════════════
        timeout_card = CardWidget(self)
        timeout_layout = QVBoxLayout(timeout_card)
        timeout_layout.setContentsMargins(20, 16, 20, 16)
        timeout_layout.setSpacing(12)

        timeout_title = StrongBodyLabel("等待與停滯保護", self)
        timeout_title.setStyleSheet("font-size: 15px; color: #333333;")
        timeout_layout.addWidget(timeout_title)

        explanation = BodyLabel("解壓默認不限總時長。停滯保護僅在持續無活動時停止；設爲 0 可關閉。", self)
        explanation.setWordWrap(True)
        timeout_layout.addWidget(explanation)
        timeout_layout.addLayout(self._make_spin_row(
            "目錄預檢等待（秒）", "超時後直接嘗試解壓，不判定文件失敗。",
            "timeout_7z_precheck", 3, 300))
        timeout_layout.addLayout(self._make_spin_row(
            "停滯保護（秒，0 = 關閉）", "參考 CPU、工具輸出與文件寫入；慢盤建議關閉。",
            "idle_timeout_seconds", 0, 86400))

        layout.addWidget(timeout_card)

        # ═══════════════════════════════════════════════
        #  分組2：路徑設置
        # ═══════════════════════════════════════════════
        path_card = CardWidget(self)
        path_layout = QVBoxLayout(path_card)
        path_layout.setContentsMargins(20, 16, 20, 16)
        path_layout.setSpacing(12)

        path_title = StrongBodyLabel("📁 工具路徑", self)
        path_title.setStyleSheet("font-size: 15px; color: #333333;")
        path_layout.addWidget(path_title)

        path_desc = BodyLabel("設置後將作爲解壓頁面的默認路徑。留空則自動查找。", self)
        path_desc.setStyleSheet("color: #526174; font-size: 12px;")
        path_layout.addWidget(path_desc)

        row7 = QHBoxLayout()
        row7.addWidget(BodyLabel("7z.exe", self))
        self.txt_path_7z = LineEdit(self)
        self.txt_path_7z.setPlaceholderText("自動查找...")
        self.txt_path_7z.setText(self.settings.get("path_7z", ""))
        self.txt_path_7z.setMinimumWidth(300)
        btn7 = PushButton("瀏覽", self)
        btn7.clicked.connect(lambda: self._browse_file("7z.exe (7z.exe)", self.txt_path_7z))
        row7.addWidget(self.txt_path_7z)
        row7.addWidget(btn7)
        row7.addStretch()
        path_layout.addLayout(row7)

        rowr = QHBoxLayout()
        rowr.addWidget(BodyLabel("WinRAR.exe", self))
        self.txt_path_rar = LineEdit(self)
        self.txt_path_rar.setPlaceholderText("自動查找...")
        self.txt_path_rar.setText(self.settings.get("path_rar", ""))
        self.txt_path_rar.setMinimumWidth(300)
        btnr = PushButton("瀏覽", self)
        btnr.clicked.connect(lambda: self._browse_file("WinRAR.exe (WinRAR.exe)", self.txt_path_rar))
        rowr.addWidget(self.txt_path_rar)
        rowr.addWidget(btnr)
        rowr.addStretch()
        path_layout.addLayout(rowr)

        layout.addWidget(path_card)

        # ═══════════════════════════════════════════════
        #  分組3：高級設置
        # ═══════════════════════════════════════════════
        advanced_card = CardWidget(self)
        advanced_layout = QVBoxLayout(advanced_card)
        advanced_layout.setContentsMargins(20, 16, 20, 16)
        advanced_layout.setSpacing(12)

        advanced_title = StrongBodyLabel("🔧 高級設置", self)
        advanced_title.setStyleSheet("font-size: 15px; color: #333333;")
        advanced_layout.addWidget(advanced_title)

        advanced_layout.addLayout(self._make_spin_row(
            "遞歸深度上限",
            "防止無限遞歸，超過此層數將停止。建議 10~50",
            "max_recursion_depth", 5, 100
        ))

        switch_row = QHBoxLayout()
        switch_label_col = QVBoxLayout()
        switch_label = BodyLabel("遞歸解壓後刪除壓縮包", self)
        switch_hint = BodyLabel("內層壓縮包解壓成功後自動刪除原文件", self)
        switch_hint.setStyleSheet("color: #526174; font-size: 12px;")
        switch_label_col.addWidget(switch_label)
        switch_label_col.addWidget(switch_hint)

        self.switch_delete = SwitchButton(self)
        self.switch_delete.setOnText("開")
        self.switch_delete.setOffText("關")
        self.switch_delete.setChecked(self.settings.get("delete_after_extract", True))

        switch_row.addLayout(switch_label_col)
        switch_row.addStretch()
        switch_row.addWidget(self.switch_delete)
        advanced_layout.addLayout(switch_row)

        layout.addWidget(advanced_card)

        # ═══════════════════════════════════════════════
        #  按鈕區
        # ═══════════════════════════════════════════════
        btn_layout = QHBoxLayout()

        self.btn_reset = PushButton(FluentIcon.CANCEL, "恢復默認", self)
        self.btn_reset.clicked.connect(self.reset_defaults)

        self.btn_save = PrimaryPushButton(FluentIcon.SAVE, "保存設置", self)
        self.btn_save.setMinimumHeight(38)
        self.btn_save.clicked.connect(self.save_current)

        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        layout.addStretch()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _make_spin_row(self, label_text, hint_text, key, min_val, max_val):
        row = QHBoxLayout()
        label_col = QVBoxLayout()
        label = BodyLabel(label_text, self)
        hint = BodyLabel(hint_text, self)
        hint.setStyleSheet("color: #526174; font-size: 12px;")
        hint.setWordWrap(True)
        label_col.addWidget(label)
        label_col.addWidget(hint)

        spin = SpinBox(self)
        spin.setRange(min_val, max_val)
        spin.setValue(self.settings.get(key, DEFAULT_SETTINGS[key]))
        spin.setMinimumWidth(100)
        spin.setMaximumWidth(120)
        spin.setProperty("settings_key", key)
        self._spinboxes[key] = spin

        row.addLayout(label_col)
        row.addStretch()
        row.addWidget(spin)
        return row

    def _browse_file(self, filter_str, target_lineedit):
        f, _ = QFileDialog.getOpenFileName(self, "選擇文件", "", filter_str)
        if f:
            target_lineedit.setText(f)

    def save_current(self):
        self.settings["path_7z"] = self.txt_path_7z.text().strip()
        self.settings["path_rar"] = self.txt_path_rar.text().strip()
        self.settings["delete_after_extract"] = self.switch_delete.isChecked()
        for key, spin in self._spinboxes.items():
            self.settings[key] = spin.value()

        if save_settings(self.settings):
            effective = get_effective_settings()
            window = self.window()
            for name in ("extractor_interface", "all_in_one_interface"):
                panel = getattr(window, name, None)
                if panel is not None and not panel.running:
                    panel.txt_7z_path.setText(effective["path_7z"])
                    panel.txt_rar_path.setText(effective["path_rar"])
            InfoBar.success("已保存", "設置已保存，將在下次解壓任務時生效。", duration=3000, parent=self)
        else:
            InfoBar.error("錯誤", "保存設置失敗，請檢查文件權限。", duration=3000, parent=self)

    def reset_defaults(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.txt_path_7z.setText("")
        self.txt_path_rar.setText("")
        self.switch_delete.setChecked(DEFAULT_SETTINGS["delete_after_extract"])
        for key in DEFAULT_SETTINGS:
            if key in self._spinboxes:
                self._spinboxes[key].setValue(DEFAULT_SETTINGS[key])
        InfoBar.success("已重置", "已恢復爲默認設置（尚未保存）。", duration=2500, parent=self)


class LazyPage(QWidget):
    """頁面首次顯示或存取功能時建立；保持既有導覽與公開介面。"""
    def __init__(self, factory, name, parent):
        super().__init__(parent)
        self.setObjectName(name)
        self._factory = factory
        self._content = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

    def ensure_loaded(self):
        if self._content is None:
            self._content = self._factory(self)
            self._content.setObjectName(self.objectName() + "Content")
            self._layout.addWidget(self._content)
        return self._content

    def showEvent(self, event):
        self.ensure_loaded()
        super().showEvent(event)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self.ensure_loaded(), name)


# --- 主窗口 ---
class MainWindow(MSFluentWindow):
    def __init__(self):
        install_traditional_translations()
        super().__init__()
        self.setWindowTitle("一站式文件解壓助手 v6.1.0")
        self.resize(1100, 860)
        self.setMinimumSize(920, 760)
        from qfluentwidgets import setTheme, setThemeColor, Theme, setFontFamilies
        from PyQt5.QtGui import QIcon
        setTheme(Theme.LIGHT)
        setThemeColor(COLORS["accent"])
        setFontFamilies(["Microsoft JhengHei UI", "Microsoft JhengHei", "Segoe UI"])
        self.setMicaEffectEnabled(False)
        self.setBackgroundColor(QColor(COLORS["canvas"]))
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "Auto7z.ico")))
        self.setStyleSheet("MSFluentWindow { background: #F7F9FC; } BodyLabel { color: #1F2937; }")

        self.changer_interface = LazyPage(ExtensionChangerWidget, "ExtensionChangerWidget", self)
        self.extractor_interface = AutoExtractorWidget(self)
        self.all_in_one_interface = LazyPage(AllInOneWidget, "AllInOneWidget", self)
        self.settings_interface = LazyPage(SettingsWidget, "SettingsWidget", self)

        self.addSubInterface(self.changer_interface, FluentIcon.EDIT, "一鍵改後綴")
        self.addSubInterface(self.extractor_interface, FluentIcon.ZIP_FOLDER, "遞歸解壓")
        self.addSubInterface(self.all_in_one_interface, FluentIcon.SYNC, "改後綴解壓")
        self.addSubInterface(self.settings_interface, FluentIcon.SETTING, "設置",
                             position=NavigationItemPosition.BOTTOM)
        self.switchTo(self.extractor_interface)

    def closeEvent(self, event):
        panels = [self.extractor_interface]
        if self.all_in_one_interface._content is not None:
            panels.append(self.all_in_one_interface._content)
        if any(panel.running for panel in panels):
            for panel in panels:
                panel.cancel()
            InfoBar.warning("正在停止任務", "取消完成後即可關閉窗口。", parent=self)
            event.ignore()
            return
        super().closeEvent(event)


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    log("═══════════════════════════════════", "START")
    log("Auto7z v6.1.0 啓動 (雙引擎: 7z + WinRAR)", "START")
    s = get_effective_settings()
    log(f"7z:  {s['path_7z'] or '未找到'}")
    log(f"RAR: {s['path_rar'] or '未找到'}")
    log(f"目錄預檢等待={s['timeout_7z_precheck']}s；解壓不限總時長；停滯保護={s['idle_timeout_seconds']}s (0=關閉)")
    log("═══════════════════════════════════", "START")

    app = QApplication(sys.argv)
    if "--smoke-test" in sys.argv:
        import faulthandler
        fault_log = open(sys.argv[sys.argv.index("--smoke-test") + 1] + ".fault.log", "w")
        faulthandler.enable(file=fault_log)
    w = MainWindow()
    w.show()
    if "--smoke-test" in sys.argv:
        from PyQt5.QtCore import QTimer
        def smoke_test():
            import tempfile, zipfile
            from extraction import Engine
            report_path = sys.argv[sys.argv.index("--smoke-test") + 1]
            try:
                w.grab()
                with tempfile.TemporaryDirectory(prefix="auto7z-release-") as folder:
                    source = os.path.join(folder, "測試.zip")
                    with zipfile.ZipFile(source, "w") as z:
                        z.writestr("hello.txt", "Auto7z release smoke test")
                    result = Engine(find_7z_path(), "").process(source)
                    report = {"version": "6.1.0", "status": result.status,
                              "payload_correct": os.path.isfile(os.path.join(result.output, "hello.txt")),
                              "style": w.extractor_interface.progress_bar.visualStyle(),
                              "lazy_pages": w.settings_interface._content is None,
                              "translators": [not t.isEmpty() for t in app._auto7z_translators]}
                    with open(report_path, "w", encoding="utf-8") as f:
                        json.dump(report, f, ensure_ascii=False, indent=2)
                    app.exit(0 if result.status == "success" and report["payload_correct"] else 2)
            except Exception:
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump({"error": traceback.format_exc()}, f)
                app.exit(3)
        QTimer.singleShot(0, smoke_test)
    exit_code = app.exec_with_context() if hasattr(app, 'exec_with_context') else app.exec_()
    # Destroy native windows while Qt and Python callbacks are still alive.
    w.close()
    w.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    sys.exit(exit_code)

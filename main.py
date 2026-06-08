import os
import sys
import shutil
import subprocess
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QPoint, QThread, QObject
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QMenu, QAction
from PyQt5.QtGui import QPainter, QPen, QColor, QCursor
from qfluentwidgets import (MSFluentWindow, SubtitleLabel, PushButton, ComboBox,
                            LineEdit, ListWidget, FluentIcon, InfoBar, InfoBarPosition,
                            RoundMenu, Action, MessageBox, BodyLabel, PrimaryPushButton,
                            CardWidget, ProgressBar, ImageLabel, TextEdit)


# --- 1. 自定義圓角虛線拖拽區域組件 ---
class DragDropArea(QWidget):
    filesDropped = pyqtSignal(list)

    def __init__(self, text="將文件拖拽到此處，或點擊選擇文件", parent=None):
        super().__init__(parent=parent)
        self.text = text
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self.is_drag_over = False

        self.label = SubtitleLabel(self.text, self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)

    def resizeEvent(self, event):
        self.label.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.is_drag_over:
            pen = QPen(QColor(0, 151, 251), 2, Qt.DashLine)
            painter.setBrush(QColor(0, 151, 251, 18))
        else:
            pen = QPen(QColor(180, 180, 180), 1.5, Qt.DashLine)
            painter.setBrush(QColor(0, 0, 0, 8))

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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_drag_over = True
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_drag_over = False
            self.update()
            if hasattr(self, 'click_callback'):
                self.click_callback()


# --- 2. 支持右鍵選單和直接拖拽的通用列表組件 ---
class RightClickListWidget(ListWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.parent_widget = parent

        self.setStyleSheet("""
            ListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 5px;
                background-color: #ffffff;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: #f3f3f3;
            }
            QListWidget::item:selected {
                background-color: #eaeaea;
                color: #000000;
            }
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
        file_paths = [url.toLocalFile() for url in urls if os.path.isfile(url.toLocalFile())]
        if file_paths and self.parent_widget and hasattr(self.parent_widget, 'add_files_to_list'):
            event.accept()
            self.parent_widget.add_files_to_list(file_paths)

    def show_context_menu(self, pos: QPoint):
        item = self.itemAt(pos)
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background-color: #f3f3f3; border: 1px solid #cccccc; border-radius: 8px; padding: 4px; }\n"
            "QMenu::item { padding: 8px 24px 8px 20px; background-color: transparent; border-radius: 4px; }\n"
            "QMenu::item:selected { background-color: #e5e5e5; color: #000000; }")
        has_action = False
        if item:
            remove_action = QAction('❌ 從列表中移除該文件', menu)
            remove_action.triggered.connect(lambda: self.remove_selected_item(item))
            menu.addAction(remove_action)
            has_action = True
        if self.count() > 0:
            clear_action = QAction('🗑️ 清空所有文件', menu)
            clear_action.triggered.connect(self.clear_all_items)
            menu.addAction(clear_action)
            has_action = True
        if has_action:
            menu.exec_(QCursor.pos())

    def remove_selected_item(self, item):
        if item:
            text = item.text()
            if self.parent_widget and hasattr(self.parent_widget,
                                              'file_paths') and text in self.parent_widget.file_paths:
                self.parent_widget.file_paths.remove(text)
            self.takeItem(self.row(item))

    def clear_all_items(self):
        if self.parent_widget and hasattr(self.parent_widget, 'file_paths'):
            self.parent_widget.file_paths.clear()
        self.clear()


def find_7z_path():
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, "7z.exe")
        if os.path.exists(p): return p
    if os.path.exists("7z.exe"):
        return os.path.abspath("7z.exe")
    common_paths = ["C:\\Program Files\\7-Zip\\7z.exe", "C:\\Program Files\\(x86)\\7-Zip\\7z.exe"]
    for p in common_paths:
        if os.path.exists(p): return p
    return ""


# --- 3. 多線程核心：帶進度反饋的後台解壓任務工人類 ---
class ExtractionWorker(QObject):
    info_signal = pyqtSignal(str, str, int)  # 類型(success/error/warning), 訊息內容, 持續時間
    progress_signal = pyqtSignal(int, str)  # 實時進度值 (0-100), 當前操作描述文本
    finished_signal = pyqtSignal(int)  # 成功處理的文件數量

    def __init__(self, exe_path, file_paths, passwords, is_all_in_one=False, real_ext=""):
        super().__init__()
        self.exe_path = exe_path
        self.file_paths = file_paths
        self.passwords = passwords
        self.is_all_in_one = is_all_in_one
        self.real_ext = real_ext

    def extract_single_safe(self, archive_path, out_dir, password_list):
        if "" not in password_list:
            password_list = [""] + password_list

        for pwd in password_list:
            cmd = [self.exe_path, "x", archive_path, f"-o{out_dir}", "-y"]
            if pwd:
                cmd.append(f"-p{pwd}")
            try:
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode == 0:
                    return True
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill", "/F", "/IM", "7z.exe"], creationflags=subprocess.CREATE_NO_WINDOW)
                continue
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir, ignore_errors=True)
        return False

    def run(self):
        total_files = len(self.file_paths)
        success_files = 0
        archives_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz']

        for index, file_path in enumerate(self.file_paths):
            if not os.path.exists(file_path):
                continue

            filename = os.path.basename(file_path)
            # 發射信號：更新當前工作狀態描述
            self.progress_signal.emit(int((index / total_files) * 100),
                                      f"正在處理 ({index + 1}/{total_files}): {filename}")

            current_archive = file_path

            # 如果是一鍵聯動模式，先在後台靜默修改後綴
            if self.is_all_in_one:
                base_path, _ = os.path.splitext(file_path)
                real_archive_path = base_path + self.real_ext
                try:
                    counter = 1
                    while os.path.exists(real_archive_path):
                        real_archive_path = f"{base_path}_{counter}{self.real_ext}"
                        counter += 1
                    os.rename(file_path, real_archive_path)
                    current_archive = real_archive_path
                except Exception as e:
                    self.info_signal.emit("error", f"文件重命名失敗: {filename}", 3000)
                    continue

            # 準備解壓目錄
            base_dir = os.path.dirname(current_archive)
            base_name = os.path.splitext(os.path.basename(current_archive))[0]
            current_out_dir = os.path.join(base_dir, base_name)
            os.makedirs(current_out_dir, exist_ok=True)

            # 第一層解壓
            if not self.extract_single_safe(current_archive, current_out_dir, self.passwords):
                if self.is_all_in_one:
                    try:
                        os.rename(current_archive, file_path)
                    except:
                        pass
                self.info_signal.emit("warning", f"解壓失敗(密碼錯誤或損壞): {filename}", 3000)
                continue

            # 遞歸深層解壓
            has_new_archive = True
            loop_counter = 1
            while has_new_archive:
                has_new_archive = False
                for root, dirs, files in os.walk(current_out_dir):
                    for f in files:
                        full_path = os.path.join(root, f)
                        ext = os.path.splitext(f)[1].lower()
                        if ext in archives_extensions:
                            new_out_dir = os.path.join(root, os.path.splitext(f)[0])
                            os.makedirs(new_out_dir, exist_ok=True)

                            # 局部狀態微調提示
                            self.progress_signal.emit(int((index / total_files) * 100), f"正在遞歸深層解壓: {f}")

                            if self.extract_single_safe(full_path, new_out_dir, self.passwords):
                                has_new_archive = True
                                try:
                                    os.remove(full_path)
                                except:
                                    pass
                    if has_new_archive:
                        break
                loop_counter += 1
                if loop_counter > 20:
                    break

            success_files += 1

        # 任務完全結束，進度拉滿至 100%
        self.progress_signal.emit(100, "批量解壓任務完成！")
        self.finished_signal.emit(success_files)


# --- 功能一：一鍵改後綴介面 ---
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

        title_label = SubtitleLabel("一鍵修改文件擴展名", self)
        title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #202020;")
        layout.addWidget(title_label)

        self.drag_area = DragDropArea("🗂️ 將要改名的文件拖拽到此處，或點擊批量選擇", self)
        self.drag_area.filesDropped.connect(self.add_files_to_list)
        self.drag_area.click_callback = self.import_files
        layout.addWidget(self.drag_area)

        layout.addWidget(BodyLabel("待處理文件列表 (右鍵可移除特定項)：", self))

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

        card_layout.addWidget(BodyLabel("目標擴充名：", self))
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
        if files: self.add_files_to_list(files)

    def change_extensions(self):
        if not self.file_paths:
            InfoBar.warning("提示", "請先導入文件！", duration=2000, parent=self)
            return
        target_ext = self.combo_ext.currentText()
        success_count = 0
        for file_path in list(self.file_paths):
            if os.path.exists(file_path):
                base, _ = os.path.splitext(file_path)
                new_path = base + target_ext
                try:
                    counter = 1
                    while os.path.exists(new_path):
                        new_path = f"{base}_{counter}{target_ext}"
                        counter += 1
                    os.rename(file_path, new_path)
                    success_count += 1
                except Exception as e:
                    print(f"修改失敗: {e}")
        InfoBar.success("成功", f"成功修改 {success_count} 個文件的後綴！", duration=3000, parent=self)
        self.list_widget.clear_all_items()


# --- 功能二：多文件遞歸解壓介面 (包含進度條) ---
class AutoExtractorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("AutoExtractorWidget")
        self.file_paths = []
        self.init_ui()
        self.txt_7z_path.setText(find_7z_path())

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(14)

        title_label = SubtitleLabel("多層壓縮包一鍵遞歸解壓 (實時進度可視化)", self)
        title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #202020;")
        layout.addWidget(title_label)

        path_card = CardWidget(self)
        path_layout = QHBoxLayout(path_card)
        path_layout.setContentsMargins(15, 10, 15, 10)
        self.txt_7z_path = LineEdit(self)
        self.btn_browse_7z = PushButton("瀏覽...", self)
        self.btn_browse_7z.clicked.connect(self.browse_7z)
        path_layout.addWidget(BodyLabel("7z 軟體路徑:", self))
        path_layout.addWidget(self.txt_7z_path)
        path_layout.addWidget(self.btn_browse_7z)
        layout.addWidget(path_card)

        self.drag_area = DragDropArea("📦 將多個待解壓的壓縮包拖拽到此處，或點擊批量選擇", self)
        self.drag_area.filesDropped.connect(self.add_files_to_list)
        self.drag_area.click_callback = self.browse_target
        layout.addWidget(self.drag_area)

        layout.addWidget(BodyLabel("待處理處理壓縮包列表：", self))
        self.list_widget = RightClickListWidget(self)
        layout.addWidget(self.list_widget)

        param_card = CardWidget(self)
        param_layout = QVBoxLayout(param_card)
        param_layout.setContentsMargins(15, 12, 15, 12)
        param_layout.setSpacing(6)
        param_layout.addWidget(BodyLabel("解壓密碼庫 (多個密碼請用逗號 ',' 或換行分隔)：", self))
        self.txt_password = TextEdit(self)
        self.txt_password.setPlaceholderText("例如: password123, 123456\n程序會自動嘗試無密碼及上述密碼庫。")
        self.txt_password.setMaximumHeight(80)
        param_layout.addWidget(self.txt_password)
        layout.addWidget(param_card)

        # ✨【新增】UI 進度條可視化渲染區
        self.progress_label = BodyLabel("等待任務啟動...", self)
        self.progress_label.setStyleSheet("color: #666666; font-weight: 500;")
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()  # 默認隱藏，工作時顯示
        self.progress_label.hide()
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.btn_clear = PushButton(FluentIcon.DELETE, "清空列表", self)
        self.btn_clear.clicked.connect(self.list_widget.clear_all_items)

        self.btn_extract = PrimaryPushButton(FluentIcon.DOWNLOAD, "開始批量遞歸解壓", self)
        self.btn_extract.setMinimumHeight(40)
        self.btn_extract.clicked.connect(self.start_extraction)

        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_extract)
        layout.addLayout(btn_layout)

    def browse_7z(self):
        file, _ = QFileDialog.getOpenFileName(self, "選取 7z.exe", "C:\\", "7z Tool (7z.exe)")
        if file: self.txt_7z_path.setText(file)

    def browse_target(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇壓縮文件", "", "Archive Files (*.zip *.rar *.7z *.tar *.gz)")
        if files: self.add_files_to_list(files)

    def add_files_to_list(self, files):
        for f in files:
            if f not in self.file_paths:
                self.file_paths.append(f)
                self.list_widget.addItem(f)

    def get_passwords(self):
        raw_text = self.txt_password.toPlainText().strip()
        if not raw_text: return [""]
        raw_text = raw_text.replace("\n", ",")
        return [p.strip() for p in raw_text.split(",") if p.strip()]

    # ✨【新增】接收子線程進度信號的槽函數
    def handle_worker_progress(self, value, status_text):
        self.progress_bar.setValue(value)
        self.progress_label.setText(status_text)

    def handle_worker_info(self, type_str, msg, duration):
        if type_str == "error":
            InfoBar.error("錯誤", msg, duration=duration, parent=self)
        elif type_str == "warning":
            InfoBar.warning("提示", msg, duration=duration, parent=self)

    def handle_worker_finished(self, success_files):
        self.btn_extract.setEnabled(True)
        self.btn_extract.setText("開始批量遞歸解壓")
        self.list_widget.clear_all_items()

        # 延遲隱藏進度條
        self.progress_bar.hide()
        self.progress_label.hide()

        InfoBar.success("任務完成", f"後台批量解壓完成！成功處理 {success_files} 個壓縮包。", duration=5000, parent=self)

        self.thread.quit()
        self.thread.wait()

    def start_extraction(self):
        exe_path = self.txt_7z_path.text().strip()
        if not os.path.exists(exe_path):
            InfoBar.error("錯誤", "7z.exe 路徑不正確！", duration=3000, parent=self)
            return
        if not self.file_paths:
            InfoBar.error("錯誤", "請先導入至少一個壓縮包！", duration=3000, parent=self)
            return

        passwords = self.get_passwords()

        # 顯示並重置進度條状态
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.setText("正在初始化線程...")
        self.progress_label.show()

        self.btn_extract.setEnabled(False)
        self.btn_extract.setText("解壓任務運行中...")

        self.thread = QThread()
        self.worker = ExtractionWorker(exe_path, list(self.file_paths), passwords, is_all_in_one=False)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress_signal.connect(self.handle_worker_progress)  # ✨ 綁定進度反饋
        self.worker.info_signal.connect(self.handle_worker_info)
        self.worker.finished_signal.connect(self.handle_worker_finished)

        self.thread.start()


# --- 功能三：一鍵改名+遞歸解壓聯動介面 (包含進度条) ---
class AllInOneWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("AllInOneWidget")
        self.file_paths = []
        self.init_ui()
        self.txt_7z_path.setText(find_7z_path())

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(14)

        title_label = SubtitleLabel("一鍵還原真實後綴並遞歸解壓", self)
        title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #202020;")
        layout.addWidget(title_label)

        path_card = CardWidget(self)
        path_layout = QHBoxLayout(path_card)
        path_layout.setContentsMargins(15, 10, 15, 10)
        self.txt_7z_path = LineEdit(self)
        path_layout.addWidget(BodyLabel("7z 軟體路徑:", self))
        path_layout.addWidget(self.txt_7z_path)
        layout.addWidget(path_card)

        self.drag_area = DragDropArea("✨ 將偽裝後綴的壓縮包批量拖入此處", self)
        self.drag_area.filesDropped.connect(self.add_files_to_list)
        self.drag_area.click_callback = self.browse_target
        layout.addWidget(self.drag_area)

        layout.addWidget(BodyLabel("待處理被偽裝文件列表：", self))
        self.list_widget = RightClickListWidget(self)
        layout.addWidget(self.list_widget)

        config_card = CardWidget(self)
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(15, 12, 15, 12)
        config_layout.setSpacing(8)

        setup_layout = QHBoxLayout()
        self.combo_real_ext = ComboBox(self)
        self.combo_real_ext.addItems([".zip", ".rar", ".7z", ".tar"])
        setup_layout.addWidget(BodyLabel("真實擴充名:", self))
        setup_layout.addWidget(self.combo_real_ext)
        setup_layout.addStretch()
        config_layout.addLayout(setup_layout)

        config_layout.addWidget(BodyLabel("解壓密碼庫 (多個請用逗號或換行分隔)：", self))
        self.txt_password = TextEdit(self)
        self.txt_password.setPlaceholderText("選填，若有解壓密碼請寫在這裡")
        self.txt_password.setMaximumHeight(60)
        config_layout.addWidget(self.txt_password)
        layout.addWidget(config_card)

        # ✨【新增】UI 進度條可視化渲染區
        self.progress_label = BodyLabel("等待聯動任務啟動...", self)
        self.progress_label.setStyleSheet("color: #666666; font-weight: 500;")
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.progress_label.hide()
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.btn_clear = PushButton(FluentIcon.DELETE, "清空列表", self)
        self.btn_clear.clicked.connect(self.list_widget.clear_all_items)

        self.btn_run = PrimaryPushButton(FluentIcon.PLAY, "啟動：還原後綴 ➡️ 批量遞歸解壓", self)
        self.btn_run.setMinimumHeight(42)
        self.btn_run.clicked.connect(self.process_all_in_one)

        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_run)
        layout.addLayout(btn_layout)

    def browse_target(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇被偽裝的文件", "", "All Files (*)")
        if files: self.add_files_to_list(files)

    def add_files_to_list(self, files):
        for f in files:
            if f not in self.file_paths:
                self.file_paths.append(f)
                self.list_widget.addItem(f)

    def get_passwords(self):
        raw_text = self.txt_password.toPlainText().strip()
        if not raw_text: return [""]
        raw_text = raw_text.replace("\n", ",")
        return [p.strip() for p in raw_text.split(",") if p.strip()]

    # ✨【新增】接收進度信號
    def handle_worker_progress(self, value, status_text):
        self.progress_bar.setValue(value)
        self.progress_label.setText(status_text)

    def handle_worker_info(self, type_str, msg, duration):
        if type_str == "error":
            InfoBar.error("錯誤", msg, duration=duration, parent=self)
        elif type_str == "warning":
            InfoBar.warning("提示", msg, duration=duration, parent=self)

    def handle_worker_finished(self, success_files):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("啟動：還原後綴 ➡️ 批量遞歸解壓")
        self.list_widget.clear_all_items()

        self.progress_bar.hide()
        self.progress_label.hide()

        InfoBar.success("大功告成", f"一鍵聯動處理完成！成功處理 {success_files} 個文件。", duration=6000, parent=self)

        self.thread.quit()
        self.thread.wait()

    def process_all_in_one(self):
        exe_path = self.txt_7z_path.text().strip()
        real_ext = self.combo_real_ext.currentText()
        passwords = self.get_passwords()

        if not os.path.exists(exe_path):
            InfoBar.error("錯誤", "7z.exe 路徑不正確！", duration=3000, parent=self)
            return
        if not self.file_paths:
            InfoBar.error("錯誤", "請先選擇被偽裝的文件！", duration=3000, parent=self)
            return

        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.setText("正在配置聯動後台...")
        self.progress_label.show()

        self.btn_run.setEnabled(False)
        self.btn_run.setText("聯動任務執行中...")

        self.thread = QThread()
        self.worker = ExtractionWorker(exe_path, list(self.file_paths), passwords, is_all_in_one=True,
                                       real_ext=real_ext)
        self.moveToThread(self.thread)  # 安全綁定
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress_signal.connect(self.handle_worker_progress)  # ✨ 綁定進度反饋
        self.worker.info_signal.connect(self.handle_worker_info)
        self.worker.finished_signal.connect(self.handle_worker_finished)

        self.thread.start()


# --- 主窗口導航橋接 ---
class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("一站式文件解壓助手 v4.0")
        self.resize(1000, 850)

        self.changer_interface = ExtensionChangerWidget(self)
        self.extractor_interface = AutoExtractorWidget(self)
        self.all_in_one_interface = AllInOneWidget(self)

        self.addSubInterface(self.changer_interface, FluentIcon.EDIT, "一鍵改後綴")
        self.addSubInterface(self.extractor_interface, FluentIcon.ZIP_FOLDER, "文件遞歸解壓")
        self.addSubInterface(self.all_in_one_interface, FluentIcon.SYNC, "改后缀解压")


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_with_context() if hasattr(app, 'exec_with_context') else app.exec_())
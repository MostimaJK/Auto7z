import os
import sys
import shutil
import subprocess
import time
import json
import traceback
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QThread, QObject
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QFileDialog, QMenu, QAction, QMessageBox)
from PyQt5.QtGui import QPainter, QPen, QColor, QCursor
from qfluentwidgets import (MSFluentWindow, SubtitleLabel, PushButton, ComboBox,
                            LineEdit, ListWidget, FluentIcon, InfoBar,
                            BodyLabel, PrimaryPushButton, CardWidget, ProgressBar,
                            TextEdit, SpinBox, SwitchButton, ScrollArea,
                            StrongBodyLabel, NavigationItemPosition)


# ═══════════════════════════════════════════════════════════════
#  全局异常钩子
# ═══════════════════════════════════════════════════════════════
def global_exception_hook(exc_type, exc_value, exc_tb):
    tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"[FATAL] {tb_str}", flush=True)
    QMessageBox.critical(None, "程序异常", f"发生未捕获的异常：\n\n{tb_str}")
    sys.exit(1)

sys.excepthook = global_exception_hook


# ═══════════════════════════════════════════════════════════════
#  日志 & 配置
# ═══════════════════════════════════════════════════════════════
def log(msg, level="INFO"):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}", flush=True)


SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULT_SETTINGS = {
    "timeout_7z_precheck": 3,
    "timeout_no_password": 5,
    "timeout_rar_no_password": 5,       # ★ WinRAR 无密码超时（加密包秒级返回）
    "timeout_7z_extract": 30,
    "timeout_rar_extract": 60,
    "max_recursion_depth": 20,
    "path_7z": "",
    "path_rar": "",
    "delete_after_extract": True,
}


def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            merged.update(data)
            return merged
    except Exception as e:
        log(f"加载设置失败: {e}", "WARN")
    return DEFAULT_SETTINGS.copy()


def save_settings(settings_dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings_dict, f, indent=4, ensure_ascii=False)
        log("设置已保存", "OK")
        return True
    except Exception as e:
        log(f"保存设置失败: {e}", "ERROR")
        return False


# ═══════════════════════════════════════════════════════════════
#  路径查找
# ═══════════════════════════════════════════════════════════════
def find_7z_path():
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, "7z.exe")
        if os.path.exists(p): return p
    if os.path.exists("7z.exe"):
        return os.path.abspath("7z.exe")
    for p in ["C:\\Program Files\\7-Zip\\7z.exe",
              "C:\\Program Files\\(x86)\\7-Zip\\7z.exe"]:
        if os.path.exists(p): return p
    return ""


def find_rar_path():
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, "WinRAR.exe")
        if os.path.exists(p): return p
    if os.path.exists("WinRAR.exe"):
        return os.path.abspath("WinRAR.exe")
    for p in ["C:\\Program Files\\WinRAR\\WinRAR.exe",
              "C:\\Program Files\\(x86)\\WinRAR\\WinRAR.exe"]:
        if os.path.exists(p): return p
    return ""


def get_effective_settings():
    s = load_settings()
    if not s["path_7z"]:
        s["path_7z"] = find_7z_path()
    if not s["path_rar"]:
        s["path_rar"] = find_rar_path()
    return s


# --- 1. 拖拽区域 ---
class DragDropArea(QWidget):
    filesDropped = pyqtSignal(list)

    def __init__(self, text="将文件拖拽到此处，或点击选择文件", parent=None):
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

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_drag_over = False
            self.update()
            if self.click_callback:
                self.click_callback()


# --- 2. 右键列表 ---
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
                padding: 8px; border-radius: 4px; margin-bottom: 2px;
            }
            QListWidget::item:hover { background-color: #f3f3f3; }
            QListWidget::item:selected { background-color: #eaeaea; color: #000000; }
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
            menu.addAction(QAction('❌ 移除该文件', menu,
                                   triggered=lambda: self.remove_selected_item(item)))
        if self.count() > 0:
            menu.addAction(QAction('🗑️ 清空所有文件', menu,
                                   triggered=self.clear_all_items))
        if not menu.isEmpty():
            menu.exec_(QCursor.pos())

    def remove_selected_item(self, item):
        if item:
            text = item.text()
            if self.parent_widget and hasattr(self.parent_widget, 'file_paths') and text in self.parent_widget.file_paths:
                self.parent_widget.file_paths.remove(text)
            self.takeItem(self.row(item))

    def clear_all_items(self):
        if self.parent_widget and hasattr(self.parent_widget, 'file_paths'):
            self.parent_widget.file_paths.clear()
        self.clear()


# --- 3. 解压 Worker ---
class ExtractionWorker(QObject):
    info_signal = pyqtSignal(str, str, int)
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(int)

    def __init__(self, exe_7z_path, exe_rar_path, file_paths, passwords,
                 is_all_in_one=False, real_ext="", engine_mode="auto",
                 timeout_7z_precheck=8,
                 timeout_no_password=20,
                 timeout_rar_no_password=5,
                 timeout_7z_extract=30,
                 timeout_rar_extract=60,
                 max_recursion_depth=20,
                 delete_after_extract=True):
        super().__init__()
        self.exe_7z_path = exe_7z_path
        self.exe_rar_path = exe_rar_path
        self.file_paths = file_paths
        self.passwords = passwords
        self.is_all_in_one = is_all_in_one
        self.real_ext = real_ext
        self.engine_mode = engine_mode
        self.timeout_7z_precheck = timeout_7z_precheck
        self.timeout_no_password = timeout_no_password
        self.timeout_rar_no_password = timeout_rar_no_password
        self.timeout_7z_extract = timeout_7z_extract
        self.timeout_rar_extract = timeout_rar_extract
        self.max_recursion_depth = max_recursion_depth
        self.delete_after_extract = delete_after_extract

    # ══════════════════════════════════════════════════════
    #  预检：返回 (can_extract, tool, is_fully_encrypted)
    # ══════════════════════════════════════════════════════
    def _precheck_archive(self, archive_path):
        archive_name = os.path.basename(archive_path)
        log(f"├─ 预检文件: {archive_name}")
        log(f"│  解压模式: {self.engine_mode}")

        if self.engine_mode == "7z":
            ok, encrypted = self._precheck_7z(archive_path)
            return ok, "7z" if ok else None, encrypted

        if self.engine_mode == "winrar":
            log(f"│  WinRAR 模式，跳过预检")
            return True, "winrar", False  # 不预检，不知道是否加密

        # Auto：7z 预检
        ok, encrypted = self._precheck_7z(archive_path)
        if ok:
            return True, "7z", encrypted

        log(f"│  7z 预检失败，直接切换到 WinRAR")
        return True, "winrar", False  # WinRAR 不预检，不知道是否加密

    def _precheck_7z(self, archive_path):
        """
        7z 预检。用 -slt 列出详细信息，检测是否全加密。
        返回 (success: bool, is_fully_encrypted: bool)
        """
        if not self.exe_7z_path or not os.path.exists(self.exe_7z_path):
            log(f"│  7z 路径无效，跳过")
            return False, False

        cmd = [self.exe_7z_path, "l", "-slt", archive_path]
        log(f"│  7z 测试: 7z l -slt ...")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=self.timeout_7z_precheck,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                last = result.stderr.strip().split('\n')[-1] if result.stderr.strip() else "(空)"
                log(f"│  ✘ 7z 预检失败: {last}")
                return False, False

            # 解析输出，统计 Encrypted = + 的文件
            lines = result.stdout.split('\n')
            total_files = 0
            encrypted_files = 0

            for line in lines:
                stripped = line.strip()
                if stripped == "Encrypted = +":
                    encrypted_files += 1
                elif stripped.startswith("Path ="):
                    total_files += 1

            is_fully_encrypted = (total_files > 0 and encrypted_files == total_files)

            if is_fully_encrypted:
                log(f"│  ✔ 7z 预检通过 (全加密，{total_files} 个文件)", "OK")
            else:
                log(f"│  ✔ 7z 预检通过 ({total_files} 个文件, {encrypted_files} 个加密)", "OK")

            return True, is_fully_encrypted

        except subprocess.TimeoutExpired:
            log(f"│  ✘ 7z 预检超时 ({self.timeout_7z_precheck}s)", "WARN")
            return False, False
        except Exception as e:
            log(f"│  ✘ 7z 预检异常: {e}", "ERROR")
            return False, False

    # ══════════════════════════════════════════════════════
    #  解压入口
    # ══════════════════════════════════════════════════════
    def extract_single_safe(self, archive_path, out_dir, password_list, tool,
                            skip_no_password=False):
        if tool == "winrar":
            return self._extract_with_rar(archive_path, out_dir, password_list,
                                          skip_no_password)
        else:
            return self._extract_with_7z(archive_path, out_dir, password_list,
                                         skip_no_password)

    # ══════════════════════════════════════════════════════
    #  7z 解压
    # ══════════════════════════════════════════════════════
    def _extract_with_7z(self, archive_path, out_dir, password_list,
                         skip_no_password=False):
        archive_name = os.path.basename(archive_path)

        # ── 如果给了密码，密码优先 ──
        if password_list:
            log(f"├─ [7z] 已提供密码，优先尝试密码解压: {archive_name}")
            log(f"│  共 {len(password_list)} 个密码")
            for i, pwd in enumerate(password_list, 1):
                if not pwd or pwd.strip() == "":
                    continue
                masked = pwd if len(pwd) <= 2 else f"{pwd[0]}***{pwd[-1]}"
                log(f"│  [{i}/{len(password_list)}] 密码: {masked}")
                cmd = [self.exe_7z_path, "x", archive_path, f"-o{out_dir}", "-y", f"-p{pwd}"]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True,
                                            timeout=self.timeout_7z_extract,
                                            creationflags=subprocess.CREATE_NO_WINDOW)
                    if result.returncode == 0:
                        log(f"│  ✔ [7z] 密码解压成功!", "OK")
                        return True
                    else:
                        last = result.stderr.strip().split('\n')[-1] if result.stderr.strip() else "(空)"
                        if "wrong password" in last.lower():
                            log(f"│  密码错误")
                        else:
                            log(f"│  失败: {last}")
                except subprocess.TimeoutExpired:
                    log(f"│  超时")
                    subprocess.run(["taskkill", "/F", "/IM", "7z.exe"],
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception as e:
                    log(f"│  异常: {e}")

            # 所有密码都失败，尝试无密码兜底
            if skip_no_password:
                log(f"│  所有密码失败，且预检判定全加密，跳过无密码兜底")
                if os.path.exists(out_dir):
                    shutil.rmtree(out_dir, ignore_errors=True)
                return False
            log(f"│  所有密码失败，尝试无密码兜底...")
        else:
            if skip_no_password:
                log(f"├─ [7z] 预检判定全加密且无密码，无法解压: {archive_name}")
                return False
            log(f"├─ [7z] 尝试无密码解压: {archive_name}")

        # ── 无密码解压 ──
        cmd = [self.exe_7z_path, "x", archive_path, f"-o{out_dir}", "-y"]
        log(f"│  命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=self.timeout_no_password,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                log(f"│  ✔ [7z] 无密码解压成功", "OK")
                return True
            else:
                last = result.stderr.strip().split('\n')[-1] if result.stderr.strip() else "(空)"
                log(f"│  ✘ [7z] 无密码失败: {last}")
        except subprocess.TimeoutExpired:
            log(f"│  ✘ [7z] 无密码超时 ({self.timeout_no_password}s)", "WARN")
            subprocess.run(["taskkill", "/F", "/IM", "7z.exe"],
                           creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            log(f"│  ✘ [7z] 异常: {e}", "ERROR")

        if os.path.exists(out_dir):
            shutil.rmtree(out_dir, ignore_errors=True)
        return False

    # ══════════════════════════════════════════════════════
    #  WinRAR 解压
    # ══════════════════════════════════════════════════════
    def _extract_with_rar(self, archive_path, out_dir, password_list,
                          skip_no_password=False):
        archive_name = os.path.basename(archive_path)

        need_temp = (' ' in out_dir or any(ord(c) > 127 for c in out_dir))
        actual_out_dir = out_dir

        if need_temp:
            temp_base = os.path.dirname(out_dir)
            temp_dir = os.path.join(temp_base, f"_rar_tmp_{os.getpid()}_{int(time.time())}")
            os.makedirs(temp_dir, exist_ok=True)
            log(f"│  路径含空格/中文，使用临时目录: {os.path.basename(temp_dir)}")
        else:
            temp_dir = out_dir

        success = False

        # ── 如果给了密码，密码优先 ──
        if password_list:
            log(f"├─ [WinRAR] 已提供密码，优先尝试密码解压: {archive_name}")
            log(f"│  共 {len(password_list)} 个密码")
            for i, pwd in enumerate(password_list, 1):
                if not pwd or pwd.strip() == "":
                    continue
                masked = pwd if len(pwd) <= 2 else f"{pwd[0]}***{pwd[-1]}"
                log(f"│  [{i}/{len(password_list)}] 密码: {masked}")
                cmd = [self.exe_rar_path, "x", "-y", "-o+", f"-p{pwd}", archive_path, temp_dir + "\\"]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True,
                                            timeout=self.timeout_rar_extract,
                                            creationflags=subprocess.CREATE_NO_WINDOW)
                    if result.returncode == 0:
                        log(f"│  ✔ [WinRAR] 密码解压成功!", "OK")
                        success = True
                        break
                    else:
                        last = result.stderr.strip().split('\n')[-1] if result.stderr.strip() else "(空)"
                        log(f"│  失败: {last}")
                except subprocess.TimeoutExpired:
                    log(f"│  超时")
                except Exception as e:
                    log(f"│  异常: {e}")

            # 所有密码失败，无密码兜底
            if not success:
                if skip_no_password:
                    log(f"│  所有密码失败，且预检判定全加密，跳过无密码兜底")
                else:
                    log(f"│  所有密码失败，尝试无密码兜底...")
                    cmd = [self.exe_rar_path, "x", "-y", "-o+", archive_path, temp_dir + "\\"]
                    log(f"│  命令: {' '.join(cmd)}")
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True,
                                                timeout=self.timeout_rar_no_password,
                                                creationflags=subprocess.CREATE_NO_WINDOW)
                        if result.returncode == 0:
                            log(f"│  ✔ [WinRAR] 无密码兜底成功", "OK")
                            success = True
                        else:
                            last = result.stderr.strip().split('\n')[-1] if result.stderr.strip() else "(空)"
                            log(f"│  ✘ [WinRAR] 无密码失败: {last}")
                    except subprocess.TimeoutExpired:
                        log(f"│  ✘ [WinRAR] 无密码超时 ({self.timeout_rar_no_password}s)", "WARN")
                    except Exception as e:
                        log(f"│  ✘ [WinRAR] 异常: {e}", "ERROR")
        else:
            # 无密码，直接无密码解压
            if skip_no_password:
                log(f"├─ [WinRAR] 预检判定全加密且无密码，无法解压: {archive_name}")
                # success 保持 False
            else:
                log(f"├─ [WinRAR] 尝试无密码解压: {archive_name}")
                cmd = [self.exe_rar_path, "x", "-y", "-o+", archive_path, temp_dir + "\\"]
                log(f"│  命令: {' '.join(cmd)}")
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True,
                                            timeout=self.timeout_rar_no_password,
                                            creationflags=subprocess.CREATE_NO_WINDOW)
                    if result.returncode == 0:
                        log(f"│  ✔ [WinRAR] 无密码解压成功", "OK")
                        success = True
                    else:
                        last = result.stderr.strip().split('\n')[-1] if result.stderr.strip() else "(空)"
                        log(f"│  ✘ [WinRAR] 无密码失败: {last}")
                except subprocess.TimeoutExpired:
                    log(f"│  ✘ [WinRAR] 无密码超时 ({self.timeout_rar_no_password}s)", "WARN")
                except Exception as e:
                    log(f"│  ✘ [WinRAR] 异常: {e}", "ERROR")

        # ── 移动临时目录文件 ──
        if need_temp and success:
            log(f"│  移动文件到目标目录...")
            try:
                os.makedirs(actual_out_dir, exist_ok=True)
                for item in os.listdir(temp_dir):
                    src = os.path.join(temp_dir, item)
                    dst = os.path.join(actual_out_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                log(f"│  ✔ 移动完成")
            except Exception as e:
                log(f"│  ✘ 移动失败: {e}", "ERROR")
                success = False

        if need_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)
            log(f"│  已清理临时目录")

        if not success:
            if os.path.exists(actual_out_dir):
                shutil.rmtree(actual_out_dir, ignore_errors=True)
            if os.path.exists(out_dir) and out_dir != actual_out_dir:
                shutil.rmtree(out_dir, ignore_errors=True)

        return success

    # ══════════════════════════════════════════════════════
    #  主运行
    # ══════════════════════════════════════════════════════
    def run(self):
        total_files = len(self.file_paths)
        success_files = 0
        archives_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz']

        log("═" * 60)
        log(f"开始批量解压，共 {total_files} 个文件", "START")
        log(f"7z: {self.exe_7z_path}  |  WinRAR: {self.exe_rar_path}")
        log(f"模式: {self.engine_mode}  密码数: {len(self.passwords)}")
        log(f"超时: 预检={self.timeout_7z_precheck}s 无密码={self.timeout_no_password}s "
            f"RAR无密码={self.timeout_rar_no_password}s "
            f"7z有密码={self.timeout_7z_extract}s RAR有密码={self.timeout_rar_extract}s")
        log(f"递归深度上限: {self.max_recursion_depth}")
        log("═" * 60)

        for index, file_path in enumerate(self.file_paths):
            if not os.path.exists(file_path):
                log(f"文件不存在，跳过: {file_path}", "WARN")
                continue

            filename = os.path.basename(file_path)
            log(f"\n▸ [{index+1}/{total_files}] {filename}")
            self.progress_signal.emit(int((index / total_files) * 100),
                                      f"正在处理 ({index + 1}/{total_files}): {filename}")

            current_archive = file_path

            if self.is_all_in_one:
                base_path, _ = os.path.splitext(file_path)
                real_archive_path = base_path + self.real_ext
                if real_archive_path != file_path:
                    try:
                        counter = 1
                        while os.path.exists(real_archive_path):
                            real_archive_path = f"{base_path}_{counter}{self.real_ext}"
                            counter += 1
                        os.rename(file_path, real_archive_path)
                        current_archive = real_archive_path
                        log(f"  后缀已修改: {filename} → {os.path.basename(real_archive_path)}")
                    except Exception as e:
                        log(f"  ✘ 重命名失败: {e}", "ERROR")
                        self.info_signal.emit("error", f"重命名失败: {filename}", 3000)
                        continue
                else:
                    log(f"  后缀已为目标格式，跳过重命名")

            base_dir = os.path.dirname(current_archive)
            base_name = os.path.splitext(os.path.basename(current_archive))[0]
            current_out_dir = os.path.join(base_dir, base_name)
            original_out_dir = current_out_dir
            counter = 1
            while os.path.exists(current_out_dir):
                current_out_dir = f"{original_out_dir}_{counter}"
                counter += 1

            try:
                os.makedirs(current_out_dir, exist_ok=True)
            except Exception as e:
                log(f"  ✘ 无法创建目录: {e}", "ERROR")
                self.info_signal.emit("warning", f"无法创建目录: {filename}", 3000)
                continue

            log(f"  ── 第1层解压 ──")
            can_extract, tool, is_encrypted = self._precheck_archive(current_archive)

            if not can_extract:
                log(f"  ✘ 无法识别，跳过", "ERROR")
                self._restore_name(current_archive, file_path)
                self.info_signal.emit("warning", f"无法识别: {filename}", 3000)
                self._clean_empty_dir(current_out_dir)
                continue

            log(f"  使用引擎: {tool}" +
                (" (全加密，跳过无密码)" if is_encrypted else ""))

            if not self.extract_single_safe(current_archive, current_out_dir,
                                            self.passwords, tool=tool,
                                            skip_no_password=is_encrypted):
                self._restore_name(current_archive, file_path)
                self.info_signal.emit("warning", f"解压失败: {filename}", 3000)
                continue

            log(f"  ✔ 第1层解压完成")
            self.info_signal.emit("success", f"解压成功: {filename}", 2000)

            # 递归深层解压
            has_new_archive = True
            loop_counter = 1
            total_inner_extracted = 0

            while has_new_archive:
                has_new_archive = False
                log(f"  ── 递归扫描第{loop_counter}轮 ──")

                for root, dirs, files in os.walk(current_out_dir):
                    for f in files:
                        full_path = os.path.join(root, f)
                        ext = os.path.splitext(f)[1].lower()
                        if ext not in archives_extensions:
                            continue

                        raw_out_dir = os.path.join(root, os.path.splitext(f)[0])
                        c2 = 1
                        new_out_dir = raw_out_dir
                        while os.path.exists(new_out_dir):
                            new_out_dir = f"{raw_out_dir}_{c2}"
                            c2 += 1

                        log(f"    发现内层: {f}")
                        self.progress_signal.emit(
                            int((index / total_files) * 100),
                            f"递归解压: {f}"
                        )

                        try:
                            os.makedirs(new_out_dir, exist_ok=True)
                            can_extract_inner, tool_inner, inner_encrypted = \
                                self._precheck_archive(full_path)

                            if not can_extract_inner:
                                log(f"    ✘ 内层无法识别: {f}", "WARN")
                                self._clean_empty_dir(new_out_dir)
                                continue

                            log(f"    内层引擎: {tool_inner}" +
                                (" (全加密，跳过无密码)" if inner_encrypted else ""))

                            if self.extract_single_safe(full_path, new_out_dir,
                                                        self.passwords,
                                                        tool=tool_inner,
                                                        skip_no_password=inner_encrypted):
                                has_new_archive = True
                                total_inner_extracted += 1
                                log(f"    ✔ 内层解压成功: {f}")
                                self.info_signal.emit("success", f"递归解压: {f}", 1500)
                                if self.delete_after_extract:
                                    try:
                                        os.remove(full_path)
                                        log(f"    已删除内层压缩包")
                                    except Exception as e:
                                        log(f"    ⚠ 无法删除: {e}")
                            else:
                                log(f"    ✘ 内层解压失败: {f}", "WARN")
                                self._clean_empty_dir(new_out_dir)
                        except Exception as e:
                            log(f"    ✘ 递归异常: {e}", "ERROR")
                            self.info_signal.emit("warning", f"递归跳过: {f}", 2000)
                            continue

                    if has_new_archive:
                        break

                loop_counter += 1
                if loop_counter > self.max_recursion_depth:
                    log(f"  ⚠ 递归深度超过{self.max_recursion_depth}层，终止", "WARN")
                    break

            if total_inner_extracted > 0:
                log(f"  ✔ 共递归解压 {total_inner_extracted} 个内层压缩包")
            else:
                log(f"  - 无内层压缩包")

            success_files += 1

        log(f"\n{'═' * 60}")
        log(f"任务结束: 成功 {success_files}/{total_files}", "DONE")
        log(f"{'═' * 60}")

        self.progress_signal.emit(100, "批量解压完成！")
        self.finished_signal.emit(success_files)

    def _restore_name(self, current_archive, original_path):
        if self.is_all_in_one and current_archive != original_path:
            try:
                os.rename(current_archive, original_path)
                log(f"  已还原文件名: {os.path.basename(original_path)}")
            except:
                pass

    def _clean_empty_dir(self, dir_path):
        try:
            if os.path.exists(dir_path) and not os.listdir(dir_path):
                os.rmdir(dir_path)
        except:
            pass


# --- 功能一：改后缀 ---
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

        title = SubtitleLabel("一键修改文件扩展名", self)
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #202020;")
        layout.addWidget(title)

        self.drag_area = DragDropArea("🗂️ 将文件拖拽到此处，或点击批量选择", self)
        self.drag_area.filesDropped.connect(self.add_files_to_list)
        self.drag_area.click_callback = self.import_files
        layout.addWidget(self.drag_area)

        layout.addWidget(BodyLabel("待处理文件列表 (右键可移除)：", self))
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

        self.btn_action = PrimaryPushButton(FluentIcon.UPDATE, "开始一键修改", self)
        self.btn_action.clicked.connect(self.change_extensions)

        card_layout.addWidget(BodyLabel("目标扩展名：", self))
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
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", "All Files (*)")
        if files:
            self.add_files_to_list(files)

    def change_extensions(self):
        if not self.file_paths:
            InfoBar.warning("提示", "请先导入文件！", duration=2000, parent=self)
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
                    log(f"重命名失败: {e}", "ERROR")
        InfoBar.success("成功", f"成功修改 {success_count} 个文件后缀！", duration=3000, parent=self)
        self.list_widget.clear_all_items()


# --- 功能二：递归解压 ---
class AutoExtractorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("AutoExtractorWidget")
        self.file_paths = []
        self.init_ui()
        s = get_effective_settings()
        self.txt_7z_path.setText(s["path_7z"])
        self.txt_rar_path.setText(s["path_rar"])

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(14)

        title = SubtitleLabel("多层压缩包一键递归解压", self)
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #202020;")
        layout.addWidget(title)

        engine_card = CardWidget(self)
        el = QHBoxLayout(engine_card)
        el.setContentsMargins(15, 10, 15, 10)
        self.combo_engine = ComboBox(self)
        self.combo_engine.addItems(["Auto", "7z", "WinRAR"])
        self.combo_engine.setMinimumWidth(120)
        el.addWidget(BodyLabel("解压模式:", self))
        el.addWidget(self.combo_engine)
        el.addStretch()
        layout.addWidget(engine_card)

        c7 = CardWidget(self)
        l7 = QHBoxLayout(c7)
        l7.setContentsMargins(15, 10, 15, 10)
        self.txt_7z_path = LineEdit(self)
        self.txt_7z_path.setPlaceholderText("7z.exe 路径...")
        self.btn_browse_7z = PushButton("浏览...", self)
        self.btn_browse_7z.clicked.connect(self.browse_7z)
        l7.addWidget(BodyLabel("7z 路径:", self))
        l7.addWidget(self.txt_7z_path)
        l7.addWidget(self.btn_browse_7z)
        layout.addWidget(c7)

        cr = CardWidget(self)
        lr = QHBoxLayout(cr)
        lr.setContentsMargins(15, 10, 15, 10)
        self.txt_rar_path = LineEdit(self)
        self.txt_rar_path.setPlaceholderText("WinRAR.exe 路径...")
        self.btn_browse_rar = PushButton("浏览...", self)
        self.btn_browse_rar.clicked.connect(self.browse_rar)
        lr.addWidget(BodyLabel("WinRAR 路径:", self))
        lr.addWidget(self.txt_rar_path)
        lr.addWidget(self.btn_browse_rar)
        layout.addWidget(cr)

        self.drag_area = DragDropArea("📦 将压缩包拖拽到此处，或点击批量选择", self)
        self.drag_area.filesDropped.connect(self.add_files_to_list)
        self.drag_area.click_callback = self.browse_target
        layout.addWidget(self.drag_area)

        layout.addWidget(BodyLabel("待处理压缩包列表：", self))
        self.list_widget = RightClickListWidget(self)
        layout.addWidget(self.list_widget)

        pc = CardWidget(self)
        pl = QVBoxLayout(pc)
        pl.setContentsMargins(15, 12, 15, 12)
        pl.setSpacing(6)
        pl.addWidget(BodyLabel("解压密码库 (多个密码用逗号或换行分隔)：", self))
        self.txt_password = TextEdit(self)
        self.txt_password.setPlaceholderText("例如: password123, 123456")
        self.txt_password.setMaximumHeight(80)
        pl.addWidget(self.txt_password)
        layout.addWidget(pc)

        self.progress_label = BodyLabel("等待任务启动...", self)
        self.progress_label.setStyleSheet("color: #666666;")
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.progress_label.hide()
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        bl = QHBoxLayout()
        self.btn_clear = PushButton(FluentIcon.DELETE, "清空列表", self)
        self.btn_clear.clicked.connect(self.list_widget.clear_all_items)
        self.btn_extract = PrimaryPushButton(FluentIcon.DOWNLOAD, "开始批量递归解压", self)
        self.btn_extract.setMinimumHeight(40)
        self.btn_extract.clicked.connect(self.start_extraction)
        bl.addWidget(self.btn_clear)
        bl.addStretch()
        bl.addWidget(self.btn_extract)
        layout.addLayout(bl)

    def browse_7z(self):
        f, _ = QFileDialog.getOpenFileName(self, "选取 7z.exe", "", "7z (7z.exe)")
        if f: self.txt_7z_path.setText(f)

    def browse_rar(self):
        f, _ = QFileDialog.getOpenFileName(self, "选取 WinRAR.exe", "", "WinRAR (WinRAR.exe)")
        if f: self.txt_rar_path.setText(f)

    def browse_target(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择压缩文件", "",
                                                 "Archive Files (*.zip *.rar *.7z *.tar *.gz)")
        if files: self.add_files_to_list(files)

    def add_files_to_list(self, files):
        for f in files:
            if f not in self.file_paths:
                self.file_paths.append(f)
                self.list_widget.addItem(f)

    def get_passwords(self):
        raw = self.txt_password.toPlainText().strip()
        if not raw: return []
        raw = raw.replace("\n", ",")
        return [p.strip() for p in raw.split(",") if p.strip()]

    def get_engine_mode(self):
        t = self.combo_engine.currentText()
        if t == "Auto": return "auto"
        if t == "7z": return "7z"
        if t == "WinRAR": return "winrar"
        return "auto"

    def handle_worker_progress(self, value, status_text):
        self.progress_bar.setValue(value)
        self.progress_label.setText(status_text)

    def handle_worker_info(self, type_str, msg, duration):
        if type_str == "error":
            InfoBar.error("错误", msg, duration=duration, parent=self)
        elif type_str == "warning":
            InfoBar.warning("提示", msg, duration=duration, parent=self)
        elif type_str == "success":
            InfoBar.success("成功", msg, duration=duration, parent=self)

    def handle_worker_finished(self, success_files):
        self.btn_extract.setEnabled(True)
        self.btn_extract.setText("开始批量递归解压")
        self.list_widget.clear_all_items()
        self.progress_bar.hide()
        self.progress_label.hide()
        InfoBar.success("完成", f"成功处理 {success_files} 个压缩包。", duration=5000, parent=self)
        self.thread.quit()
        self.thread.wait()

    def start_extraction(self):
        exe_7z = self.txt_7z_path.text().strip()
        exe_rar = self.txt_rar_path.text().strip()
        mode = self.get_engine_mode()

        if mode in ("7z", "auto") and (not exe_7z or not os.path.exists(exe_7z)):
            InfoBar.error("错误", "7z.exe 路径不正确！", duration=3000, parent=self)
            return
        if mode in ("winrar", "auto") and (not exe_rar or not os.path.exists(exe_rar)):
            InfoBar.error("错误", "WinRAR.exe 路径不正确！", duration=3000, parent=self)
            return
        if not self.file_paths:
            InfoBar.error("错误", "请先导入压缩包！", duration=3000, parent=self)
            return

        passwords = self.get_passwords()
        settings = load_settings()
        log(f"手动触发: {len(self.file_paths)} 个文件, 模式={mode}")

        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.setText("正在初始化...")
        self.progress_label.show()
        self.btn_extract.setEnabled(False)
        self.btn_extract.setText("运行中...")

        self.thread = QThread()
        self.worker = ExtractionWorker(
            exe_7z_path=exe_7z, exe_rar_path=exe_rar,
            file_paths=list(self.file_paths), passwords=passwords,
            is_all_in_one=False, engine_mode=mode,
            timeout_7z_precheck=settings["timeout_7z_precheck"],
            timeout_no_password=settings["timeout_no_password"],
            timeout_rar_no_password=settings["timeout_rar_no_password"],
            timeout_7z_extract=settings["timeout_7z_extract"],
            timeout_rar_extract=settings["timeout_rar_extract"],
            max_recursion_depth=settings["max_recursion_depth"],
            delete_after_extract=settings["delete_after_extract"],
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress_signal.connect(self.handle_worker_progress)
        self.worker.info_signal.connect(self.handle_worker_info)
        self.worker.finished_signal.connect(self.handle_worker_finished)
        self.thread.start()


# --- 功能三：改后缀+解压联动 ---
class AllInOneWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("AllInOneWidget")
        self.file_paths = []
        self.init_ui()
        s = get_effective_settings()
        self.txt_7z_path.setText(s["path_7z"])
        self.txt_rar_path.setText(s["path_rar"])

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(14)

        title = SubtitleLabel("一键还原真实后缀并递归解压", self)
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #202020;")
        layout.addWidget(title)

        ec = CardWidget(self)
        el = QHBoxLayout(ec)
        el.setContentsMargins(15, 10, 15, 10)
        self.combo_engine = ComboBox(self)
        self.combo_engine.addItems(["Auto", "7z", "WinRAR"])
        self.combo_engine.setMinimumWidth(120)
        el.addWidget(BodyLabel("解压模式:", self))
        el.addWidget(self.combo_engine)
        el.addStretch()
        layout.addWidget(ec)

        c7 = CardWidget(self)
        l7 = QHBoxLayout(c7)
        l7.setContentsMargins(15, 10, 15, 10)
        self.txt_7z_path = LineEdit(self)
        self.txt_7z_path.setPlaceholderText("7z.exe 路径...")
        self.btn_browse_7z = PushButton("浏览...", self)
        self.btn_browse_7z.clicked.connect(self.browse_7z)
        l7.addWidget(BodyLabel("7z 路径:", self))
        l7.addWidget(self.txt_7z_path)
        l7.addWidget(self.btn_browse_7z)
        layout.addWidget(c7)

        cr = CardWidget(self)
        lr = QHBoxLayout(cr)
        lr.setContentsMargins(15, 10, 15, 10)
        self.txt_rar_path = LineEdit(self)
        self.txt_rar_path.setPlaceholderText("WinRAR.exe 路径...")
        self.btn_browse_rar = PushButton("浏览...", self)
        self.btn_browse_rar.clicked.connect(self.browse_rar)
        lr.addWidget(BodyLabel("WinRAR 路径:", self))
        lr.addWidget(self.txt_rar_path)
        lr.addWidget(self.btn_browse_rar)
        layout.addWidget(cr)

        self.drag_area = DragDropArea("✨ 将伪装后缀的压缩包批量拖入此处", self)
        self.drag_area.filesDropped.connect(self.add_files_to_list)
        self.drag_area.click_callback = self.browse_target
        layout.addWidget(self.drag_area)

        layout.addWidget(BodyLabel("待处理文件列表：", self))
        self.list_widget = RightClickListWidget(self)
        layout.addWidget(self.list_widget)

        cc = CardWidget(self)
        cl = QVBoxLayout(cc)
        cl.setContentsMargins(15, 12, 15, 12)
        cl.setSpacing(8)
        sl = QHBoxLayout()
        self.combo_real_ext = ComboBox(self)
        self.combo_real_ext.addItems([".zip", ".rar", ".7z", ".tar"])
        sl.addWidget(BodyLabel("真实扩展名:", self))
        sl.addWidget(self.combo_real_ext)
        sl.addStretch()
        cl.addLayout(sl)
        cl.addWidget(BodyLabel("解压密码库 (多个用逗号或换行分隔)：", self))
        self.txt_password = TextEdit(self)
        self.txt_password.setPlaceholderText("选填")
        self.txt_password.setMaximumHeight(60)
        cl.addWidget(self.txt_password)
        layout.addWidget(cc)

        self.progress_label = BodyLabel("等待联动任务启动...", self)
        self.progress_label.setStyleSheet("color: #666666;")
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.progress_label.hide()
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        bl = QHBoxLayout()
        self.btn_clear = PushButton(FluentIcon.DELETE, "清空列表", self)
        self.btn_clear.clicked.connect(self.list_widget.clear_all_items)
        self.btn_run = PrimaryPushButton(FluentIcon.PLAY, "启动：还原后缀 → 批量递归解压", self)
        self.btn_run.setMinimumHeight(42)
        self.btn_run.clicked.connect(self.process_all_in_one)
        bl.addWidget(self.btn_clear)
        bl.addStretch()
        bl.addWidget(self.btn_run)
        layout.addLayout(bl)

    def browse_7z(self):
        f, _ = QFileDialog.getOpenFileName(self, "选取 7z.exe", "", "7z (7z.exe)")
        if f: self.txt_7z_path.setText(f)

    def browse_rar(self):
        f, _ = QFileDialog.getOpenFileName(self, "选取 WinRAR.exe", "", "WinRAR (WinRAR.exe)")
        if f: self.txt_rar_path.setText(f)

    def browse_target(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", "All Files (*)")
        if files: self.add_files_to_list(files)

    def add_files_to_list(self, files):
        for f in files:
            if f not in self.file_paths:
                self.file_paths.append(f)
                self.list_widget.addItem(f)

    def get_passwords(self):
        raw = self.txt_password.toPlainText().strip()
        if not raw: return []
        raw = raw.replace("\n", ",")
        return [p.strip() for p in raw.split(",") if p.strip()]

    def get_engine_mode(self):
        t = self.combo_engine.currentText()
        if t == "Auto": return "auto"
        if t == "7z": return "7z"
        if t == "WinRAR": return "winrar"
        return "auto"

    def handle_worker_progress(self, value, status_text):
        self.progress_bar.setValue(value)
        self.progress_label.setText(status_text)

    def handle_worker_info(self, type_str, msg, duration):
        if type_str == "error":
            InfoBar.error("错误", msg, duration=duration, parent=self)
        elif type_str == "warning":
            InfoBar.warning("提示", msg, duration=duration, parent=self)
        elif type_str == "success":
            InfoBar.success("成功", msg, duration=duration, parent=self)

    def handle_worker_finished(self, success_files):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("启动：还原后缀 → 批量递归解压")
        self.list_widget.clear_all_items()
        self.progress_bar.hide()
        self.progress_label.hide()
        InfoBar.success("完成", f"成功处理 {success_files} 个文件。", duration=6000, parent=self)
        self.thread.quit()
        self.thread.wait()

    def process_all_in_one(self):
        exe_7z = self.txt_7z_path.text().strip()
        exe_rar = self.txt_rar_path.text().strip()
        real_ext = self.combo_real_ext.currentText()
        passwords = self.get_passwords()
        mode = self.get_engine_mode()

        if mode in ("7z", "auto") and (not exe_7z or not os.path.exists(exe_7z)):
            InfoBar.error("错误", "7z.exe 路径不正确！", duration=3000, parent=self)
            return
        if mode in ("winrar", "auto") and (not exe_rar or not os.path.exists(exe_rar)):
            InfoBar.error("错误", "WinRAR.exe 路径不正确！", duration=3000, parent=self)
            return
        if not self.file_paths:
            InfoBar.error("错误", "请先选择文件！", duration=3000, parent=self)
            return

        settings = load_settings()
        log(f"一键联动: {len(self.file_paths)} 个文件, 真实后缀={real_ext}, 模式={mode}")

        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.setText("正在配置...")
        self.progress_label.show()
        self.btn_run.setEnabled(False)
        self.btn_run.setText("运行中...")

        self.thread = QThread()
        self.worker = ExtractionWorker(
            exe_7z_path=exe_7z, exe_rar_path=exe_rar,
            file_paths=list(self.file_paths), passwords=passwords,
            is_all_in_one=True, real_ext=real_ext, engine_mode=mode,
            timeout_7z_precheck=settings["timeout_7z_precheck"],
            timeout_no_password=settings["timeout_no_password"],
            timeout_rar_no_password=settings["timeout_rar_no_password"],
            timeout_7z_extract=settings["timeout_7z_extract"],
            timeout_rar_extract=settings["timeout_rar_extract"],
            max_recursion_depth=settings["max_recursion_depth"],
            delete_after_extract=settings["delete_after_extract"],
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress_signal.connect(self.handle_worker_progress)
        self.worker.info_signal.connect(self.handle_worker_info)
        self.worker.finished_signal.connect(self.handle_worker_finished)
        self.thread.start()


# --- 功能四：设置界面 ---
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

        # ── 标题 ──
        header_row = QHBoxLayout()
        title = SubtitleLabel("⚙️ 程序设置", self)
        title.setStyleSheet("font-size: 22px; font-weight: 600; color: #202020;")
        header_row.addWidget(title)
        header_row.addStretch()
        version_label = BodyLabel("v5.4", self)
        version_label.setStyleSheet("color: #999999; font-size: 13px;")
        header_row.addWidget(version_label)
        layout.addLayout(header_row)

        desc = BodyLabel("修改设置后请点击下方「保存设置」按钮使其生效。", self)
        desc.setStyleSheet("color: #888888; margin-bottom: 6px;")
        layout.addWidget(desc)

        # ═══════════════════════════════════════════════
        #  分组1：超时设置
        # ═══════════════════════════════════════════════
        timeout_card = CardWidget(self)
        timeout_layout = QVBoxLayout(timeout_card)
        timeout_layout.setContentsMargins(20, 16, 20, 16)
        timeout_layout.setSpacing(12)

        timeout_title = StrongBodyLabel("⏱ 超时设置", self)
        timeout_title.setStyleSheet("font-size: 15px; color: #333333;")
        timeout_layout.addWidget(timeout_title)

        # 7z 预检
        timeout_layout.addLayout(self._make_spin_row(
            "7z 预检超时 (秒)",
            "7z 列出压缩包目录 + 检测加密的最大等待时间，建议 5~15",
            "timeout_7z_precheck", 3, 60
        ))

        # 无密码解压超时（7z 用）
        timeout_layout.addLayout(self._make_spin_row(
            "7z 无密码解压超时 (秒)",
            "7z 无密码解压阶段的最大等待时间。全加密包会自动跳过此阶段，建议 10~60",
            "timeout_no_password", 5, 180
        ))

        # WinRAR 无密码超时
        timeout_layout.addLayout(self._make_spin_row(
            "WinRAR 无密码解压超时 (秒)",
            "WinRAR 无密码解压的最大等待时间。加密包通常秒级返回错误码，建议 3~10",
            "timeout_rar_no_password", 2, 30
        ))

        # 7z 有密码解压超时
        timeout_layout.addLayout(self._make_spin_row(
            "7z 有密码解压超时 (秒)",
            "7z 逐密码尝试解压时的单次超时，建议 20~120",
            "timeout_7z_extract", 10, 300
        ))

        # WinRAR 有密码解压超时
        timeout_layout.addLayout(self._make_spin_row(
            "WinRAR 有密码解压超时 (秒)",
            "WinRAR 逐密码尝试解压时的单次超时，建议 30~180",
            "timeout_rar_extract", 10, 300
        ))

        layout.addWidget(timeout_card)

        # ═══════════════════════════════════════════════
        #  分组2：路径设置
        # ═══════════════════════════════════════════════
        path_card = CardWidget(self)
        path_layout = QVBoxLayout(path_card)
        path_layout.setContentsMargins(20, 16, 20, 16)
        path_layout.setSpacing(12)

        path_title = StrongBodyLabel("📁 工具路径", self)
        path_title.setStyleSheet("font-size: 15px; color: #333333;")
        path_layout.addWidget(path_title)

        path_desc = BodyLabel("设置后将作为解压页面的默认路径。留空则自动查找。", self)
        path_desc.setStyleSheet("color: #888888; font-size: 12px;")
        path_layout.addWidget(path_desc)

        row7 = QHBoxLayout()
        row7.addWidget(BodyLabel("7z.exe", self))
        self.txt_path_7z = LineEdit(self)
        self.txt_path_7z.setPlaceholderText("自动查找...")
        self.txt_path_7z.setText(self.settings.get("path_7z", ""))
        self.txt_path_7z.setMinimumWidth(300)
        btn7 = PushButton("浏览", self)
        btn7.clicked.connect(lambda: self._browse_file("7z.exe (7z.exe)", self.txt_path_7z))
        row7.addWidget(self.txt_path_7z)
        row7.addWidget(btn7)
        row7.addStretch()
        path_layout.addLayout(row7)

        rowr = QHBoxLayout()
        rowr.addWidget(BodyLabel("WinRAR.exe", self))
        self.txt_path_rar = LineEdit(self)
        self.txt_path_rar.setPlaceholderText("自动查找...")
        self.txt_path_rar.setText(self.settings.get("path_rar", ""))
        self.txt_path_rar.setMinimumWidth(300)
        btnr = PushButton("浏览", self)
        btnr.clicked.connect(lambda: self._browse_file("WinRAR.exe (WinRAR.exe)", self.txt_path_rar))
        rowr.addWidget(self.txt_path_rar)
        rowr.addWidget(btnr)
        rowr.addStretch()
        path_layout.addLayout(rowr)

        layout.addWidget(path_card)

        # ═══════════════════════════════════════════════
        #  分组3：高级设置
        # ═══════════════════════════════════════════════
        advanced_card = CardWidget(self)
        advanced_layout = QVBoxLayout(advanced_card)
        advanced_layout.setContentsMargins(20, 16, 20, 16)
        advanced_layout.setSpacing(12)

        advanced_title = StrongBodyLabel("🔧 高级设置", self)
        advanced_title.setStyleSheet("font-size: 15px; color: #333333;")
        advanced_layout.addWidget(advanced_title)

        advanced_layout.addLayout(self._make_spin_row(
            "递归深度上限",
            "防止无限递归，超过此层数将停止。建议 10~50",
            "max_recursion_depth", 5, 100
        ))

        switch_row = QHBoxLayout()
        switch_label_col = QVBoxLayout()
        switch_label = BodyLabel("递归解压后删除压缩包", self)
        switch_hint = BodyLabel("内层压缩包解压成功后自动删除原文件", self)
        switch_hint.setStyleSheet("color: #888888; font-size: 12px;")
        switch_label_col.addWidget(switch_label)
        switch_label_col.addWidget(switch_hint)

        self.switch_delete = SwitchButton(self)
        self.switch_delete.setOnText("开")
        self.switch_delete.setOffText("关")
        self.switch_delete.setChecked(self.settings.get("delete_after_extract", True))

        switch_row.addLayout(switch_label_col)
        switch_row.addStretch()
        switch_row.addWidget(self.switch_delete)
        advanced_layout.addLayout(switch_row)

        layout.addWidget(advanced_card)

        # ═══════════════════════════════════════════════
        #  按钮区
        # ═══════════════════════════════════════════════
        btn_layout = QHBoxLayout()

        self.btn_reset = PushButton(FluentIcon.CANCEL, "恢复默认", self)
        self.btn_reset.clicked.connect(self.reset_defaults)

        self.btn_save = PrimaryPushButton(FluentIcon.SAVE, "保存设置", self)
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
        hint.setStyleSheet("color: #888888; font-size: 12px;")
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
        f, _ = QFileDialog.getOpenFileName(self, "选择文件", "", filter_str)
        if f:
            target_lineedit.setText(f)

    def save_current(self):
        self.settings["path_7z"] = self.txt_path_7z.text().strip()
        self.settings["path_rar"] = self.txt_path_rar.text().strip()
        self.settings["delete_after_extract"] = self.switch_delete.isChecked()
        for key, spin in self._spinboxes.items():
            self.settings[key] = spin.value()

        if save_settings(self.settings):
            InfoBar.success("已保存", "设置已保存，将在下次解压任务时生效。", duration=3000, parent=self)
        else:
            InfoBar.error("错误", "保存设置失败，请检查文件权限。", duration=3000, parent=self)

    def reset_defaults(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.txt_path_7z.setText("")
        self.txt_path_rar.setText("")
        self.switch_delete.setChecked(DEFAULT_SETTINGS["delete_after_extract"])
        for key in DEFAULT_SETTINGS:
            if key in self._spinboxes:
                self._spinboxes[key].setValue(DEFAULT_SETTINGS[key])
        InfoBar.success("已重置", "已恢复为默认设置（尚未保存）。", duration=2500, parent=self)


# --- 主窗口 ---
class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("一站式文件解压助手 v5.4")
        self.resize(1050, 900)

        self.changer_interface = ExtensionChangerWidget(self)
        self.extractor_interface = AutoExtractorWidget(self)
        self.all_in_one_interface = AllInOneWidget(self)
        self.settings_interface = SettingsWidget(self)

        self.addSubInterface(self.changer_interface, FluentIcon.EDIT, "一键改后缀")
        self.addSubInterface(self.extractor_interface, FluentIcon.ZIP_FOLDER, "文件递归解压")
        self.addSubInterface(self.all_in_one_interface, FluentIcon.SYNC, "改后缀解压")
        self.addSubInterface(self.settings_interface, FluentIcon.SETTING, "设置",
                             position=NavigationItemPosition.BOTTOM)


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    log("═══════════════════════════════════", "START")
    log("Auto7z v5.4 启动 (双引擎: 7z + WinRAR)", "START")
    s = get_effective_settings()
    log(f"7z:  {s['path_7z'] or '未找到'}")
    log(f"RAR: {s['path_rar'] or '未找到'}")
    log(f"超时: 预检={s['timeout_7z_precheck']}s 无密码={s['timeout_no_password']}s "
        f"RAR无密码={s['timeout_rar_no_password']}s "
        f"7z有密码={s['timeout_7z_extract']}s RAR有密码={s['timeout_rar_extract']}s")
    log("═══════════════════════════════════", "START")

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_with_context() if hasattr(app, 'exec_with_context') else app.exec_())
import os
from pathlib import Path
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import (SubtitleLabel, BodyLabel, CardWidget, ComboBox,
                            LineEdit, PushButton, PrimaryPushButton, TextEdit,
                            InfoBar, FluentIcon, ScrollArea)
from worker import ExtractionWorker
from animated_progress import AnimatedProgressBar


COLORS = {"canvas": "#F7F9FC", "surface": "#FFFFFF", "text": "#1F2937",
          "muted": "#526174", "border": "#D5DCE5", "accent": "#1765CC",
          "selected": "#E8F0FE", "success": "#157333", "warning": "#915400",
          "danger": "#B3261E"}


class ExtractionPanel(QWidget):
    def __init__(self, parent, drag_class, list_class, load_settings,
                 effective_settings, all_in_one=False):
        super().__init__(parent)
        self.setObjectName("AllInOneWidget" if all_in_one else "AutoExtractorWidget")
        self.all_in_one = all_in_one
        self.load_settings = load_settings
        self.file_paths = []
        self.running = False
        self.results = []
        self.thread = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        content = QWidget(self)
        scroll = ScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(12)
        title = SubtitleLabel("還原後綴並解壓" if all_in_one else "遞歸解壓", self)
        title.setStyleSheet(f"font-size: 24px; font-weight: 600; color: {COLORS['text']};")
        layout.addWidget(title)
        toolbar = QHBoxLayout()
        toolbar.addWidget(BodyLabel("解壓引擎", self))
        self.combo_engine = ComboBox(self)
        self.combo_engine.addItems(["自動選擇", "7-Zip", "WinRAR"])
        self.combo_engine.setMinimumWidth(140)
        toolbar.addWidget(self.combo_engine)
        if all_in_one:
            toolbar.addSpacing(16)
            toolbar.addWidget(BodyLabel("真實後綴", self))
            self.combo_real_ext = ComboBox(self)
            self.combo_real_ext.addItems([".zip", ".rar", ".7z", ".tar", ".gz"])
            toolbar.addWidget(self.combo_real_ext)
        toolbar.addStretch()
        self.btn_tools = PushButton("工具路徑 ▾", self)
        toolbar.addWidget(self.btn_tools)
        layout.addLayout(toolbar)
        self.tools_card = CardWidget(self)
        tool_layout = QVBoxLayout(self.tools_card)
        tool_layout.setContentsMargins(16, 12, 16, 12)
        settings = effective_settings()
        for key, label in (("7z", "7-Zip"), ("rar", "WinRAR")):
            row = QHBoxLayout()
            row.addWidget(BodyLabel(label, self))
            field = LineEdit(self)
            field.setText(settings[f"path_{key}"])
            field.setPlaceholderText("選擇可執行文件")
            setattr(self, f"txt_{key}_path", field)
            row.addWidget(field, 1)
            button = PushButton("瀏覽", self)
            button.clicked.connect(lambda checked=False, edit=field: self.browse_tool(edit))
            row.addWidget(button)
            tool_layout.addLayout(row)
        layout.addWidget(self.tools_card)
        self.tools_card.hide()
        self.btn_tools.clicked.connect(lambda: self.tools_card.setVisible(self.tools_card.isHidden()))

        self.drag_area = drag_class("拖入壓縮包，或點擊添加文件", self)
        self.drag_area.setMinimumHeight(94)
        self.drag_area.filesDropped.connect(self.add_files_to_list)
        self.drag_area.click_callback = self.browse_target
        layout.addWidget(self.drag_area)
        self.queue_label = BodyLabel("文件隊列 · 0 個文件", self)
        queue_header = QHBoxLayout()
        queue_header.addWidget(self.queue_label)
        queue_header.addStretch()
        self.btn_clear = PushButton("清空隊列", self)
        self.btn_clear.clicked.connect(self.clear_queue)
        queue_header.addWidget(self.btn_clear)
        layout.addLayout(queue_header)
        self.list_widget = list_class(self)
        self.list_widget.setMinimumHeight(120)
        self.list_widget.model().rowsRemoved.connect(self.update_count)
        layout.addWidget(self.list_widget, 1)

        password_card = CardWidget(self)
        password_layout = QVBoxLayout(password_card)
        password_layout.setContentsMargins(16, 12, 16, 12)
        password_layout.addWidget(BodyLabel("Password", self))
        self.txt_password = TextEdit(self)
        self.txt_password.setPlaceholderText("每行一組密碼，或以逗號分隔")
        self.txt_password.setFixedHeight(65)
        password_layout.addWidget(self.txt_password)
        layout.addWidget(password_card)

        self.status_card = CardWidget(self)
        status_layout = QVBoxLayout(self.status_card)
        status_layout.setContentsMargins(16, 12, 16, 12)
        self.progress_label = BodyLabel("準備就緒", self)
        self.progress_label.setWordWrap(True)
        self.percent_label = BodyLabel("0%", self)
        self.percent_label.setStyleSheet(f"color: {COLORS['muted']};")
        status_header = QHBoxLayout()
        status_header.addWidget(self.progress_label, 1)
        status_header.addWidget(self.percent_label)
        self.activity_label = BodyLabel("", self)
        self.activity_label.setWordWrap(True)
        self.activity_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        self.activity_label.hide()
        self.progress_bar = AnimatedProgressBar(self)
        self.progress_bar.setVisualStyle("apple")
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setAccessibleName("文件隊列處理進度")
        self.progress_bar.setValue(0)
        self.progress_bar.valueChanged.connect(lambda value: self.percent_label.setText(f"{value}%"))
        status_layout.addLayout(status_header)
        status_layout.addWidget(self.progress_bar)
        status_layout.addWidget(self.activity_label)
        status_row = QHBoxLayout()
        status_row.setContentsMargins(28, 4, 28, 0)
        status_row.addWidget(self.status_card)
        outer.addLayout(status_row)
        self.detail = TextEdit(self)
        self.detail.setReadOnly(True)
        self.detail.setFixedHeight(100)
        self.detail.hide()
        layout.addWidget(self.detail)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(28, 4, 28, 20)
        self.btn_details = PushButton("查看結果", self)
        self.btn_details.clicked.connect(lambda: self.detail.setVisible(self.detail.isHidden()))
        self.btn_open = PushButton("打開結果目錄", self)
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self.open_output)
        self.btn_cancel = PushButton("取消任務", self)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_start = PrimaryPushButton(FluentIcon.PLAY, "開始解壓", self)
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setMinimumWidth(170)
        self.btn_start.clicked.connect(self.start)
        buttons.addWidget(self.btn_details)
        buttons.addWidget(self.btn_open)
        buttons.addStretch()
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_start)
        outer.addLayout(buttons)

    def update_count(self, *args):
        self.results = [r for r in self.results if r.source in self.file_paths]
        self.queue_label.setText(f"文件隊列 · {len(self.file_paths)} 個文件")

    def add_files_to_list(self, files):
        if self.running:
            return
        for filename in files:
            filename = os.path.abspath(filename)
            if os.path.isfile(filename) and filename not in self.file_paths:
                self.file_paths.append(filename)
                self.list_widget.addItem(filename)
                self.list_widget.item(self.list_widget.count()-1).setToolTip(filename)
        self.update_count()

    def clear_queue(self):
        self.list_widget.clear_all_items()
        self.update_count()
        self.progress_bar.setValue(0)
        self.progress_label.setText("準備就緒")
        self.activity_label.clear()
        self.activity_label.hide()
        self.detail.clear()
        self.detail.hide()
        self.btn_open.setEnabled(False)
        self.btn_start.setText("開始解壓")

    def browse_tool(self, field):
        filename, _ = QFileDialog.getOpenFileName(self, "選擇解壓引擎", "", "可執行文件 (*.exe)")
        if filename:
            field.setText(filename)

    def browse_target(self):
        files, _ = QFileDialog.getOpenFileNames(self, "添加壓縮包", "", "所有文件 (*)")
        self.add_files_to_list(files)

    def start(self):
        if self.running:
            return
        # Only fully successful rows are skipped on retry; failures stay visible.
        succeeded = {r.source for r in self.results if r.status == "success"}
        originals = [p for p in self.file_paths if p not in succeeded]
        retry_archives = {r.source: r.archive for r in self.results if r.archive}
        sources = [retry_archives.get(p, p) for p in originals]
        if not sources:
            InfoBar.warning("沒有待處理文件", "請添加文件，或清空隊列後重新導入。", parent=self)
            return
        path_7z = self.txt_7z_path.text().strip()
        path_rar = self.txt_rar_path.text().strip()
        mode = ("auto", "7z", "winrar")[self.combo_engine.currentIndex()]
        valid7, validrar = os.path.isfile(path_7z), os.path.isfile(path_rar)
        if (mode == "auto" and not (valid7 or validrar)) or (mode == "7z" and not valid7) or (mode == "winrar" and not validrar):
            self.tools_card.show()
            InfoBar.error("引擎不可用", "請檢查所選引擎的工具路徑。自動模式只需一個可用引擎。", parent=self)
            return
        settings = self.load_settings()
        raw = self.txt_password.toPlainText().replace("\n", ",").replace("，", ",")
        passwords = [p.strip() for p in raw.split(",") if p.strip()]
        self.results = [r for r in self.results if r.source in succeeded and r.source in self.file_paths]
        self.detail.clear()
        self.progress_bar.setValue(0)
        self.progress_label.setText("正在啓動…")
        self.activity_label.clear()
        self.running = True
        self.set_busy(True)
        self.thread = QThread(self)
        self.worker = ExtractionWorker(path_7z, path_rar, sources, passwords,
            source_aliases=dict(zip(sources, originals)),
            is_all_in_one=self.all_in_one,
            real_ext=self.combo_real_ext.currentText() if self.all_in_one else "",
            engine_mode=mode, max_recursion_depth=settings["max_recursion_depth"],
            delete_after_extract=settings["delete_after_extract"],
            idle_timeout_seconds=settings["idle_timeout_seconds"],
            timeout_7z_precheck=settings["timeout_7z_precheck"])
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress_signal.connect(self.handle_progress)
        self.worker.activity_signal.connect(self.show_activity)
        self.worker.result_signal.connect(self.handle_result)
        self.worker.info_signal.connect(self.handle_info)
        self.worker.finished_signal.connect(self.thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.finish)
        self.thread.start()

    def set_busy(self, busy):
        self.progress_bar.setBusy(busy)
        for widget in (self.btn_start, self.btn_clear, self.list_widget, self.drag_area,
                       self.tools_card, self.combo_engine, self.txt_password):
            widget.setEnabled(not busy)
        if self.all_in_one:
            self.combo_real_ext.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)
        self.btn_start.setText("正在解壓…" if busy else "開始解壓")

    def show_activity(self, message):
        self.activity_label.setText(message)
        self.activity_label.setVisible(bool(message))

    def handle_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def handle_info(self, level, message, duration):
        getattr(InfoBar, level)("任務提示", message, duration=duration, parent=self)

    def handle_result(self, result):
        self.results = [r for r in self.results if r.source != result.source]
        self.results.append(result)
        labels = {"success": "成功", "partial": "部分完成", "failed": "失敗", "cancelled": "已取消"}
        color = {"success": "success", "partial": "warning", "failed": "danger", "cancelled": "muted"}[result.status]
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == result.source or item.text() == result.source:
                item.setData(Qt.UserRole, result.source)
                item.setText(f"[{labels[result.status]}] {Path(result.source).name}")
                item.setForeground(QColor(COLORS[color]))
                item.setToolTip(f"{result.source}\n{result.output}\n{result.detail}")
        self.detail.append(f"{labels[result.status]} · {result.source}\n結果: {result.output or '無'}\n{result.detail}\n")
        self.btn_open.setEnabled(any(r.output for r in self.results))

    def cancel(self):
        if self.running:
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)
            self.show_activity("正在取消…")

    def finish(self):
        self.running = False
        self.set_busy(False)
        self.thread.deleteLater()
        self.thread = None
        success = sum(r.status == "success" for r in self.results)
        partial = sum(r.status == "partial" for r in self.results)
        failed = sum(r.status == "failed" for r in self.results)
        pending = len(self.file_paths) - success - partial - failed
        self.progress_label.setText(f"成功 {success} · 部分完成 {partial} · 失敗 {failed} · 未完成 {pending}")
        self.activity_label.clear()
        self.activity_label.hide()
        if partial or failed or pending:
            self.detail.show()
        self.btn_start.setText("重試未成功文件" if partial or failed or pending else "開始解壓")

    def open_output(self):
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        outputs = [r.output for r in self.results if r.output and os.path.isdir(r.output)]
        if outputs:
            QDesktopServices.openUrl(QUrl.fromLocalFile(outputs[-1]))

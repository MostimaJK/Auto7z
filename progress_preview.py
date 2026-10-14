"""Local palette workbench; every displayed percentage is simulated."""
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSlider, QFrame
from qfluentwidgets import BodyLabel, SubtitleLabel, PushButton, CheckBox, ComboBox, ScrollArea
from animated_progress import AnimatedProgressBar


class ProgressPreviewDialog(QDialog):
    SURFACES = {
        "light": ("#FFFFFF", "#1F2937", "#526174"),
        "cream": ("#FFFCF6", "#30262A", "#74626A"),
        "dark": ("#141B22", "#F2F5F7", "#B5C1CC"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("進度條配色試驗檯")
        self.resize(760, 740)
        self.setMinimumSize(420, 560)
        self.setStyleSheet("QDialog { background: #F7F9FC; }")
        self.bars = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)
        outer.addWidget(SubtitleLabel("經典樣式與微光配色", self))
        self.value_label = BodyLabel("模擬進度 64% · 直接更新 · 不影響任務", self)
        self.value_label.setWordWrap(True)
        outer.addWidget(self.value_label)
        self.scroll = ScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)
        body.addWidget(BodyLabel("已確認的經典樣式", self))
        classic = QFrame(self)
        classic.setStyleSheet("QFrame { background: white; border-radius: 12px; }")
        classic_layout = QVBoxLayout(classic)
        classic_layout.setContentsMargins(14, 10, 14, 10)
        classic_layout.setSpacing(3)
        self.classic_grid = QGridLayout()
        self.classic_grid.setHorizontalSpacing(18)
        self.classic_cells = []
        for style, name in zip(AnimatedProgressBar.STYLES[:3], AnimatedProgressBar.STYLE_NAMES[:3]):
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(0)
            cell_layout.addWidget(BodyLabel(name, self))
            cell_layout.addWidget(self.make_bar(style))
            self.classic_cells.append(cell)
        classic_layout.addLayout(self.classic_grid)
        body.addWidget(classic)
        body.addWidget(BodyLabel("微光配色 · 並排比較", self))
        self.palette_surface = QFrame(self)
        palette_layout = QVBoxLayout(self.palette_surface)
        palette_layout.setContentsMargins(14, 12, 14, 12)
        self.palette_grid = QGridLayout()
        self.palette_grid.setHorizontalSpacing(20)
        self.palette_grid.setVerticalSpacing(10)
        self.palette_cells = []
        self.palette_labels = []
        for style, (name, colors, dark_colors) in AnimatedProgressBar.PALETTES.items():
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(0)
            label = BodyLabel(name, cell)
            cell_layout.addWidget(label)
            cell_layout.addWidget(self.make_bar(style))
            self.palette_labels.append(label)
            self.palette_cells.append(cell)
        palette_layout.addLayout(self.palette_grid)
        body.addWidget(self.palette_surface)
        body.addStretch()
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)

        # Fixed lower panel: the dropdowns affect preview palettes, never worker data.
        controls = QFrame(self)
        controls.setStyleSheet("QFrame { background: white; border-radius: 12px; }")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(14, 12, 14, 12)
        controls_layout.setSpacing(8)
        controls_layout.addWidget(BodyLabel("下方配色選擇區", self))
        selector_grid = QGridLayout()
        self.color_combo = ComboBox(self)
        self.color_combo.addItems([p[0] for p in AnimatedProgressBar.PALETTES.values()])
        self.surface_combo = ComboBox(self)
        self.surface_combo.addItems(["冷白底", "奶油底", "深色底"])
        self.glow_combo = ComboBox(self)
        self.glow_combo.addItems(["關閉光暈", "輕微光暈", "適中光暈"])
        self.glow_combo.setCurrentIndex(1)
        for col, (label, combo) in enumerate((("配色", self.color_combo), ("底色", self.surface_combo), ("光暈", self.glow_combo))):
            selector_grid.addWidget(BodyLabel(label, self), 0, col)
            selector_grid.addWidget(combo, 1, col)
        controls_layout.addLayout(selector_grid)
        self.selected_surface = QFrame(self)
        selected_layout = QVBoxLayout(self.selected_surface)
        selected_layout.setContentsMargins(10, 7, 10, 7)
        self.selected_label = BodyLabel("", self)
        self.selected_label.setWordWrap(True)
        selected_layout.addWidget(self.selected_label)
        self.selected_bar = self.make_bar("klein")
        selected_layout.addWidget(self.selected_bar)
        controls_layout.addWidget(self.selected_surface)
        for combo in (self.color_combo, self.surface_combo, self.glow_combo):
            combo.currentIndexChanged.connect(self.update_palette)
        outer.addWidget(controls)
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(0, 100)
        self.slider.setValue(64)
        self.slider.setAccessibleName("模擬進度百分比")
        self.slider.valueChanged.connect(self.set_preview_value)
        outer.addWidget(self.slider)
        actions = QHBoxLayout()
        self.animation_check = CheckBox("動態效果", self)
        self.animation_check.setChecked(True)
        self.animation_check.toggled.connect(self.set_preview_animation)
        actions.addWidget(self.animation_check)
        self.unknown_check = CheckBox("未知進度", self)
        self.unknown_check.toggled.connect(self.set_unknown)
        actions.addWidget(self.unknown_check)
        actions.addStretch()
        close = PushButton("關閉預覽", self)
        close.clicked.connect(self.accept)
        actions.addWidget(close)
        outer.addLayout(actions)
        self.update_palette()
        self.arrange_palette_grid()

    def make_bar(self, style):
        bar = AnimatedProgressBar(self)
        bar.setVisualStyle(style)
        bar.setValue(64)
        bar.setBusy(True)
        bar.setAccessibleName(f"{style}模擬進度")
        self.bars.append(bar)
        return bar

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "palette_cells"):
            self.arrange_palette_grid()

    def arrange_palette_grid(self):
        while self.classic_grid.count():
            self.classic_grid.takeAt(0)
        classic_columns = 1 if self.width() < 620 else 3
        for index, cell in enumerate(self.classic_cells):
            self.classic_grid.addWidget(cell, index//classic_columns, index%classic_columns)
        while self.palette_grid.count():
            self.palette_grid.takeAt(0)
        columns = 1 if self.width() < 620 else 2
        for index, cell in enumerate(self.palette_cells):
            self.palette_grid.addWidget(cell, index//columns, index%columns)

    def update_palette(self, *args):
        surface = ("light", "cream", "dark")[self.surface_combo.currentIndex()]
        bg, text, muted = self.SURFACES[surface]
        style = tuple(AnimatedProgressBar.PALETTES)[self.color_combo.currentIndex()]
        name, colors, dark_colors = AnimatedProgressBar.PALETTES[style]
        colors = dark_colors if surface == "dark" else colors
        self.selected_bar.setVisualStyle(style)
        self.selected_label.setText(f"{name} · {' → '.join(colors)}" + (" · 深色適配" if surface == "dark" else ""))
        for frame in (self.palette_surface, self.selected_surface):
            frame.setStyleSheet(f"QFrame {{ background: {bg}; border-radius: 10px; }}")
        for label in self.palette_labels + [self.selected_label]:
            label.setStyleSheet(f"color: {text}; background: transparent;")
        for bar in self.bars:
            if bar.visualStyle() in AnimatedProgressBar.PALETTES:
                bar.setSurface(surface)
                bar.setGlowStrength(self.glow_combo.currentIndex())

    def set_preview_value(self, value):
        if not self.unknown_check.isChecked():
            self.value_label.setText(f"模擬進度 {value}% · 直接更新 · 不影響任務")
        for bar in self.bars:
            bar.setValue(value)

    def set_preview_animation(self, enabled):
        for bar in self.bars:
            bar.setAnimated(enabled)

    def set_unknown(self, unknown):
        self.slider.setEnabled(not unknown)
        self.value_label.setText("模擬未知進度 · 不顯示完成百分比" if unknown else f"模擬進度 {self.slider.value()}% · 直接更新 · 不影響任務")
        for bar in self.bars:
            bar.setIndeterminate(unknown)

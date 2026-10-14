"""Native Qt adaptations of classic progress styles; values update immediately."""
import math
import time
from PyQt5.QtCore import Qt, QRectF, QSize, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen, QLinearGradient
from PyQt5.QtWidgets import QWidget


class AnimatedProgressBar(QWidget):
    valueChanged = pyqtSignal(int)
    PALETTES = {
        "klein": ("克萊因藍", ("#002FA7", "#2457A7"), ("#8EACFF", "#B8C6FF")),
        "burgundy": ("勃艮第紅", ("#742D46", "#9A4B65"), ("#E7A3BD", "#F0CAD8")),
        "emerald": ("祖母綠", ("#176B52", "#267754"), ("#73C8A3", "#A8DFC2")),
        "indigo": ("靛藍", ("#353D70", "#5B5FA0"), ("#ADB3E7", "#D5D8F5")),
        "prussian": ("普魯士藍 · 青綠", ("#163F56", "#176B70"), ("#72B9CE", "#9EDBC4")),
        "terracotta": ("陶土紅", ("#9E4F34", "#B64E2F"), ("#E3A188", "#F2C5B3")),
    }
    STYLES = ("apple", "google", "fluent") + tuple(PALETTES)
    STYLE_NAMES = ("Apple 簡潔", "Google 直線", "Microsoft Fluent") + tuple(p[0]+" · 微光" for p in PALETTES.values())

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._style = "apple"
        self._busy = False
        self._animated = True
        self._indeterminate = False
        self._surface = "light"
        self._glow_strength = 1
        self._epoch = time.monotonic()
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self.setMinimumHeight(34)
        self.setAccessibleName("文件隊列處理進度")
        self._update_accessibility()

    def sizeHint(self):
        return QSize(280, 34)

    def value(self):
        return self._value

    def displayedValue(self):
        return float(self._value)

    def setValue(self, value):
        value = max(0, min(100, int(value)))
        if value != self._value:
            self._value = value
            self._update_accessibility()
            self.valueChanged.emit(value)
        self._sync_timer()
        self.update()

    def setVisualStyle(self, style):
        if style not in self.STYLES:
            raise ValueError(f"Unknown progress style: {style}")
        self._style = style
        self._sync_timer()
        self.update()

    def visualStyle(self):
        return self._style

    def setBusy(self, busy):
        self._busy = bool(busy)
        self._sync_timer()
        self.update()

    def setAnimated(self, animated):
        self._animated = bool(animated)
        self._sync_timer()
        self.update()

    def setSurface(self, surface):
        if surface not in ("light", "cream", "dark"):
            raise ValueError("Unknown preview surface")
        self._surface = surface
        self.update()

    def setGlowStrength(self, strength):
        self._glow_strength = max(0, min(2, int(strength)))
        self._sync_timer()
        self.update()

    def setIndeterminate(self, indeterminate):
        self._indeterminate = bool(indeterminate)
        self._update_accessibility()
        self._sync_timer()
        self.update()

    def _update_accessibility(self):
        description = "正在處理；完成比例未知" if self._indeterminate else f"隊列已處理 {self._value}%；此數值不表示解壓成功率"
        self.setAccessibleDescription(description)
        self.setToolTip(description)

    def _sync_timer(self):
        meaningful_motion = self._indeterminate or (self._style in self.PALETTES and self._glow_strength and 0 < self._value < 100)
        active = self._animated and self._busy and meaningful_motion and self.isVisible()
        if active and not self._timer.isActive():
            self._timer.start()
        elif not active:
            self._timer.stop()

    def _tick(self):
        if not self.window().isMinimized():
            self._phase = (time.monotonic() - self._epoch) % 60
            self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    @staticmethod
    def _rounded(rect, radius):
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        left, right = 8.0, max(8.0, self.width() - 8.0)
        width = right - left
        if width <= 0:
            return
        center = self.height() / 2
        phase = self._phase if self._animated else 0
        if self._style == "google":
            self._paint_google(painter, left, right, center, phase)
            return
        if self._style in self.PALETTES:
            self._paint_soft_glow(painter, left, right, center, phase)
            return
        thickness = 6 if self._style == "apple" else 4
        color = QColor("#007AFF" if self._style == "apple" else "#0F6CBD")
        track = QRectF(left, center-thickness/2, width, thickness)
        painter.fillPath(self._rounded(track, thickness/2), QColor("#E5E5EA" if self._style == "apple" else "#E1DFDD"))
        if self._indeterminate:
            # Separate unknown-progress state: this capsule is activity, not a percentage.
            ratio = .30 if self._style == "apple" else .35
            segment = width * ratio
            position = (.5 - .5*math.cos(phase*math.tau/2)) if self._style == "apple" else (phase/1.8) % 1
            x = left + position*(width-segment)
            painter.fillPath(self._rounded(QRectF(x, track.top(), segment, thickness), thickness/2), color)
        elif self._value:
            fill = QRectF(left, track.top(), width*self._value/100, thickness)
            painter.fillPath(self._rounded(fill, min(thickness/2, fill.width()/2)), color)

    def _paint_google(self, painter, left, right, center, phase):
        width = right-left
        color, track_color = QColor("#6750A4"), QColor("#E8DEF8")
        painter.setPen(QPen(track_color, 4, Qt.SolidLine, Qt.RoundCap))
        if self._indeterminate:
            start = left + (.5-.5*math.cos(phase*math.tau/2.2))*width*.65
            end = start+width*.35
            painter.drawLine(int(left), int(center), int(right), int(center))
        else:
            start, end = left, left+width*self._value/100
            if self._value < 100:
                remaining = min(right, end+8) if self._value else left
                if remaining < right:
                    painter.drawLine(int(remaining), int(center), int(right), int(center))
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(QRectF(right-2, center-2, 4, 4))
        if end <= start:
            return
        fill = QRectF(start, center-2, end-start, 4)
        painter.fillPath(self._rounded(fill, min(2, fill.width()/2)), color)

    def _paint_soft_glow(self, painter, left, right, center, phase):
        track = QRectF(left, center-3, right-left, 6)
        track_colors = {"light": "#E5E5EA", "cream": "#E3D9CD", "dark": "#364252"}
        painter.fillPath(self._rounded(track, 3), QColor(track_colors[self._surface]))
        if self._indeterminate:
            width = track.width()*.30
            position = .5-.5*math.cos(phase*math.tau/2)
            fill = QRectF(left+position*(track.width()-width), center-3, width, 6)
        elif self._value:
            fill = QRectF(left, center-3, track.width()*self._value/100, 6)
        else:
            return
        # Nearby cool hues keep the light UI coherent. Only halo opacity breathes.
        breathing = self._animated and self._busy and (self._indeterminate or self._value < 100)
        strength = .65+.35*(.5+.5*math.sin(phase*math.tau/3.6)) if breathing else 1
        colors = self.PALETTES[self._style][2 if self._surface == "dark" else 1]
        for spread in range(7 if self._glow_strength else 0, 0, -1):
            halo = QLinearGradient(fill.left(), 0, fill.right(), 0)
            for index, hex_color in enumerate(colors):
                color = QColor(hex_color)
                color.setAlpha(round((5 if spread > 4 else 9)*strength*self._glow_strength))
                halo.setColorAt(index/(len(colors)-1), color)
            painter.fillPath(self._rounded(fill.adjusted(-spread, -spread, spread, spread), 3+spread), halo)
        gradient = QLinearGradient(fill.left(), 0, fill.right(), 0)
        for index, color in enumerate(colors):
            gradient.setColorAt(index/(len(colors)-1), QColor(color))
        painter.fillPath(self._rounded(fill, min(3, fill.width()/2)), gradient)

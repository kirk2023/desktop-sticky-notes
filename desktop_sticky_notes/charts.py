"""
简单条形图组件 - 用于归档分析的投入统计（QPainter 自绘，无第三方图表依赖）
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont

AMBER = "#F59E0B"
AMBER_LIGHT = "#FDE68A"
TEXT_PRIMARY = "#1C1917"
TEXT_TERTIARY = "#78716C"
TEXT_DISABLED = "#A8A29E"
BORDER = "#E7E5E4"


class BarChartWidget(QWidget):
    """极简条形图：垂直或水平条形，带数值与标签"""

    def __init__(self, title="", horizontal=False, parent=None):
        super().__init__(parent)
        self.title = title
        self.horizontal = horizontal
        self.labels = []
        self.values = []
        self.unit = "h"
        self.setMinimumHeight(170)
        self.setMinimumWidth(220)

    def set_data(self, labels, values, unit="h"):
        self.labels = list(labels)
        self.values = list(values)
        self.unit = unit
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor("#FFFFFF"))
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 10, 10)

        # 标题
        painter.setPen(QPen(QColor(TEXT_TERTIARY)))
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        painter.drawText(QRectF(12, 6, w - 24, 20),
                         Qt.AlignLeft | Qt.AlignVCenter, self.title)

        area = QRectF(12, 32, w - 24, h - 44)
        if not self.values:
            painter.setPen(QPen(QColor(TEXT_DISABLED)))
            painter.setFont(QFont("Microsoft YaHei", 9))
            painter.drawText(area, Qt.AlignCenter, "暂无数据")
            painter.end()
            return

        max_v = max(self.values) or 1
        n = max(len(self.values), 1)
        painter.setFont(QFont("Microsoft YaHei", 8))

        if self.horizontal:
            step = area.height() / n
            bar_h = min(18.0, step - 8)
            label_w = 78
            val_w = 46
            bar_max = area.width() - label_w - val_w
            for i, (label, val) in enumerate(zip(self.labels, self.values)):
                y = area.y() + i * step + (step - bar_h) / 2
                painter.setPen(QPen(QColor(TEXT_TERTIARY)))
                painter.drawText(QRectF(area.x(), y, label_w - 8, bar_h),
                                 Qt.AlignVCenter | Qt.AlignRight, self._elide(label))
                bw = max(bar_max * val / max_v, 2) if val > 0 else 2
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(AMBER if val > 0 else AMBER_LIGHT))
                painter.drawRoundedRect(
                    QRectF(area.x() + label_w, y, bw, bar_h), 3, 3)
                painter.setPen(QPen(QColor(TEXT_PRIMARY)))
                painter.drawText(
                    QRectF(area.x() + label_w + bw + 4, y, val_w - 4, bar_h),
                    Qt.AlignVCenter | Qt.AlignLeft, f"{val:g}{self.unit}")
        else:
            slot = area.width() / n
            bar_w = min(36.0, slot - 14)
            val_h = 14
            label_h = 16
            bar_max = area.height() - val_h - label_h - 6
            for i, (label, val) in enumerate(zip(self.labels, self.values)):
                x = area.x() + i * slot + (slot - bar_w) / 2
                bh = max(bar_max * val / max_v, 2) if val > 0 else 2
                by = area.y() + val_h + (bar_max - bh)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(AMBER if val > 0 else AMBER_LIGHT))
                painter.drawRoundedRect(QRectF(x, by, bar_w, bh), 3, 3)
                painter.setPen(QPen(QColor(TEXT_PRIMARY)))
                painter.drawText(
                    QRectF(area.x() + i * slot, by - val_h - 2, slot, val_h),
                    Qt.AlignCenter, f"{val:g}{self.unit}")
                painter.setPen(QPen(QColor(TEXT_TERTIARY)))
                painter.drawText(
                    QRectF(area.x() + i * slot, area.bottom() - label_h + 2, slot, label_h),
                    Qt.AlignCenter, self._elide(label))
        painter.end()

    @staticmethod
    def _elide(text, max_len=9):
        text = str(text)
        if len(text) <= max_len:
            return text
        return text[:max_len - 1] + "…"

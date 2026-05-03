"""
休息提醒模块 - 全屏猫咪遮罩 + 倒计时
"""

import os
import sys

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QPainter, QLinearGradient, QColor


def get_resource_path(filename):
    """获取资源文件路径（兼容 PyInstaller onefile 模式）"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


class RestReminderDialog(QDialog):
    """全屏休息提醒对话框"""

    rest_finished = pyqtSignal()  # 休息结束信号

    def __init__(self, rest_duration_minutes, parent=None):
        super().__init__(parent)
        self.rest_duration_minutes = rest_duration_minutes
        self.remaining_seconds = rest_duration_minutes * 60

        # 全屏无边框，置顶
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.showFullScreen()

        self._setup_ui()
        self._start_countdown()

    def _setup_ui(self):
        """设置界面"""
        # 中央容器
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        # 猫咪图片
        cat_label = QLabel()
        cat_label.setAlignment(Qt.AlignCenter)
        cat_path = get_resource_path("rest_cat.png")
        if os.path.exists(cat_path):
            pixmap = QPixmap(cat_path)
            # 保持宽高比，占屏幕约45%高度
            screen_height = self.height()
            target_height = int(screen_height * 0.45)
            if pixmap.height() > 0:
                scaled = pixmap.scaledToHeight(
                    target_height, Qt.SmoothTransformation
                )
                cat_label.setPixmap(scaled)
        layout.addWidget(cat_label)

        # 倒计时标签
        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setFont(
            QFont("Microsoft YaHei", 48, QFont.Bold)
        )
        self.countdown_label.setStyleSheet("color: #4a4a6a;")
        self._update_countdown_text()
        layout.addWidget(self.countdown_label)

        # 提示文字
        tip_label = QLabel("休息一下吧~")
        tip_label.setAlignment(Qt.AlignCenter)
        tip_label.setFont(QFont("Microsoft YaHei", 18))
        tip_label.setStyleSheet("color: #7a7a9a;")
        layout.addWidget(tip_label)

        # 底部提示
        bottom_label = QLabel("休息期间请离开屏幕，放松眼睛和身体")
        bottom_label.setAlignment(Qt.AlignCenter)
        bottom_label.setFont(QFont("Microsoft YaHei", 12))
        bottom_label.setStyleSheet("color: #aaaacc;")
        layout.addWidget(bottom_label)

        self._central_widget = central

    def paintEvent(self, event):
        """绘制渐变背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 柔和渐变背景：淡蓝到淡紫
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#e8f4fd"))
        gradient.setColorAt(1, QColor("#f3e8ff"))
        painter.fillRect(self.rect(), gradient)
        painter.end()

    def resizeEvent(self, event):
        """窗口大小变化时重新布局"""
        super().resizeEvent(event)
        if hasattr(self, '_central_widget'):
            self._central_widget.setGeometry(self.rect())

    def showEvent(self, event):
        """显示时布局"""
        super().showEvent(event)
        if hasattr(self, '_central_widget'):
            self._central_widget.setGeometry(self.rect())

    def _start_countdown(self):
        """启动倒计时"""
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._update_countdown)
        self.countdown_timer.start(1000)  # 每秒更新

    def _update_countdown(self):
        """每秒更新倒计时"""
        self.remaining_seconds -= 1
        self._update_countdown_text()

        if self.remaining_seconds <= 0:
            self.countdown_timer.stop()
            self.rest_finished.emit()
            self.close()

    def _update_countdown_text(self):
        """更新倒计时显示文本"""
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.countdown_label.setText(
            f"休息还剩 {minutes:02d}:{seconds:02d}"
        )

    def keyPressEvent(self, event):
        """禁止通过按键关闭"""
        # ESC键不关闭
        if event.key() == Qt.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """禁止手动关闭（仅允许倒计时结束自动关闭）"""
        if self.remaining_seconds > 0:
            event.ignore()
            return
        super().closeEvent(event)

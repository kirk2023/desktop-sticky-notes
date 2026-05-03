"""
休息提醒模块 - 全屏猫咪遮罩 + 倒计时
"""

import os
import sys

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QWidget, QPushButton, QMessageBox)
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
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._setup_ui()
        self._start_countdown()

    def _setup_ui(self):
        """设置界面"""
        # 中央容器
        central = QWidget(self)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- 顶部区域：倒计时 ----
        top_area = QWidget()
        top_layout = QVBoxLayout(top_area)
        top_layout.setContentsMargins(0, 40, 0, 10)
        top_layout.setAlignment(Qt.AlignCenter)
        top_layout.setSpacing(8)

        title_label = QLabel("倒计时")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 20))
        title_label.setStyleSheet("color: #5a5a7a; background: transparent; border: none;")
        top_layout.addWidget(title_label)

        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setFont(QFont("Microsoft YaHei", 72, QFont.Bold))
        self.countdown_label.setStyleSheet("color: #3a3a5a; background: transparent; border: none;")
        self._update_countdown_text()
        top_layout.addWidget(self.countdown_label)

        tip_label = QLabel("休息一下吧~ 离开屏幕，放松眼睛和身体")
        tip_label.setAlignment(Qt.AlignCenter)
        tip_label.setFont(QFont("Microsoft YaHei", 14))
        tip_label.setStyleSheet("color: #8888aa; background: transparent; border: none;")
        top_layout.addWidget(tip_label)

        main_layout.addWidget(top_area, 1)

        # ---- 中间区域：猫咪横幅 ----
        cat_container = QWidget()
        cat_layout = QHBoxLayout(cat_container)
        cat_layout.setContentsMargins(40, 0, 40, 0)

        cat_label = QLabel()
        cat_label.setAlignment(Qt.AlignCenter)
        cat_label.setStyleSheet("background: transparent; border: none;")
        cat_path = get_resource_path("rest_cat.png")
        if os.path.exists(cat_path):
            pixmap = QPixmap(cat_path)
            if not pixmap.isNull():
                cat_label.setPixmap(pixmap)
                cat_label.setScaledContents(False)
        cat_layout.addWidget(cat_label)

        main_layout.addWidget(cat_container, 5)

        # ---- 底部区域：跳过按钮 ----
        bottom_area = QWidget()
        bottom_layout = QVBoxLayout(bottom_area)
        bottom_layout.setContentsMargins(0, 10, 0, 40)
        bottom_layout.setAlignment(Qt.AlignCenter)

        self.skip_btn = QPushButton("提前结束休息")
        self.skip_btn.setFont(QFont("Microsoft YaHei", 12))
        self.skip_btn.setFixedSize(200, 44)
        self.skip_btn.setCursor(Qt.PointingHandCursor)
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.6);
                color: #8888aa;
                border: 1px solid rgba(150, 150, 180, 0.4);
                border-radius: 22px;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.9);
                color: #5a5a7a;
                border-color: #aaaacc;
            }
        """)
        self.skip_btn.clicked.connect(self._on_skip_clicked)
        bottom_layout.addWidget(self.skip_btn)

        main_layout.addWidget(bottom_area, 1)

        self._central_widget = central
        self._cat_label = cat_label

    def resizeEvent(self, event):
        """窗口大小变化时重新布局和缩放猫咪"""
        super().resizeEvent(event)
        if hasattr(self, '_central_widget'):
            self._central_widget.setGeometry(self.rect())
        self._resize_cat()

    def _resize_cat(self):
        """按屏幕宽度缩放猫咪图片，保持宽高比"""
        if not hasattr(self, '_cat_label'):
            return
        cat_path = get_resource_path("rest_cat.png")
        if not os.path.exists(cat_path):
            return
        pixmap = QPixmap(cat_path)
        if pixmap.isNull():
            return
        # 猫咪占屏幕宽度约70%，高度自适应
        screen_width = self.width()
        target_width = int(screen_width * 0.7)
        if pixmap.width() > 0:
            scaled = pixmap.scaledToWidth(
                target_width, Qt.SmoothTransformation
            )
            self._cat_label.setPixmap(scaled)
            self._cat_label.setFixedSize(scaled.size())

    def showEvent(self, event):
        """显示时布局并全屏"""
        super().showEvent(event)
        self.showFullScreen()
        if hasattr(self, '_central_widget'):
            self._central_widget.setGeometry(self.rect())
        # 延迟缩放猫咪（确保窗口尺寸已确定）
        QTimer.singleShot(100, self._resize_cat)

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
        self.countdown_label.setText(f"{minutes:02d}:{seconds:02d}")

    def _on_skip_clicked(self):
        """跳过按钮点击 - 二次确认"""
        reply = QMessageBox.question(
            self, "提前结束休息",
            "休息时间还没到哦，确定要提前结束吗？\n身体才是革命的本钱！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.countdown_timer.stop()
            self.rest_finished.emit()
            self.close()

    def keyPressEvent(self, event):
        """ESC键不关闭"""
        if event.key() == Qt.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """倒计时未结束时禁止手动关闭"""
        if self.remaining_seconds > 0:
            event.ignore()
            return
        super().closeEvent(event)

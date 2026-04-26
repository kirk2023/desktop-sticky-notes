"""
便利贴卡片组件 - 可拖拽、可缩放的桌面卡片
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QGraphicsDropShadowEffect,
                              QSizePolicy, QApplication)
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QDateTime, QRect, QSize
from PyQt5.QtGui import (QFont, QColor, QCursor, QPainter, QPen, QBrush,
                          QLinearGradient, QPainterPath)


# 缩放区域边距（像素）- 增大以提升易用性
RESIZE_MARGIN = 12
# 最小/最大卡片尺寸
MIN_SIZE = QSize(220, 180)
MAX_SIZE = QSize(500, 500)


class StickyNoteCard(QWidget):
    """便利贴卡片 - 可拖拽、可缩放的桌面小部件"""

    # 信号
    start_timer_signal = pyqtSignal(int)
    stop_timer_signal = pyqtSignal(int)
    complete_signal = pyqtSignal(int)
    close_signal = pyqtSignal(int)
    position_changed = pyqtSignal(int, int, int)  # event_id, x, y
    size_changed = pyqtSignal(int, int, int)      # event_id, w, h

    def __init__(self, event_data, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.event_id = event_data['id']
        self.is_timing = False
        self.accumulated_seconds = 0  # 之前累计的秒数（暂停前的时间）
        self.session_start_time = None  # 当前会话开始的时间
        self._drag_pos = None
        self._resize_dir = None
        self.is_always_on_top = True

        # 卡片大小（从事件数据读取或使用默认值）
        w = event_data.get('card_width', 280)
        h = event_data.get('card_height', 220)
        w = max(MIN_SIZE.width(), min(MAX_SIZE.width(), w))
        h = max(MIN_SIZE.height(), min(MAX_SIZE.height(), h))

        # 计时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer_display)

        self._setup_ui(w, h)
        self._apply_style()

    def _setup_ui(self, w, h):
        """设置 UI"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(w, h)
        self.setMinimumSize(MIN_SIZE)
        self.setMaximumSize(MAX_SIZE)
        self.setCursor(QCursor(Qt.ArrowCursor))

        # 主容器
        self.container = QFrame(self)
        self.container.setObjectName("cardContainer")
        self._update_container_geometry()

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # 标题栏
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(self.event_data.get('title', '未命名事件'))
        self.title_label.setObjectName("titleLabel")
        self.title_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.title_label.setWordWrap(True)
        title_bar.addWidget(self.title_label, 1)

        # 置顶切换按钮
        self.pin_top_btn = QPushButton("📌")
        self.pin_top_btn.setObjectName("pinTopBtn")
        self.pin_top_btn.setFixedSize(24, 24)
        self.pin_top_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.pin_top_btn.setToolTip("点击切换置顶/取消置顶")
        self.pin_top_btn.clicked.connect(self._toggle_always_on_top)
        title_bar.addWidget(self.pin_top_btn)

        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.close_btn.clicked.connect(lambda: self.close_signal.emit(self.event_id))
        title_bar.addWidget(self.close_btn)

        layout.addLayout(title_bar)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("separator")
        layout.addWidget(line)

        # 计划时间信息
        self.time_info_label = QLabel()
        self.time_info_label.setObjectName("timeInfoLabel")
        self.time_info_label.setFont(QFont("Microsoft YaHei", 9))
        self.time_info_label.setWordWrap(True)
        layout.addWidget(self.time_info_label)
        self._update_time_info()

        # 描述
        if self.event_data.get('description'):
            desc_label = QLabel(self.event_data['description'])
            desc_label.setObjectName("descLabel")
            desc_label.setFont(QFont("Microsoft YaHei", 8))
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        layout.addStretch()

        # 计时显示
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setObjectName("timerLabel")
        self.timer_label.setFont(QFont("Consolas", 18, QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.timer_label)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.start_btn = QPushButton("▶ 开始")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.start_btn.clicked.connect(self._on_start_clicked)

        self.complete_btn = QPushButton("✓ 完成")
        self.complete_btn.setObjectName("completeBtn")
        self.complete_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.complete_btn.clicked.connect(self._on_complete_clicked)
        self.complete_btn.setEnabled(False)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.complete_btn)
        layout.addLayout(btn_layout)

    def _update_container_geometry(self):
        """更新容器几何位置（留出阴影+缩放区域空间）"""
        margin = RESIZE_MARGIN  # 使用和缩放区域相同的边距
        self.container.setGeometry(margin, margin,
                                  self.width() - margin * 2,
                                  self.height() - margin * 2)

    def resizeEvent(self, event):
        """窗口大小改变时更新容器和字体"""
        super().resizeEvent(event)
        self._update_container_geometry()
        # 根据卡片大小动态调整字体
        self._adjust_fonts()

    def _adjust_fonts(self):
        """根据卡片大小动态调整字体大小"""
        w = self.width()
        h = self.height()
        # 基准尺寸 280x220
        base_w, base_h = 280, 220
        scale = min(w / base_w, h / base_h, 1.3)  # 最大放大1.3倍
        scale = max(scale, 0.7)  # 最小缩小到0.7倍

        title_size = max(int(11 * scale), 8)
        info_size = max(int(9 * scale), 7)
        timer_size = max(int(18 * scale), 12)

        if hasattr(self, 'title_label'):
            self.title_label.setFont(QFont("Microsoft YaHei", title_size, QFont.Bold))
        if hasattr(self, 'time_info_label'):
            self.time_info_label.setFont(QFont("Microsoft YaHei", info_size))
        if hasattr(self, 'desc_label'):
            self.desc_label.setFont(QFont("Microsoft YaHei", max(int(8 * scale), 6)))
        if hasattr(self, 'timer_label'):
            self.timer_label.setFont(QFont("Consolas", timer_size, QFont.Bold))

    def _apply_style(self):
        """应用便利贴风格样式"""
        color = self.event_data.get('color', '#FFF9C4')

        self.container.setStyleSheet(f"""
            #cardContainer {{
                background-color: transparent;
                border: 1px solid rgba(0,0,0,0.08);
                border-radius: 8px;
            }}
            #titleLabel {{
                color: #333333;
                background: transparent;
                border: none;
                padding: 2px;
            }}
            #closeBtn {{
                background-color: transparent;
                color: #999999;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
            }}
            #closeBtn:hover {{
                background-color: rgba(255,0,0,0.15);
                color: #e74c3c;
            }}
            #pinTopBtn {{
                background-color: transparent;
                color: #999999;
                border: none;
                border-radius: 12px;
                font-size: 14px;
            }}
            #pinTopBtn:hover {{
                background-color: rgba(52,152,219,0.15);
                color: #3498db;
            }}
            #separator {{
                background-color: rgba(0,0,0,0.1);
                max-height: 1px;
            }}
            #timeInfoLabel {{
                color: #555555;
                background: transparent;
                border: none;
                padding: 2px;
            }}
            #descLabel {{
                color: #666666;
                background: transparent;
                border: none;
                padding: 2px;
            }}
            #timerLabel {{
                color: #2c3e50;
                background: transparent;
                border: none;
                padding: 4px;
            }}
            #startBtn {{
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            #startBtn:hover {{
                background-color: #2ecc71;
            }}
            #startBtn:disabled {{
                background-color: #bdc3c7;
                color: #7f8c8d;
            }}
            #completeBtn {{
                background-color: #2980b9;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            #completeBtn:hover {{
                background-color: #3498db;
            }}
            #completeBtn:disabled {{
                background-color: #bdc3c7;
                color: #7f8c8d;
            }}
        """)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(3, 3)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.container.setGraphicsEffect(shadow)

    # ==================== 渐变色绘制 ====================

    def paintEvent(self, event):
        """绘制渐变背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        color = QColor(self.event_data.get('color', '#FFF9C4'))
        margin = 5

        # 创建圆角路径
        path = QPainterPath()
        path.addRoundedRect(margin, margin,
                            self.width() - margin * 2,
                            self.height() - margin * 2, 8, 8)

        # 创建从上到下的渐变：原色 → 更浅的白色混合
        gradient = QLinearGradient(0, margin, 0, self.height() - margin)
        gradient.setColorAt(0.0, color)
        # 底部混入白色，让颜色更柔和
        lighter = QColor(
            min(color.red() + 60, 255),
            min(color.green() + 60, 255),
            min(color.blue() + 60, 255),
            200
        )
        gradient.setColorAt(1.0, lighter)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(path)

    # ==================== 缩放区域检测 ====================

    def _get_resize_direction(self, pos):
        """根据鼠标位置判断缩放方向"""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = RESIZE_MARGIN

        directions = 0

        # 左边缘
        if x < m:
            directions |= 1  # 左
        # 右边缘
        elif x > w - m:
            directions |= 2  # 右

        # 上边缘
        if y < m:
            directions |= 4  # 上
        # 下边缘
        elif y > h - m:
            directions |= 8  # 下

        return directions

    def _direction_to_cursor(self, direction):
        """根据方向返回对应鼠标样式"""
        cursors = {
            0: Qt.ArrowCursor,      # 中间 - 拖拽
            1: Qt.SizeHorCursor,    # 左
            2: Qt.SizeHorCursor,    # 右
            3: Qt.SizeFDiagCursor,  # 左右 = 水平（不应出现）
            4: Qt.SizeVerCursor,    # 上
            5: Qt.SizeFDiagCursor,  # 左上
            6: Qt.SizeBDiagCursor,  # 右上
            7: Qt.SizeAllCursor,    # 上下（不应出现）
            8: Qt.SizeVerCursor,    # 下
            9: Qt.SizeBDiagCursor,  # 左下
            10: Qt.SizeFDiagCursor, # 右下
        }
        return cursors.get(direction, Qt.ArrowCursor)

    # ==================== 鼠标事件（拖拽 + 缩放） ====================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            direction = self._get_resize_direction(event.pos())
            if direction == 0:
                # 中间区域 - 拖拽
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                self._resize_dir = None
            else:
                # 边缘区域 - 缩放
                self._resize_dir = direction
                self._resize_start_geo = self.geometry()
                self._resize_start_pos = event.globalPos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if self._resize_dir:
                # 缩放模式
                self._do_resize(event.globalPos())
            elif self._drag_pos:
                # 拖拽模式
                self.move(event.globalPos() - self._drag_pos)
                pos = self.pos()
                self.position_changed.emit(self.event_id, pos.x(), pos.y())
            event.accept()
        else:
            # 悬停时更新鼠标样式
            direction = self._get_resize_direction(event.pos())
            self.setCursor(QCursor(self._direction_to_cursor(direction)))

    def mouseReleaseEvent(self, event):
        if self._resize_dir:
            # 缩放结束，通知大小变化
            self.size_changed.emit(self.event_id, self.width(), self.height())
        self._drag_pos = None
        self._resize_dir = None
        event.accept()

    def _do_resize(self, global_pos):
        """执行缩放操作"""
        if not self._resize_dir or not self._resize_start_geo:
            return

        delta = global_pos - self._resize_start_pos
        geo = QRect(self._resize_start_geo)
        d = self._resize_dir

        new_x = geo.x()
        new_y = geo.y()
        new_w = geo.width()
        new_h = geo.height()

        # 左边缘
        if d & 1:
            new_x = geo.x() + delta.x()
            new_w = geo.width() - delta.x()
        # 右边缘
        if d & 2:
            new_w = geo.width() + delta.x()
        # 上边缘
        if d & 4:
            new_y = geo.y() + delta.y()
            new_h = geo.height() - delta.y()
        # 下边缘
        if d & 8:
            new_h = geo.height() + delta.y()

        # 限制最小/最大尺寸
        if new_w < MIN_SIZE.width():
            if d & 1:
                new_x = geo.right() - MIN_SIZE.width()
            new_w = MIN_SIZE.width()
        if new_w > MAX_SIZE.width():
            new_w = MAX_SIZE.width()
        if new_h < MIN_SIZE.height():
            if d & 4:
                new_y = geo.bottom() - MIN_SIZE.height()
            new_h = MIN_SIZE.height()
        if new_h > MAX_SIZE.height():
            new_h = MAX_SIZE.height()

        self.setGeometry(new_x, new_y, new_w, new_h)

    # ==================== 业务逻辑 ====================

    def _update_time_info(self):
        """更新时间信息显示"""
        planned_start = self.event_data.get('planned_start', '')
        duration = self.event_data.get('planned_duration_minutes', 30)

        if planned_start:
            try:
                dt = QDateTime.fromString(planned_start, "yyyy-MM-dd HH:mm")
                time_str = dt.toString("HH:mm")
                date_str = dt.toString("MM月dd日")
                self.time_info_label.setText(
                    f"📅 {date_str}  ⏰ {time_str}  ⏱ 计划 {duration} 分钟")
            except Exception:
                self.time_info_label.setText(f"⏱ 计划 {duration} 分钟")
        else:
            self.time_info_label.setText(f"⏱ 计划 {duration} 分钟")

    def _on_start_clicked(self):
        """点击开始/暂停按钮"""
        if not self.is_timing:
            # 开始或恢复计时
            self.is_timing = True
            self.session_start_time = QDateTime.currentDateTime()
            self.start_btn.setText("⏸ 暂停")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e67e22;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #f39c12;
                }
            """)
            self.complete_btn.setEnabled(True)
            # 通知主窗口开始/恢复计时
            self.start_timer_signal.emit(self.event_id)
            self.timer.start(1000)
        else:
            # 暂停计时
            self.is_timing = False
            self.timer.stop()
            # 累加本次会话时间
            if self.session_start_time:
                session_secs = self.session_start_time.secsTo(QDateTime.currentDateTime())
                self.accumulated_seconds += session_secs
                self.session_start_time = None
            self.start_btn.setText("▶ 继续")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2ecc71;
                }
            """)
            # 通知主窗口暂停
            self.stop_timer_signal.emit(self.event_id)

    def sync_start(self):
        """从主窗口同步开始状态（列表按钮点击时调用）"""
        if not self.is_timing:
            self.is_timing = True
            self.session_start_time = QDateTime.currentDateTime()
            self.start_btn.setText("⏸ 暂停")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e67e22;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #f39c12;
                }
            """)
            self.complete_btn.setEnabled(True)
            self.timer.start(1000)

    def sync_pause(self):
        """从主窗口同步暂停状态（列表按钮点击时调用）"""
        if self.is_timing:
            self.is_timing = False
            self.timer.stop()
            if self.session_start_time:
                session_secs = self.session_start_time.secsTo(QDateTime.currentDateTime())
                self.accumulated_seconds += session_secs
                self.session_start_time = None
            self.start_btn.setText("▶ 继续")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2ecc71;
                }
            """)

    def _on_complete_clicked(self):
        """点击完成按钮"""
        self.timer.stop()
        # 累加最后一段会话时间
        if self.session_start_time:
            session_secs = self.session_start_time.secsTo(QDateTime.currentDateTime())
            self.accumulated_seconds += session_secs
            self.session_start_time = None
        self.is_timing = False
        self.complete_signal.emit(self.event_id)

    def _toggle_always_on_top(self):
        """切换置顶状态"""
        self.is_always_on_top = not self.is_always_on_top
        # 保存当前位置
        pos = self.pos()
        # 保存当前大小
        size = self.size()

        if self.is_always_on_top:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.pin_top_btn.setText("📌")
            self.pin_top_btn.setToolTip("当前: 始终置顶 | 点击取消置顶")
        else:
            # 使用 Window 类型而非 Tool，确保可以被其他窗口遮挡
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
            self.pin_top_btn.setText("📍")
            self.pin_top_btn.setToolTip("当前: 普通窗口 | 点击置顶")

        # setWindowFlags 会隐藏窗口，需要重新显示并恢复属性
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(pos.x(), pos.y(), size.width(), size.height())
        self.show()

    def _get_total_seconds(self):
        """获取当前总计时秒数（累计 + 当前会话）"""
        total = self.accumulated_seconds
        if self.session_start_time and self.is_timing:
            total += self.session_start_time.secsTo(QDateTime.currentDateTime())
        return total

    def _update_timer_display(self):
        """更新计时器显示"""
        total = self._get_total_seconds()
        hours = total // 3600
        minutes = (total % 3600) // 60
        seconds = total % 60
        self.timer_label.setText(
            f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def set_elapsed_time(self, seconds):
        """设置已累计时间（用于恢复状态）"""
        self.accumulated_seconds = seconds
        self._update_timer_display()

    def resume_timing(self, accumulated_seconds, session_start_str=None):
        """
        恢复计时状态（从数据库恢复）

        Args:
            accumulated_seconds: 之前累计的秒数
            session_start_str: 当前会话的开始时间字符串（如果有进行中的会话）
        """
        self.accumulated_seconds = accumulated_seconds

        if session_start_str:
            # 有进行中的会话，恢复实时计时
            from datetime import datetime
            try:
                start = datetime.strptime(session_start_str, "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                session_secs = int((now - start).total_seconds())
                self.session_start_time = QDateTime.currentDateTime().addSecs(-session_secs)
                self.is_timing = True
                self.start_btn.setText("⏸ 暂停")
                self.complete_btn.setEnabled(True)
                self.timer.start(1000)
            except (ValueError, TypeError):
                pass
        elif accumulated_seconds > 0:
            # 有累计时间但没有进行中的会话（之前暂停过）
            self.start_btn.setText("▶ 继续")
            self.complete_btn.setEnabled(True)

    def show_completion_summary(self, planned_minutes, actual_seconds):
        """显示完成摘要"""
        actual_minutes = round(actual_seconds / 60, 1)
        diff = planned_minutes - actual_minutes

        if diff > 0:
            result = f"✅ 提前 {diff:.1f} 分钟完成！"
            color = "#27ae60"
        elif diff < 0:
            result = f"⚠️ 超时 {abs(diff):.1f} 分钟"
            color = "#e74c3c"
        else:
            result = "✅ 刚好按时完成！"
            color = "#2980b9"

        self.timer_label.setText(result)
        self.timer_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background: transparent;
                border: none;
                font-size: 11px;
                padding: 4px;
            }}
        """)
        self.start_btn.setEnabled(False)
        self.complete_btn.setEnabled(False)
        self.complete_btn.setText("已归档")

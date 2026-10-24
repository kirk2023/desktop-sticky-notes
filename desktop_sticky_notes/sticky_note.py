"""
Sticky Note Card - Premium Redesign
Draggable, resizable desktop sticky note with sophisticated styling
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QGraphicsDropShadowEffect,
                              QSizePolicy, QApplication, QGraphicsOpacityEffect,
                              QLineEdit, QTextEdit)
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QDateTime, QRect, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import (QFont, QColor, QCursor, QPainter, QPen, QBrush,
                          QLinearGradient, QPainterPath, QRadialGradient, QPixmap)

from design_system import C, F, R, NC


# Resize margin (px) - increase for better usability
RESIZE_MARGIN = 14
# Min/max card size
MIN_SIZE = QSize(240, 200)
MAX_SIZE = QSize(520, 520)


class StickyNoteCard(QWidget):
    """Premium sticky note card — draggable, resizable, always-on-top"""

    # Signals
    start_timer_signal = pyqtSignal(int)
    stop_timer_signal = pyqtSignal(int)
    complete_signal = pyqtSignal(int)
    close_signal = pyqtSignal(int)
    position_changed = pyqtSignal(int, int, int)  # event_id, x, y
    size_changed = pyqtSignal(int, int, int)      # event_id, w, h
    content_changed = pyqtSignal(int, str, str)   # event_id, title, description

    def __init__(self, event_data, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.event_id = event_data['id']
        self.is_timing = False
        self.accumulated_seconds = 0
        self.session_start_time = None
        self._drag_pos = None
        self._drag_moved = False
        self._resize_dir = None
        self.is_always_on_top = True

        # Card size
        w = event_data.get('card_width', 280)
        h = event_data.get('card_height', 220)
        w = max(MIN_SIZE.width(), min(MAX_SIZE.width(), w))
        h = max(MIN_SIZE.height(), min(MAX_SIZE.height(), h))

        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer_display)

        # 内容编辑保存防抖（停止输入 700ms 后统一保存）
        self._save_debounce = QTimer(self)
        self._save_debounce.setSingleShot(True)
        self._save_debounce.timeout.connect(self._emit_content_changed)

        self._note_color = QColor(event_data.get('color', NC.YELLOW))

        self._setup_ui(w, h)
        self._apply_style()

    def apply_event_state(self, elapsed_seconds=0, has_active_session=False):
        """根据事项状态调整卡片按钮，避免状态与按钮不匹配

        - completed：按钮变为"已完成"并禁用，显示累计投入
        - 有历史投入且无进行中会话（暂停/被拖回起始甬道）：显示"继续"，完成可用
        - 正在计时：由 resume_timing 处理（显示"暂停"）
        - 从未开始的 pending：保持默认"开始" + 完成禁用
        """
        status = self.event_data.get('status', 'pending')
        if status == 'completed':
            self.start_btn.setText("已完成")
            self.start_btn.setEnabled(False)
            self.complete_btn.setText("已完成")
            self.complete_btn.setEnabled(False)
            self.start_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C.SLATE_200};
                    color: {C.SLATE_500};
                    border: none;
                    border-radius: {R.MD};
                    font-weight: 600;
                    font-size: 12px;
                }}
            """)
            if elapsed_seconds > 0:
                self.set_elapsed_time(elapsed_seconds)
        elif not has_active_session and elapsed_seconds > 0:
            self.start_btn.setText("继续")
            self.complete_btn.setEnabled(True)
            self.set_elapsed_time(elapsed_seconds)

    def _setup_ui(self, w, h):
        """Setup premium UI"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(w, h)
        self.setMinimumSize(MIN_SIZE)
        self.setMaximumSize(MAX_SIZE)
        self.setCursor(QCursor(Qt.ArrowCursor))

        # Main container with rounded corners
        self.container = QFrame(self)
        self.container.setObjectName("cardContainer")
        self._update_container_geometry()

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(2)

        # ---- Title Bar ----
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)
        title_bar.setSpacing(6)

        # Color indicator dot
        self.color_dot = QFrame()
        self.color_dot.setFixedSize(8, 8)
        self.color_dot.setStyleSheet(f"""
            background-color: {self._get_darker_color()};
            border-radius: 4px;
        """)
        title_bar.addWidget(self.color_dot)

        # Title（可直接编辑，点击即输入）
        self.title_edit = QLineEdit(self.event_data.get('title', '未命名'))
        self.title_edit.setObjectName("titleLabel")
        self.title_edit.setFont(F.bold(11))
        self.title_edit.setPlaceholderText("输入标题…")
        self.title_edit.setStyleSheet(f"""
            QLineEdit {{
                color: {C.TEXT_PRIMARY}; background: transparent; border: none;
                padding: 2px 4px; font-weight: bold;
            }}
            QLineEdit:hover {{
                background: rgba(0,0,0,25); border-radius: 4px;
            }}
            QLineEdit:focus {{
                background: rgba(255,255,255,150); border-radius: 4px;
            }}
        """)
        self.title_edit.textChanged.connect(self._on_content_edited)
        title_bar.addWidget(self.title_edit, 1)

        # Pin toggle button (icon-based)
        self.pin_top_btn = QPushButton()
        self.pin_top_btn.setObjectName("pinTopBtn")
        self.pin_top_btn.setFixedSize(22, 22)
        self.pin_top_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.pin_top_btn.setToolTip("置顶显示")
        self.pin_top_btn.setProperty("pinned", True)
        self.pin_top_btn.setText("📌")
        self.pin_top_btn.clicked.connect(self._toggle_always_on_top)
        title_bar.addWidget(self.pin_top_btn)

        # Close button
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.close_btn.setToolTip("关闭")
        self.close_btn.clicked.connect(lambda: self.close_signal.emit(self.event_id))
        title_bar.addWidget(self.close_btn)

        layout.addLayout(title_bar)

        # ---- Separator ----
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {self._get_darker_color(40)}; border: none;")
        layout.addWidget(sep)

        layout.addSpacing(4)

        # ---- Time Info ----
        self.time_info_label = QLabel()
        self.time_info_label.setObjectName("timeInfoLabel")
        self.time_info_label.setFont(F.size(9))
        self.time_info_label.setWordWrap(True)
        self.time_info_label.setStyleSheet(f"color: {C.TEXT_SECONDARY}; background: transparent; border: none;")
        layout.addWidget(self.time_info_label)
        self._update_time_info()

        # ---- Description（可直接编辑）----
        self.desc_edit = QTextEdit()
        self.desc_edit.setObjectName("descEdit")
        self.desc_edit.setPlaceholderText("添加备注…")
        self.desc_edit.setFont(F.size(9))
        self.desc_edit.setFixedHeight(46)
        self.desc_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.desc_edit.setPlainText(self.event_data.get('description', ''))
        self.desc_edit.setStyleSheet(f"""
            QTextEdit {{
                color: {C.TEXT_SECONDARY}; background: rgba(0,0,0,15);
                border: none; border-radius: 4px; padding: 2px 4px;
            }}
            QTextEdit:focus {{
                background: rgba(255,255,255,150); border-radius: 4px;
            }}
        """)
        self.desc_edit.textChanged.connect(self._on_content_edited)
        layout.addWidget(self.desc_edit)

        layout.addStretch()

        # ---- Timer Display ----
        timer_container = QFrame()
        timer_container.setObjectName("timerContainer")
        timer_container.setFixedHeight(48)
        timer_layout = QVBoxLayout(timer_container)
        timer_layout.setContentsMargins(0, 0, 0, 0)
        timer_layout.setAlignment(Qt.AlignCenter)

        self.timer_label = QLabel("00:00:00")
        self.timer_label.setObjectName("timerLabel")
        self.timer_label.setFont(F.mono(20, QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet(f"""
            color: {C.SLATE_600};
            background: transparent;
            border: none;
        """)
        timer_layout.addWidget(self.timer_label)

        layout.addWidget(timer_container)

        # ---- Action Buttons ----
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.start_btn = QPushButton("开始")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.start_btn.setFixedHeight(32)
        self.start_btn.clicked.connect(self._on_start_clicked)

        self.complete_btn = QPushButton("完成")
        self.complete_btn.setObjectName("completeBtn")
        self.complete_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.complete_btn.setFixedHeight(32)
        self.complete_btn.clicked.connect(self._on_complete_clicked)
        self.complete_btn.setEnabled(False)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.complete_btn)
        layout.addLayout(btn_layout)

    def _update_container_geometry(self):
        """Update container geometry (leave space for resize margin)"""
        margin = RESIZE_MARGIN
        self.container.setGeometry(margin, margin,
                                  self.width() - margin * 2,
                                  self.height() - margin * 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_container_geometry()
        self._adjust_fonts()

    def _adjust_fonts(self):
        """Dynamically adjust font sizes based on card size"""
        w = self.width()
        base_w = 280
        scale = min(w / base_w, 1.3)
        scale = max(scale, 0.75)

        title_size = max(int(11 * scale), 8)
        self.title_edit.setFont(F.bold(title_size))

        timer_size = max(int(20 * scale), 14)
        self.timer_label.setFont(F.mono(timer_size, QFont.Bold))

    def _get_darker_color(self, amount=50):
        """Get a darker shade of the note color"""
        h, s, l, a = self._note_color.getHslF()
        l = max(0, l - amount / 255)
        darker = QColor()
        darker.setHslF(h, s, l, a)
        return darker.name()

    def _apply_style(self):
        """Apply premium sticky note styling"""
        darker = self._get_darker_color(40)
        darkest = self._get_darker_color(80)

        self.container.setStyleSheet(f"""
            #cardContainer {{
                background-color: transparent;
                border: none;
                border-radius: {R.LG};
            }}
            #closeBtn {{
                background-color: transparent;
                color: {C.TEXT_TERTIARY};
                border: none;
                border-radius: {R.FULL};
                font-size: 18px;
                font-weight: normal;
                padding: 0;
                margin: 0;
            }}
            #closeBtn:hover {{
                background-color: {C.DANGER_LIGHT};
                color: {C.DANGER};
            }}
            #pinTopBtn {{
                background-color: transparent;
                color: {C.AMBER_500};
                border: none;
                border-radius: {R.FULL};
                font-size: 12px;
                padding: 0;
                margin: 0;
            }}
            #pinTopBtn:hover {{
                background-color: {C.AMBER_100};
            }}
            #pinTopBtn[pinned="false"] {{
                color: {C.TEXT_DISABLED};
            }}
            #timerContainer {{
                background-color: rgba(0,0,0,0.03);
                border-radius: {R.SM};
            }}
            #startBtn {{
                background-color: {C.AMBER_500};
                color: {C.WHITE};
                border: none;
                border-radius: {R.MD};
                font-weight: 600;
                font-size: 12px;
            }}
            #startBtn:hover {{
                background-color: {C.AMBER_600};
            }}
            #startBtn:disabled {{
                background-color: {C.SLATE_200};
                color: {C.SLATE_400};
            }}
            #completeBtn {{
                background-color: {C.SLATE_700};
                color: {C.WHITE};
                border: none;
                border-radius: {R.MD};
                font-weight: 600;
                font-size: 12px;
            }}
            #completeBtn:hover {{
                background-color: {C.SLATE_800};
            }}
            #completeBtn:disabled {{
                background-color: {C.SLATE_200};
                color: {C.SLATE_400};
            }}
        """)

        # Premium shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.container.setGraphicsEffect(shadow)

    # ==================== Gradient Background Painting ====================

    def paintEvent(self, event):
        """Paint gradient background with subtle texture"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        color = self._note_color
        margin = 5

        # Rounded rect path
        path = QPainterPath()
        path.addRoundedRect(margin, margin,
                            self.width() - margin * 2,
                            self.height() - margin * 2, 10, 10)

        # Top-to-bottom gradient: slightly darker at top, lighter at bottom
        gradient = QLinearGradient(0, margin, 0, self.height() - margin)
        top_color = QColor(color)
        h, s, l, a = top_color.getHslF()
        top_color.setHslF(h, max(0, s - 0.05), l, a)

        bottom_color = QColor(color)
        bh, bs, bl, ba = bottom_color.getHslF()
        bottom_color.setHslF(bh, bs, min(1, bl + 0.08), ba)

        gradient.setColorAt(0.0, top_color)
        gradient.setColorAt(0.5, color)
        gradient.setColorAt(1.0, bottom_color)

        painter.setPen(QPen(QColor(0, 0, 0, 20), 0.5))
        painter.setBrush(QBrush(gradient))
        painter.drawPath(path)

        # Subtle paper texture lines
        painter.setPen(QPen(QColor(0, 0, 0, 8), 0.5))
        y_start = margin + 40
        y_end = self.height() - margin - 60
        line_spacing = 18
        for y in range(int(y_start), int(y_end), line_spacing):
            painter.drawLine(int(margin + 8), y, int(self.width() - margin - 8), y)

    # ==================== Resize Logic ====================

    def _get_resize_direction(self, pos):
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = RESIZE_MARGIN

        directions = 0
        if x < m: directions |= 1
        elif x > w - m: directions |= 2
        if y < m: directions |= 4
        elif y > h - m: directions |= 8
        return directions

    def _direction_to_cursor(self, direction):
        cursors = {
            0: Qt.ArrowCursor,
            1: Qt.SizeHorCursor, 2: Qt.SizeHorCursor,
            4: Qt.SizeVerCursor, 8: Qt.SizeVerCursor,
            5: Qt.SizeFDiagCursor, 6: Qt.SizeBDiagCursor,
            9: Qt.SizeBDiagCursor, 10: Qt.SizeFDiagCursor,
        }
        return cursors.get(direction, Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            direction = self._get_resize_direction(event.pos())
            if direction == 0:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                self._resize_dir = None
            else:
                self._resize_dir = direction
                self._resize_start_geo = self.geometry()
                self._resize_start_pos = event.globalPos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if self._resize_dir:
                self._do_resize(event.globalPos())
            elif self._drag_pos:
                self.move(event.globalPos() - self._drag_pos)
                self._drag_moved = True
            event.accept()
        else:
            direction = self._get_resize_direction(event.pos())
            self.setCursor(QCursor(self._direction_to_cursor(direction)))

    def mouseReleaseEvent(self, event):
        if self._resize_dir:
            self.size_changed.emit(self.event_id, self.width(), self.height())
        elif self._drag_moved:
            # 拖动过程中不写库，松手时保存最终位置
            pos = self.pos()
            self.position_changed.emit(self.event_id, pos.x(), pos.y())
        self._drag_pos = None
        self._drag_moved = False
        self._resize_dir = None
        event.accept()

    def _do_resize(self, global_pos):
        if not self._resize_dir or not self._resize_start_geo:
            return
        delta = global_pos - self._resize_start_pos
        geo = QRect(self._resize_start_geo)
        d = self._resize_dir

        new_x, new_y = geo.x(), geo.y()
        new_w, new_h = geo.width(), geo.height()

        if d & 1: new_x = geo.x() + delta.x(); new_w = geo.width() - delta.x()
        if d & 2: new_w = geo.width() + delta.x()
        if d & 4: new_y = geo.y() + delta.y(); new_h = geo.height() - delta.y()
        if d & 8: new_h = geo.height() + delta.y()

        if new_w < MIN_SIZE.width():
            if d & 1: new_x = geo.right() - MIN_SIZE.width()
            new_w = MIN_SIZE.width()
        if new_w > MAX_SIZE.width(): new_w = MAX_SIZE.width()
        if new_h < MIN_SIZE.height():
            if d & 4: new_y = geo.bottom() - MIN_SIZE.height()
            new_h = MIN_SIZE.height()
        if new_h > MAX_SIZE.height(): new_h = MAX_SIZE.height()

        self.setGeometry(new_x, new_y, new_w, new_h)

    # ==================== Business Logic ====================

    def _update_time_info(self):
        planned_start = self.event_data.get('planned_start', '')
        duration = self.event_data.get('planned_duration_minutes', 30)

        if planned_start:
            try:
                dt = QDateTime.fromString(planned_start, "yyyy-MM-dd HH:mm")
                time_str = dt.toString("HH:mm")
                date_str = dt.toString("MM/dd")
                self.time_info_label.setText(f"{date_str} {time_str} · 计划 {duration} 分钟")
            except Exception:
                self.time_info_label.setText(f"计划 {duration} 分钟")
        else:
            self.time_info_label.setText(f"计划 {duration} 分钟")

    # ==================== 内容编辑（防抖保存） ====================

    def _on_content_edited(self):
        """标题/备注被编辑，启动防抖保存"""
        self._save_debounce.start(700)

    def _emit_content_changed(self):
        title = self.title_edit.text().strip()
        desc = self.desc_edit.toPlainText()
        self.event_data['title'] = title
        self.event_data['description'] = desc
        self.content_changed.emit(self.event_id, title, desc)

    def _on_start_clicked(self):
        """Start / pause timer"""
        if not self.is_timing:
            self.is_timing = True
            self.session_start_time = QDateTime.currentDateTime()
            self.start_btn.setText("暂停")
            self.start_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C.SLATE_600};
                    color: {C.WHITE};
                    border: none;
                    border-radius: {R.MD};
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {C.SLATE_700}; }}
            """)
            self.complete_btn.setEnabled(True)
            self.start_timer_signal.emit(self.event_id)
            self.timer.start(1000)
            # Pulse animation effect
            self._pulse_timer()
        else:
            self.is_timing = False
            self.timer.stop()
            if self.session_start_time:
                session_secs = self.session_start_time.secsTo(QDateTime.currentDateTime())
                self.accumulated_seconds += session_secs
                self.session_start_time = None
            self.start_btn.setText("继续")
            self.start_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C.AMBER_500};
                    color: {C.WHITE};
                    border: none;
                    border-radius: {R.MD};
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background-color: {C.AMBER_600}; }}
            """)
            self.stop_timer_signal.emit(self.event_id)

    def _pulse_timer(self):
        """Visual pulse when timer is running"""
        self.timer_label.setStyleSheet(f"""
            color: {C.AMBER_700};
            background: transparent;
            border: none;
        """)

    def _on_complete_clicked(self):
        """Complete button clicked"""
        self.timer.stop()
        if self.session_start_time:
            session_secs = self.session_start_time.secsTo(QDateTime.currentDateTime())
            self.accumulated_seconds += session_secs
            self.session_start_time = None
        self.is_timing = False
        self.complete_signal.emit(self.event_id)

    def _toggle_always_on_top(self):
        """Toggle always on top"""
        self.is_always_on_top = not self.is_always_on_top
        pos = self.pos()
        size = self.size()

        if self.is_always_on_top:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.pin_top_btn.setProperty("pinned", True)
            self.pin_top_btn.setToolTip("已置顶，点击取消置顶")
            self.pin_top_btn.setText("📌")
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
            self.pin_top_btn.setProperty("pinned", False)
            self.pin_top_btn.setToolTip("置顶显示")
            self.pin_top_btn.setText("○")

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.show()
        self.container.style().unpolish(self.container)
        self.container.style().polish(self.container)
        QTimer.singleShot(0, lambda: self.setGeometry(pos.x(), pos.y(), size.width(), size.height()))

    def _get_total_seconds(self):
        total = self.accumulated_seconds
        if self.session_start_time and self.is_timing:
            total += self.session_start_time.secsTo(QDateTime.currentDateTime())
        return total

    def _update_timer_display(self):
        total = self._get_total_seconds()
        hours = total // 3600
        minutes = (total % 3600) // 60
        seconds = total % 60
        self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def set_elapsed_time(self, seconds):
        self.accumulated_seconds = seconds
        self._update_timer_display()

    def resume_timing(self, accumulated_seconds, session_start_str=None):
        self.accumulated_seconds = accumulated_seconds

        if session_start_str:
            from datetime import datetime
            try:
                start = datetime.strptime(session_start_str, "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                session_secs = int((now - start).total_seconds())
                self.session_start_time = QDateTime.currentDateTime().addSecs(-session_secs)
                self.is_timing = True
                self.start_btn.setText("暂停")
                self.start_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {C.SLATE_600};
                        color: {C.WHITE};
                        border: none;
                        border-radius: {R.MD};
                        font-weight: 600;
                        font-size: 12px;
                    }}
                """)
                self.complete_btn.setEnabled(True)
                self.timer.start(1000)
            except (ValueError, TypeError):
                pass
        elif accumulated_seconds > 0:
            self.start_btn.setText("继续")
            self.complete_btn.setEnabled(True)

    def show_completion_summary(self, planned_minutes, actual_seconds):
        """Show completion summary"""
        actual_minutes = round(actual_seconds / 60, 1)
        diff = planned_minutes - actual_minutes

        if diff > 0:
            result = f"提前 {diff:.0f} 分钟完成 🎉"
            color = C.SUCCESS
        elif diff < 0:
            result = f"超时 {abs(diff):.0f} 分钟"
            color = C.DANGER
        else:
            result = "准时完成"
            color = C.INFO

        self.timer_label.setText(result)
        self.timer_label.setStyleSheet(f"""
            color: {color};
            background: transparent;
            border: none;
            font-size: 11px;
            padding: 4px;
        """)
        self.start_btn.setEnabled(False)
        self.complete_btn.setEnabled(False)
        self.complete_btn.setText("已完成")

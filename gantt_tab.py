"""
甘特图标签页 - 按看板展示事项时间线
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime, timedelta


# ==================== 甘特图绘制组件 ====================

class GanttChartWidget(QWidget):
    """甘特图绘制区域 - 使用 QPainter 自定义绘制"""

    event_edit_requested = pyqtSignal(int)

    # 颜色配置
    STATUS_COLORS = {
        "pending": QColor("#bdc3c7"),
        "in_progress": QColor("#3498db"),
        "completed": QColor("#27ae60"),
    }

    BG_COLOR = QColor("#f5f6fa")
    GRID_COLOR = QColor("#e8e8e8")
    HEADER_BG = QColor("#ffffff")
    TEXT_COLOR = QColor("#2c3e50")
    DEADLINE_COLOR = QColor("#e74c3c")

    LEFT_COL_WIDTH = 200
    ROW_HEIGHT = 40
    DAY_WIDTH = 40
    HEADER_HEIGHT = 50

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.events = []
        self.start_date = None
        self.end_date = None
        self.deadline = None
        self.total_days = 0
        self._event_rects = []  # 存储事件条的矩形区域，用于点击检测
        self.setMinimumHeight(400)

    def set_data(self, events, deadline=None):
        """设置要绘制的数据"""
        self.events = events
        self.deadline = deadline
        self._calculate_date_range()
        self._event_rects.clear()
        self.update()
        # 调整大小
        total_width = self.LEFT_COL_WIDTH + self.total_days * self.DAY_WIDTH + 20
        total_height = self.HEADER_HEIGHT + len(self.events) * self.ROW_HEIGHT + 20
        self.setMinimumSize(total_width, max(total_height, 400))
        self.resize(total_width, max(total_height, 400))

    def _calculate_date_range(self):
        """计算日期范围"""
        if not self.events:
            self.start_date = datetime.now().date()
            self.end_date = self.start_date + timedelta(days=7)
            self.total_days = 7
            return

        min_date = None
        max_date = None

        for event in self.events:
            planned_start = event.get('planned_start', '')
            duration_min = event.get('planned_duration_minutes', 30)
            if planned_start:
                try:
                    dt = datetime.strptime(planned_start, "%Y-%m-%d %H:%M")
                    event_date = dt.date()
                    if min_date is None or event_date < min_date:
                        min_date = event_date
                    # 按8小时工作日折算结束日期
                    work_days = duration_min / 480.0
                    end_d = event_date + timedelta(days=max(int(work_days), 1))
                    if max_date is None or end_d > max_date:
                        max_date = end_d
                except (ValueError, TypeError):
                    pass

        if min_date is None:
            min_date = datetime.now().date()
        if max_date is None:
            max_date = min_date + timedelta(days=1)

        # 前后各留2天余量
        self.start_date = min_date - timedelta(days=2)
        self.end_date = max_date + timedelta(days=2)
        self.total_days = (self.end_date - self.start_date).days + 1

    def _day_to_x(self, date):
        """将日期转换为 x 坐标"""
        delta = (date - self.start_date).days
        return self.LEFT_COL_WIDTH + delta * self.DAY_WIDTH

    def paintEvent(self, event):
        if not self.events:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillRect(self.rect(), self.BG_COLOR)
            painter.setPen(QPen(self.TEXT_COLOR))
            painter.setFont(QFont("Microsoft YaHei", 12))
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无事项数据")
            painter.end()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.BG_COLOR)

        # 绘制左侧标题列背景
        left_rect = QRectF(0, 0, self.LEFT_COL_WIDTH, self.height())
        painter.fillRect(left_rect, QColor("#ffffff"))

        # 绘制左侧标题列分隔线
        painter.setPen(QPen(self.GRID_COLOR, 1))
        painter.drawLine(self.LEFT_COL_WIDTH, 0, self.LEFT_COL_WIDTH, self.height())

        # 绘制顶部日期刻度
        self._draw_header(painter)

        # 绘制网格线
        self._draw_grid(painter)

        # 绘制 deadline 竖虚线
        if self.deadline:
            self._draw_deadline(painter)

        # 绘制事件条
        self._draw_events(painter)

        painter.end()

    def _draw_header(self, painter):
        """绘制顶部日期刻度"""
        # 顶部背景
        header_rect = QRectF(0, 0, self.width(), self.HEADER_HEIGHT)
        painter.fillRect(header_rect, self.HEADER_BG)
        painter.setPen(QPen(self.GRID_COLOR, 1))
        painter.drawLine(0, self.HEADER_HEIGHT, self.width(), self.HEADER_HEIGHT)

        # 左上角标题
        painter.setPen(QPen(self.TEXT_COLOR))
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        painter.drawText(QRectF(4, 0, self.LEFT_COL_WIDTH - 8, self.HEADER_HEIGHT),
                         Qt.AlignVCenter | Qt.AlignLeft, "事项")

        # 日期刻度
        current_month = None
        month_start_x = None
        for i in range(self.total_days):
            date = self.start_date + timedelta(days=i)
            x = self.LEFT_COL_WIDTH + i * self.DAY_WIDTH

            # 每天画竖线
            painter.setPen(QPen(self.GRID_COLOR, 1))
            painter.drawLine(x, 0, x, self.HEADER_HEIGHT)

            # 月份标注
            if current_month != date.month:
                if current_month is not None and month_start_x is not None:
                    # 绘制上个月份标签
                    painter.setPen(QPen(self.TEXT_COLOR))
                    painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
                    month_width = x - month_start_x
                    month_rect = QRectF(month_start_x, 2, month_width, 20)
                    painter.drawText(month_rect, Qt.AlignCenter,
                                     f"{date.year}/{date.month - 1 if date.month > 1 else 12}")
                current_month = date.month
                month_start_x = x

            # 日期数字
            painter.setPen(QPen(QColor("#7f8c8d")))
            painter.setFont(QFont("Microsoft YaHei", 8))
            day_rect = QRectF(x, 22, self.DAY_WIDTH, 26)
            painter.drawText(day_rect, Qt.AlignCenter, str(date.day))

        # 绘制最后一个月份标签
        if current_month is not None and month_start_x is not None:
            painter.setPen(QPen(self.TEXT_COLOR))
            painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
            last_x = self.LEFT_COL_WIDTH + self.total_days * self.DAY_WIDTH
            month_width = last_x - month_start_x
            if month_width > 0:
                month_rect = QRectF(month_start_x, 2, month_width, 20)
                last_date = self.start_date + timedelta(days=self.total_days - 1)
                painter.drawText(month_rect, Qt.AlignCenter,
                                 f"{last_date.year}/{last_date.month}")

    def _draw_grid(self, painter):
        """绘制网格线"""
        painter.setPen(QPen(self.GRID_COLOR, 1))

        # 竖线（每天）
        for i in range(self.total_days + 1):
            x = self.LEFT_COL_WIDTH + i * self.DAY_WIDTH
            painter.drawLine(x, self.HEADER_HEIGHT, x,
                             self.HEADER_HEIGHT + len(self.events) * self.ROW_HEIGHT)

        # 横线（每行）
        for i in range(len(self.events) + 1):
            y = self.HEADER_HEIGHT + i * self.ROW_HEIGHT
            painter.drawLine(self.LEFT_COL_WIDTH, y,
                             self.LEFT_COL_WIDTH + self.total_days * self.DAY_WIDTH, y)

        # 周末背景色
        for i in range(self.total_days):
            date = self.start_date + timedelta(days=i)
            if date.weekday() >= 5:  # 周六、周日
                x = self.LEFT_COL_WIDTH + i * self.DAY_WIDTH
                weekend_rect = QRectF(x, self.HEADER_HEIGHT, self.DAY_WIDTH,
                                      len(self.events) * self.ROW_HEIGHT)
                painter.fillRect(weekend_rect, QColor("#f0f0f5"))

    def _draw_deadline(self, painter):
        """绘制截止日期红色竖虚线"""
        try:
            if isinstance(self.deadline, str) and self.deadline:
                parts = self.deadline.split('-')
                deadline_date = datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
            else:
                return
        except (ValueError, TypeError, IndexError):
            return

        x = self._day_to_x(deadline_date)
        if x < self.LEFT_COL_WIDTH or x > self.LEFT_COL_WIDTH + self.total_days * self.DAY_WIDTH:
            return

        pen = QPen(self.DEADLINE_COLOR, 2, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(x, self.HEADER_HEIGHT, x,
                         self.HEADER_HEIGHT + len(self.events) * self.ROW_HEIGHT)

        # 标签
        painter.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
        painter.setPen(QPen(self.DEADLINE_COLOR))
        label_rect = QRectF(x - 30, self.HEADER_HEIGHT - 2, 60, 14)
        painter.drawText(label_rect, Qt.AlignCenter, "截止日期")

    def _draw_events(self, painter):
        """绘制事件条"""
        self._event_rects.clear()

        for i, event in enumerate(self.events):
            y = self.HEADER_HEIGHT + i * self.ROW_HEIGHT

            # 左侧事件标题
            title = event.get('title', '未命名')
            painter.setPen(QPen(self.TEXT_COLOR))
            painter.setFont(QFont("Microsoft YaHei", 9))
            title_rect = QRectF(4, y, self.LEFT_COL_WIDTH - 8, self.ROW_HEIGHT)
            painter.drawText(title_rect, Qt.AlignVCenter | Qt.AlignLeft,
                             self._truncate_text(painter, title, self.LEFT_COL_WIDTH - 16))

            # 计算事件条的 x 和宽度
            planned_start = event.get('planned_start', '')
            duration_min = event.get('planned_duration_minutes', 30)

            if not planned_start:
                continue

            try:
                dt = datetime.strptime(planned_start, "%Y-%m-%d %H:%M")
                event_start_date = dt.date()
                event_end_dt = dt + timedelta(minutes=duration_min)
                event_end_date = event_end_dt.date()
                if event_end_dt.time() > datetime.min.time():
                    # 如果结束时间不是午夜，则结束日期就是当天
                    pass
                else:
                    event_end_date -= timedelta(days=1)
            except (ValueError, TypeError):
                continue

            bar_x = self._day_to_x(event_start_date)
            # 按8小时工作日折算：480分钟=1天
            bar_days = max(duration_min / 480.0, 0.5)
            bar_width = bar_days * self.DAY_WIDTH - 4  # 留2px间距

            bar_y = y + 6
            bar_height = self.ROW_HEIGHT - 12

            # 状态颜色
            status = event.get('status', 'pending')
            color = self.STATUS_COLORS.get(status, self.STATUS_COLORS['pending'])

            # 绘制事件条（圆角）
            bar_rect = QRectF(bar_x + 2, bar_y, bar_width, bar_height)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(bar_rect, 4, 4)

            # 事件条上的标题
            if bar_width > 20:
                painter.setPen(QPen(QColor("#ffffff")))
                painter.setFont(QFont("Microsoft YaHei", 8))
                text_rect = QRectF(bar_x + 6, bar_y, bar_width - 8, bar_height)
                painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft,
                                 self._truncate_text(painter, title, bar_width - 12))

            # 存储矩形区域用于点击检测
            self._event_rects.append((bar_rect, event['id']))

    def _truncate_text(self, painter, text, max_width):
        """截断文本以适应宽度"""
        if painter.fontMetrics().horizontalAdvance(text) <= max_width:
            return text
        truncated = text
        while len(truncated) > 1 and painter.fontMetrics().horizontalAdvance(truncated + "...") > max_width:
            truncated = truncated[:-1]
        return truncated + "..."

    def mouseDoubleClickEvent(self, event):
        """双击事件条发射编辑信号"""
        pos = event.pos()
        for rect, event_id in self._event_rects:
            if rect.contains(QPointF(pos)):
                self.event_edit_requested.emit(event_id)
                return
        super().mouseDoubleClickEvent(event)


# ==================== 甘特图标签页 ====================

class GanttTab(QWidget):
    """甘特图标签页"""

    event_edit_requested = pyqtSignal(int)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_board_id = None

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(16, 12, 16, 12)
        toolbar.setSpacing(12)

        # 看板筛选下拉框
        board_label = QLabel("看板：")
        board_label.setFont(QFont("Microsoft YaHei", 11))
        board_label.setStyleSheet("color: #2c3e50; background: transparent; border: none;")
        toolbar.addWidget(board_label)

        self.board_combo = QComboBox()
        self.board_combo.setFont(QFont("Microsoft YaHei", 10))
        self.board_combo.setFixedHeight(32)
        self.board_combo.setMinimumWidth(160)
        self.board_combo.currentIndexChanged.connect(self._on_board_changed)
        toolbar.addWidget(self.board_combo)

        toolbar.addStretch()

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setFont(QFont("Microsoft YaHei", 11))
        refresh_btn.setFixedHeight(32)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        main_layout.addLayout(toolbar)

        # 甘特图滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f5f6fa;
            }
            QScrollBar:horizontal {
                height: 8px;
                background: transparent;
            }
            QScrollBar::handle:horizontal {
                background: #cccccc;
                border-radius: 4px;
                min-width: 30px;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #cccccc;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                width: 0px;
                height: 0px;
            }
        """)

        self.gantt_chart = GanttChartWidget(self.db)
        self.gantt_chart.event_edit_requested.connect(self.event_edit_requested.emit)
        self.scroll_area.setWidget(self.gantt_chart)
        main_layout.addWidget(self.scroll_area, 1)

        # 样式
        self.setStyleSheet("""
            GanttTab {
                background-color: #f5f6fa;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                padding: 0 12px;
                color: #2c3e50;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QPushButton {
                background-color: #ffffff;
                color: #2c3e50;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                padding: 6px 16px;
                font-family: "Microsoft YaHei";
            }
            QPushButton:hover {
                background-color: #f0f4f8;
                border-color: #3498db;
                color: #3498db;
            }
        """)

    def load_boards(self):
        """加载看板列表到下拉框"""
        self.board_combo.blockSignals(True)
        self.board_combo.clear()
        boards = self.db.get_boards()
        for board in boards:
            self.board_combo.addItem(board['name'], board['id'])
        self.board_combo.blockSignals(False)

        # 默认选中第一个
        if self.board_combo.count() > 0:
            self.board_combo.setCurrentIndex(0)
            self._on_board_changed(0)

    def _on_board_changed(self, index):
        """看板切换"""
        if index < 0:
            return
        board_id = self.board_combo.currentData()
        if board_id:
            self.current_board_id = board_id
            self.refresh()

    def refresh(self):
        """刷新甘特图数据"""
        if self.current_board_id is None:
            return

        # 获取看板的所有事件
        events = self.db.get_all_events(board_id=self.current_board_id)

        # 获取看板的 deadline
        board = self.db.get_board(self.current_board_id)
        deadline = board.get('deadline', '') if board else None

        self.gantt_chart.set_data(events, deadline)

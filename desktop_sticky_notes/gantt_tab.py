"""
甘特图标签页 - 按看板展示事项时间线
支持：今天指示线、计划/实际双条、拖拽调整开始日期、双击编辑
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime, timedelta

DAY_MINUTES = 480  # 按8小时工作日折算：480分钟=1天


# ==================== 甘特图绘制组件 ====================

class GanttChartWidget(QWidget):
    """甘特图绘制区域 - 使用 QPainter 自定义绘制"""

    event_edit_requested = pyqtSignal(int)
    event_rescheduled = pyqtSignal(int, str)  # (event_id, new_planned_start)

    # 颜色配置：计划=灰、实际=琥珀（与工具栏图例一致）
    PLANNED_COLOR = QColor("#94A3B8")
    ACTUAL_COLOR = QColor("#F59E0B")

    BG_COLOR = QColor("#F8FAFC")
    GRID_COLOR = QColor("#E2E8F0")
    HEADER_BG = QColor("#FFFFFF")
    TEXT_COLOR = QColor("#1E293B")
    DEADLINE_COLOR = QColor("#DC2626")
    TODAY_COLOR = QColor("#F59E0B")

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
        self._deadline_in_range = False
        self._out_of_range_count = 0
        self._event_rects = []  # (planned_rect, actual_rect, event_id)
        self._actuals = {}      # event_id -> {'start': date|None, 'minutes': float}
        self._drag = None       # {'id', 'press_x', 'orig_start': datetime, 'dx'}
        self._hover_bar = False
        # 缩放：Ctrl+滚轮调整每天像素宽度
        self.DAY_WIDTH = 40
        self._min_day_width = 12
        self._max_day_width = 80
        self.setMouseTracking(True)
        self.setMinimumHeight(400)

    def set_data(self, events, deadline=None):
        """设置要绘制的数据"""
        self.events = events
        self.deadline = deadline
        self._calculate_date_range()
        self._event_rects.clear()
        self._collect_actuals(events)
        self._drag = None
        self.update()
        # 调整大小
        total_width = self.LEFT_COL_WIDTH + self.total_days * self.DAY_WIDTH + 20
        total_height = self.HEADER_HEIGHT + len(self.events) * self.ROW_HEIGHT + 20
        self.setMinimumSize(total_width, max(total_height, 400))
        self.resize(total_width, max(total_height, 400))

    def _collect_actuals(self, events):
        """收集每个事项的实际投入（批量查询，用于绘制实际条）"""
        ids = [e['id'] for e in events]
        elapsed_map = self.db.get_elapsed_seconds_map(ids) if ids else {}
        self._actuals = {}
        for e in events:
            minutes = elapsed_map.get(e['id'], 0) / 60.0
            # 实际条起点：优先实际开始时间，否则跟随计划开始
            actual_start_date = None
            actual_start_at = e.get('actual_start_at') or ''
            if actual_start_at:
                try:
                    actual_start_date = datetime.strptime(
                        actual_start_at[:10], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    actual_start_date = None
            self._actuals[e['id']] = {'start': actual_start_date, 'minutes': minutes}

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
                    work_days = duration_min / float(DAY_MINUTES)
                    end_d = event_date + timedelta(days=max(int(work_days), 1))
                    if max_date is None or end_d > max_date:
                        max_date = end_d
                except (ValueError, TypeError):
                    pass

        # 实际开始时间也纳入范围
        for info in self._actuals.values():
            if info['start']:
                if min_date is None or info['start'] < min_date:
                    min_date = info['start']
                end_d = info['start'] + timedelta(days=max(int(info['minutes'] / DAY_MINUTES), 1))
                if max_date is None or end_d > max_date:
                    max_date = end_d

        if min_date is None:
            min_date = datetime.now().date()
        if max_date is None:
            max_date = min_date + timedelta(days=1)

        # 离群保护：范围最多 180 天。个别日期异常（如误选年份）的事项
        # 不无限拉伸时间轴，改为在图表边缘以文字提示数量
        self._out_of_range_count = 0
        if (max_date - min_date).days > 180:
            clamped_max = min_date + timedelta(days=180)
            for event in self.events:
                ps = event.get('planned_start', '')
                if ps:
                    try:
                        d = datetime.strptime(ps, "%Y-%m-%d %H:%M").date()
                        if d > clamped_max:
                            self._out_of_range_count += 1
                    except (ValueError, TypeError):
                        pass
            max_date = clamped_max

        # 将看板 deadline 纳入日期范围：
        # 仅当距离事件区间 14 天以内时才扩展范围，避免远期截止日把图表拉得过宽、
        # 近期任务挤成小点；过远的截止日在图表边缘以文字提示
        self._deadline_in_range = False
        if self.deadline:
            try:
                dl = datetime.strptime(self.deadline, "%Y-%m-%d").date()
                if dl > max_date:
                    if (dl - max_date).days <= 14:
                        max_date = dl
                        self._deadline_in_range = True
                else:
                    # 在区间内（含已过期的截止线）
                    self._deadline_in_range = True
                    if dl < min_date:
                        min_date = dl
            except (ValueError, TypeError):
                pass

        # 将"今天"纳入范围（30 天以内时），保证今天指示线始终可见
        today = datetime.now().date()
        if today < min_date and (min_date - today).days <= 30:
            min_date = today
        elif today > max_date and (today - max_date).days <= 30:
            max_date = today

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
            painter.drawText(self.rect(), Qt.AlignCenter, "该看板暂无可展示的事项")
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

        # 绘制今天指示线
        self._draw_today_line(painter)

        # 绘制 deadline 竖虚线（在范围内时）
        if self.deadline:
            self._draw_deadline(painter)
            # 截止日远在范围之外时，在右上角给出提示
            deadline_date = self._deadline_as_date()
            if deadline_date and not self._deadline_in_range and deadline_date > self.end_date:
                painter.setPen(QPen(self.DEADLINE_COLOR))
                painter.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
                painter.drawText(QRectF(self.width() - 180, 2, 175, 20),
                                 Qt.AlignRight | Qt.AlignVCenter,
                                 f"截止 {deadline_date.strftime('%Y/%m/%d')} →")

        # 有离群事项（日期超出 180 天范围）时给出提示
        if self._out_of_range_count:
            painter.setPen(QPen(self.TEXT_COLOR))
            painter.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
            painter.drawText(QRectF(self.width() - 220, 20, 215, 16),
                             Qt.AlignRight | Qt.AlignVCenter,
                             f"另有 {self._out_of_range_count} 个事项在范围外 →")

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
        today = datetime.now().date()
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

            # 今天高亮
            if date == today:
                painter.fillRect(QRectF(x, 22, self.DAY_WIDTH, 28),
                                 QColor(245, 158, 11, 40))

            # 日期数字
            painter.setPen(QPen(QColor("#78716C") if date != today else QColor("#D97706")))
            painter.setFont(QFont("Microsoft YaHei", 8, QFont.Bold if date == today else QFont.Normal))
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

    def _draw_today_line(self, painter):
        """绘制今天竖线（琥珀色实线）"""
        today = datetime.now().date()
        if not (self.start_date <= today <= self.end_date):
            return
        x = self._day_to_x(today) + self.DAY_WIDTH // 2
        painter.setPen(QPen(self.TODAY_COLOR, 2))
        painter.drawLine(x, self.HEADER_HEIGHT, x, self.height())

        # 标签
        painter.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
        painter.setPen(QPen(self.TODAY_COLOR))
        painter.drawText(QRectF(x - 30, self.HEADER_HEIGHT - 2, 60, 14),
                         Qt.AlignCenter, "今天")

    def _deadline_as_date(self):
        """解析截止日期字符串为 date，失败返回 None"""
        if isinstance(self.deadline, str) and self.deadline:
            try:
                parts = self.deadline.split('-')
                return datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
            except (ValueError, TypeError, IndexError):
                return None
        return None

    def _draw_deadline(self, painter):
        """绘制截止日期红色竖虚线"""
        deadline_date = self._deadline_as_date()
        if deadline_date is None or not self._deadline_in_range:
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
        """绘制事件条：上半为计划条（浅色），下半为实际投入条（实色）"""
        self._event_rects.clear()
        drag_dx = 0
        if self._drag:
            drag_dx = self._drag['dx']

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
            except (ValueError, TypeError):
                continue

            status = event.get('status', 'pending')
            dragging = self._drag is not None and self._drag['id'] == event['id']

            # ---- 计划条（灰色，上半）----
            bar_x = self._day_to_x(event_start_date)
            bar_days = max(duration_min / float(DAY_MINUTES), 0.25)
            bar_width = bar_days * self.DAY_WIDTH - 4

            bar_y = y + 5
            bar_height = 12

            planned_fill = QColor(self.PLANNED_COLOR)
            planned_fill.setAlpha(120)
            planned_rect = QRectF(bar_x + 2 + drag_dx, bar_y, max(bar_width, 6), bar_height)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(planned_fill))
            painter.drawRoundedRect(planned_rect, 3, 3)

            # 计划条边框 + 拖拽中的新日期提示
            painter.setPen(QPen(self.PLANNED_COLOR, 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(planned_rect, 3, 3)
            if dragging and drag_dx:
                days_shift = round(drag_dx / self.DAY_WIDTH)
                new_date = event_start_date + timedelta(days=days_shift)
                painter.setPen(QPen(self.TODAY_COLOR))
                painter.setFont(QFont("Microsoft YaHei", 8, QFont.Bold))
                painter.drawText(
                    QRectF(planned_rect.right() + 6, bar_y - 2, 70, bar_height + 4),
                    Qt.AlignVCenter | Qt.AlignLeft, new_date.strftime("MM/dd"))

            # ---- 实际条（琥珀实色，下半）----
            info = self._actuals.get(event['id'], {})
            actual_rect = None
            if info.get('minutes', 0) > 0:
                actual_start_date = info.get('start') or event_start_date
                actual_days = max(info['minutes'] / float(DAY_MINUTES), 0.1)
                actual_width = actual_days * self.DAY_WIDTH - 4
                actual_x = self._day_to_x(actual_start_date)
                actual_y = y + self.ROW_HEIGHT - 17
                actual_rect = QRectF(actual_x + 2, actual_y,
                                     max(actual_width, 4), 12)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(self.ACTUAL_COLOR))
                painter.drawRoundedRect(actual_rect, 3, 3)

            # 存储矩形区域用于点击/拖拽检测
            self._event_rects.append((planned_rect, actual_rect, event['id']))

    def _truncate_text(self, painter, text, max_width):
        """截断文本以适应宽度"""
        if painter.fontMetrics().horizontalAdvance(text) <= max_width:
            return text
        truncated = text
        while len(truncated) > 1 and painter.fontMetrics().horizontalAdvance(truncated + "...") > max_width:
            truncated = truncated[:-1]
        return truncated + "..."

    # ==================== 鼠标交互：悬停 / 拖拽改期 / 双击编辑 ====================

    def _hit_test(self, pos):
        """返回命中的 (event_id, rect)，未命中返回 (None, None)"""
        for planned_rect, actual_rect, event_id in self._event_rects:
            if planned_rect.contains(QPointF(pos)) or \
                    (actual_rect and actual_rect.contains(QPointF(pos))):
                return event_id, planned_rect
        return None, None

    def mouseMoveEvent(self, event):
        pos = event.pos()
        if self._drag:
            # 拖拽中：限制在图表范围内
            dx = pos.x() - self._drag['press_x']
            min_dx = (self._day_to_x(self.start_date)
                      - self._day_to_x(self._drag['orig_start'].date()))
            max_dx = (self._day_to_x(self.end_date)
                      - self._day_to_x(self._drag['orig_start'].date()))
            self._drag['dx'] = max(min_dx, min(dx, max_dx))
            self.update()
            event.accept()
            return

        event_id, _ = self._hit_test(pos)
        self._hover_bar = event_id is not None
        self.setCursor(QCursor(Qt.SizeHorCursor) if self._hover_bar
                       else QCursor(Qt.ArrowCursor))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """按住计划条开始拖拽改期"""
        if event.button() == Qt.LeftButton:
            event_id, _ = self._hit_test(event.pos())
            if event_id is not None:
                event_data = next((e for e in self.events if e['id'] == event_id), None)
                if event_data and event_data.get('planned_start'):
                    try:
                        orig = datetime.strptime(event_data['planned_start'],
                                                 "%Y-%m-%d %H:%M")
                        self._drag = {'id': event_id, 'press_x': event.pos().x(),
                                      'orig_start': orig, 'dx': 0}
                        event.accept()
                        return
                    except (ValueError, TypeError):
                        pass
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """松手：按天取整应用改期；无位移则视为普通点击"""
        if self._drag and event.button() == Qt.LeftButton:
            days = round(self._drag['dx'] / self.DAY_WIDTH)
            event_id = self._drag['id']
            orig = self._drag['orig_start']
            self._drag = None
            self.update()

            if days != 0:
                new_start = orig + timedelta(days=days)
                new_str = new_start.strftime("%Y-%m-%d %H:%M")
                self.db.update_event(event_id, planned_start=new_str)
                # 重绘并通知外部
                self.set_data(self.db.get_all_events(
                    board_id=self._current_board_id()), self.deadline)
                self.event_rescheduled.emit(event_id, new_str)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _current_board_id(self):
        parent = self.parent()
        while parent is not None and not hasattr(parent, 'current_board_id'):
            parent = parent.parent()
        return parent.current_board_id if parent else None

    def mouseDoubleClickEvent(self, event):
        """双击事件条发射编辑信号"""
        event_id, _ = self._hit_test(event.pos())
        if event_id is not None:
            self.event_edit_requested.emit(event_id)
            return
        super().mouseDoubleClickEvent(event)

    # ==================== 缩放 ====================

    def wheelEvent(self, event):
        """Ctrl+滚轮缩放时间轴（每天像素宽度 12~80）"""
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._set_day_width(min(self.DAY_WIDTH + 8, self._max_day_width))
            else:
                self._set_day_width(max(self.DAY_WIDTH - 8, self._min_day_width))
            event.accept()
        else:
            super().wheelEvent(event)

    def _set_day_width(self, value):
        if value == self.DAY_WIDTH:
            return
        self.DAY_WIDTH = value
        # 按新刻度重算画布尺寸
        total_width = self.LEFT_COL_WIDTH + self.total_days * self.DAY_WIDTH + 20
        total_height = self.HEADER_HEIGHT + len(self.events) * self.ROW_HEIGHT + 20
        self.setMinimumSize(total_width, max(total_height, 400))
        self.resize(total_width, max(total_height, 400))
        self.update()


# ==================== 甘特图标签页 ====================

class GanttTab(QWidget):
    """甘特图标签页"""

    event_edit_requested = pyqtSignal(int)
    event_rescheduled = pyqtSignal(int, str)

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
        toolbar.setContentsMargins(16, 10, 16, 10)
        toolbar.setSpacing(12)

        # 看板筛选下拉框
        board_label = QLabel("看板：")
        board_label.setFont(QFont("Microsoft YaHei", 11))
        board_label.setStyleSheet("color: #475569; background: transparent; border: none;")
        toolbar.addWidget(board_label)

        self.board_combo = QComboBox()
        self.board_combo.setFont(QFont("Microsoft YaHei", 10))
        self.board_combo.setFixedHeight(32)
        self.board_combo.setMinimumWidth(160)
        self.board_combo.currentIndexChanged.connect(self._on_board_changed)
        toolbar.addWidget(self.board_combo)

        toolbar.addStretch()

        # 图例：计划 / 实际 / 今天
        legend = QHBoxLayout()
        legend.setSpacing(6)
        for color, label in [("#94A3B8", "计划"), ("#F59E0B", "实际投入")]:
            chip = QFrame()
            chip.setFixedSize(18, 10)
            chip.setStyleSheet(
                f"background-color: {color}; border-radius: 3px; border: none;")
            legend.addWidget(chip)
            text = QLabel(label)
            text.setFont(QFont("Microsoft YaHei", 9))
            text.setStyleSheet("color: #475569; background: transparent; border: none;")
            legend.addWidget(text)
        toolbar.addLayout(legend)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setFont(QFont("Microsoft YaHei", 11))
        refresh_btn.setFixedHeight(32)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        main_layout.addLayout(toolbar)

        # 操作提示
        hint = QLabel("拖动计划条可按天调整开始日期 · 双击编辑 · 灰条=计划 / 琥珀条=实际 · Ctrl+滚轮缩放时间轴")
        hint.setFont(QFont("Microsoft YaHei", 9))
        hint.setStyleSheet("color: #A8A29E; background: transparent; border: none; padding: 0 16px 6px 16px;")
        main_layout.addWidget(hint)

        # 甘特图滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F8FAFC;
            }
            QScrollBar:horizontal {
                height: 8px;
                background: transparent;
            }
            QScrollBar::handle:horizontal {
                background: #CBD5E1;
                border-radius: 4px;
                min-width: 30px;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
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
        self.gantt_chart.event_rescheduled.connect(self.event_rescheduled.emit)
        self.scroll_area.setWidget(self.gantt_chart)
        main_layout.addWidget(self.scroll_area, 1)

        # 样式
        self.setStyleSheet("""
            GanttTab {
                background-color: #F8FAFC;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #E7E5E4;
                border-radius: 6px;
                padding: 0 12px;
                color: #1C1917;
            }
            QComboBox:focus {
                border-color: #F59E0B;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QPushButton {
                background-color: #ffffff;
                color: #475569;
                border: 1px solid #E7E5E4;
                border-radius: 6px;
                padding: 6px 16px;
                font-family: "Microsoft YaHei";
            }
            QPushButton:hover {
                background-color: #FEF3C7;
                border-color: #F59E0B;
                color: #92400E;
            }
        """)

    def load_boards(self):
        """加载看板列表到下拉框（已结项看板带标注，供回看）"""
        self.board_combo.blockSignals(True)
        self.board_combo.clear()
        boards = self.db.get_boards()
        for board in boards:
            label = board['name'] + ("（已结项）" if board.get('closed_at') else "")
            self.board_combo.addItem(label, board['id'])
        self.board_combo.blockSignals(False)

        # 保持当前选择，若无选择则默认第一个
        if self.current_board_id is not None:
            for i in range(self.board_combo.count()):
                if self.board_combo.itemData(i) == self.current_board_id:
                    self.board_combo.setCurrentIndex(i)
                    break
        elif self.board_combo.count() > 0:
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

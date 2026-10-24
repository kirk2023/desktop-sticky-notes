"""
今日标签页 - 聚合当天关注事项的仪表盘
包含：统计概览（今日计划/进行中/已逾期/今日投入）、
     已逾期、今日计划、计时中、即将到期看板 四个分区
"""

from datetime import datetime, timedelta

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QLabel, QFrame, QPushButton, QProgressBar,
                             QSizePolicy, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, QDateTime, pyqtSignal
from PyQt5.QtGui import QFont, QColor

BG = "#F5F5F0"
CARD_BG = "#FFFFFF"
BORDER = "#E7E5E4"
TEXT_PRIMARY = "#1C1917"
TEXT_SECONDARY = "#57534E"
TEXT_TERTIARY = "#78716C"
TEXT_DISABLED = "#A8A29E"
AMBER = "#F59E0B"
AMBER_DARK = "#D97706"
AMBER_LIGHT = "#FEF3C7"
DANGER = "#DC2626"
DANGER_LIGHT = "#FEE2E2"
SUCCESS = "#059669"
SUCCESS_LIGHT = "#D1FAE5"
INFO = "#2563EB"


def _fmt_elapsed(seconds):
    """秒数格式化为 Xh Ym / Ym"""
    minutes = int(seconds // 60)
    if minutes >= 60:
        return f"{minutes // 60}h{minutes % 60}m"
    return f"{minutes}m"


def _fmt_duration(minutes):
    """计划分钟数格式化"""
    if minutes >= 60 and minutes % 60 == 0:
        return f"{minutes // 60}小时"
    if minutes >= 60:
        return f"{minutes / 60:.1f}小时"
    return f"{minutes}分钟"


class StatCard(QFrame):
    """统计概览卡片"""

    def __init__(self, title, accent, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFixedHeight(84)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)

        self.value_label = QLabel("0")
        self.value_label.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {accent}; background: transparent; border: none;")
        layout.addWidget(self.value_label)

        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Microsoft YaHei", 10))
        self.title_label.setStyleSheet(
            f"color: {TEXT_TERTIARY}; background: transparent; border: none;")
        layout.addWidget(self.title_label)

    def set_value(self, value):
        self.value_label.setText(str(value))


class EventRow(QFrame):
    """今日事项行"""

    edit_requested = pyqtSignal(int)
    start_requested = pyqtSignal(int)
    stop_requested = pyqtSignal(int)
    complete_requested = pyqtSignal(int)
    pin_requested = pyqtSignal(int)

    def __init__(self, event, elapsed_seconds=0, has_active_session=False,
                 overdue=False, parent=None):
        super().__init__(parent)
        self.event_id = event['id']
        self.setObjectName("eventRow")
        self.setStyleSheet(f"""
            #eventRow {{
                background-color: {DANGER_LIGHT if overdue else CARD_BG};
                border: 1px solid {'#FECACA' if overdue else BORDER};
                border-radius: 8px;
            }}
            #eventRow:hover {{
                border-color: {AMBER};
            }}
        """)
        self.setFixedHeight(46)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 6, 12, 6)
        row.setSpacing(8)

        # 颜色圆点
        dot = QFrame()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(
            f"background-color: {event.get('color', AMBER_LIGHT)}; "
            "border-radius: 5px; border: none;")
        row.addWidget(dot)

        # 标题（点击编辑）
        title_btn = QPushButton(event.get('title', '未命名'))
        title_btn.setCursor(Qt.PointingHandCursor)
        title_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        title_btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_PRIMARY}; background: transparent; border: none;
                padding: 0; text-align: left; font-weight: bold;
            }}
            QPushButton:hover {{ color: {AMBER_DARK}; }}
        """)
        title_btn.setToolTip("点击编辑事项")
        title_btn.clicked.connect(lambda: self.edit_requested.emit(self.event_id))
        row.addWidget(title_btn, 1)

        # 计划时间
        planned = event.get('planned_start', '')
        if planned:
            try:
                dt = QDateTime.fromString(planned, "yyyy-MM-dd HH:mm")
                time_text = dt.toString("MM/dd HH:mm")
            except Exception:
                time_text = planned[:16]
        else:
            time_text = "未排期"
        time_label = QLabel(f"🕒 {time_text}")
        time_label.setFont(QFont("Microsoft YaHei", 9))
        time_label.setStyleSheet(f"color: {TEXT_TERTIARY}; background: transparent; border: none;")
        row.addWidget(time_label)

        # 已投入
        if elapsed_seconds > 0:
            elapsed_label = QLabel(f"已用 {_fmt_elapsed(elapsed_seconds)}")
            elapsed_label.setFont(QFont("Microsoft YaHei", 9))
            elapsed_label.setStyleSheet(
                f"color: {SUCCESS}; background: transparent; border: none;")
            row.addWidget(elapsed_label)

        # 操作按钮
        status = event.get('status', 'pending')
        if status == 'in_progress':
            if has_active_session:
                stop_btn = self._make_btn("⏸ 暂停", AMBER_DARK, AMBER_LIGHT)
                stop_btn.clicked.connect(lambda: self.stop_requested.emit(self.event_id))
                row.addWidget(stop_btn)
            else:
                start_btn = self._make_btn("▶ 继续", SUCCESS, SUCCESS_LIGHT)
                start_btn.clicked.connect(lambda: self.start_requested.emit(self.event_id))
                row.addWidget(start_btn)
            done_btn = self._make_btn("✓ 完成", INFO, "#DBEAFE")
            done_btn.clicked.connect(lambda: self.complete_requested.emit(self.event_id))
            row.addWidget(done_btn)
            pin_btn = self._make_btn("📌 Pin", INFO, "#DBEAFE")
            pin_btn.clicked.connect(lambda: self.pin_requested.emit(self.event_id))
            row.addWidget(pin_btn)
        elif status == 'pending':
            text = "▶ 继续" if elapsed_seconds > 0 else "▶ 开始"
            start_btn = self._make_btn(text, SUCCESS, SUCCESS_LIGHT)
            start_btn.clicked.connect(lambda: self.start_requested.emit(self.event_id))
            row.addWidget(start_btn)
            done_btn = self._make_btn("✓ 完成", INFO, "#DBEAFE")
            done_btn.clicked.connect(lambda: self.complete_requested.emit(self.event_id))
            row.addWidget(done_btn)
            pin_btn = self._make_btn("📌 Pin", INFO, "#DBEAFE")
            pin_btn.clicked.connect(lambda: self.pin_requested.emit(self.event_id))
            row.addWidget(pin_btn)
        else:  # completed
            done_tag = QLabel("已完成")
            done_tag.setFixedHeight(24)
            done_tag.setAlignment(Qt.AlignCenter)
            done_tag.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
            done_tag.setStyleSheet(
                f"color: {SUCCESS}; background: {SUCCESS_LIGHT}; "
                "border: none; border-radius: 12px; padding: 0 12px;")
            row.addWidget(done_tag)

    @staticmethod
    def _make_btn(text, color, bg):
        btn = QPushButton(text)
        btn.setFixedSize(66, 26)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        btn.setStyleSheet(f"""
            QPushButton {{
                color: {color}; background-color: {bg}; border: none;
                border-radius: 13px; font-size: 10px; font-weight: bold; padding: 0;
            }}
            QPushButton:hover {{ background-color: {color}; color: white; }}
        """)
        return btn


class BoardDueRow(QFrame):
    """即将到期看板行"""

    def __init__(self, board, stats, days_left, parent=None):
        super().__init__(parent)
        self.setObjectName("boardRow")
        overdue = days_left < 0
        self.setStyleSheet(f"""
            #boardRow {{
                background-color: {DANGER_LIGHT if overdue else CARD_BG};
                border: 1px solid {'#FECACA' if overdue else BORDER};
                border-radius: 8px;
            }}
        """)
        self.setFixedHeight(52)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(12)

        name_label = QLabel(board.get('name', '未命名'))
        name_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; border: none;")
        row.addWidget(name_label)

        total = stats.get('total_count', 0)
        completed = stats.get('completed_count', 0)
        progress = QProgressBar()
        progress.setRange(0, max(total, 1))
        progress.setValue(completed)
        progress.setFixedHeight(8)
        progress.setFixedWidth(140)
        progress.setTextVisible(False)
        progress.setStyleSheet(f"""
            QProgressBar {{
                background: #F1F5F9; border: none; border-radius: 4px;
            }}
            QProgressBar::chunk {{ background: {AMBER}; border-radius: 4px; }}
        """)
        row.addWidget(progress)

        progress_label = QLabel(f"{completed}/{total}")
        progress_label.setFont(QFont("Microsoft YaHei", 9))
        progress_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; background: transparent; border: none;")
        row.addWidget(progress_label)

        row.addStretch()

        if overdue:
            due_text = f"已逾期 {abs(days_left)} 天"
            color = DANGER
        elif days_left == 0:
            due_text = "今天截止"
            color = DANGER
        else:
            due_text = f"还剩 {days_left} 天"
            color = DANGER if days_left <= 3 else TEXT_SECONDARY
        due_label = QLabel(f"截止 {board.get('deadline', '')} · {due_text}")
        due_label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        due_label.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        row.addWidget(due_label)


class SectionTitle(QLabel):
    """分区标题"""

    def __init__(self, text, color=TEXT_PRIMARY, parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.setStyleSheet(
            f"color: {color}; background: transparent; border: none; padding: 4px 0;")


class TodayTab(QWidget):
    """今日仪表盘标签页"""

    event_edit_requested = pyqtSignal(int)
    start_timer_requested = pyqtSignal(int)
    stop_timer_requested = pyqtSignal(int)
    complete_requested = pyqtSignal(int)
    pin_requested = pyqtSignal(int)
    resolve_overdue_requested = pyqtSignal()  # 批量处理逾期事项

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

        # 定时自动刷新（只在页面可见时生效）
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._auto_refresh)
        self._refresh_timer.start(15000)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(24, 16, 24, 24)
        self.content_layout.setSpacing(12)

        self.stat_row = QHBoxLayout()
        self.stat_row.setSpacing(12)
        self.stat_today = StatCard("今日计划", INFO)
        self.stat_progress = StatCard("进行中", AMBER)
        self.stat_overdue = StatCard("已逾期", DANGER)
        self.stat_minutes = StatCard("今日投入(分)", SUCCESS)
        self.stat_row.addWidget(self.stat_today)
        self.stat_row.addWidget(self.stat_progress)
        self.stat_row.addWidget(self.stat_overdue)
        self.stat_row.addWidget(self.stat_minutes)
        self.content_layout.addLayout(self.stat_row)

        # 各分区容器（refresh 时重建内容）
        self.overdue_box = QVBoxLayout()
        self.today_box = QVBoxLayout()
        self.timing_box = QVBoxLayout()
        self.boards_box = QVBoxLayout()
        self.content_layout.addLayout(self.overdue_box)
        self.content_layout.addLayout(self.today_box)
        self.content_layout.addLayout(self.timing_box)
        self.content_layout.addLayout(self.boards_box)

        self.content_layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.setStyleSheet(f"""
            TodayTab {{ background-color: {BG}; }}
            QScrollBar:vertical {{ width: 6px; background: transparent; }}
            QScrollBar::handle:vertical {{ background: #CBD5E1; border-radius: 3px; min-height: 24px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)

    def _auto_refresh(self):
        if self.isVisible():
            self.refresh()

    def _clear_box(self, box):
        while box.count():
            item = box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _add_section_header(self, box, text, color=TEXT_PRIMARY):
        box.addWidget(SectionTitle(text, color))

    def _add_empty_hint(self, box, text):
        hint = QLabel(text)
        hint.setFont(QFont("Microsoft YaHei", 10))
        hint.setStyleSheet(
            f"color: {TEXT_DISABLED}; background: transparent; border: none; padding: 2px 4px;")
        box.addWidget(hint)

    def refresh(self):
        """刷新今日数据"""
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M")
        today_str = now.strftime("%Y-%m-%d")

        events = self.db.get_all_events()
        ids = [e['id'] for e in events]
        elapsed_map = self.db.get_elapsed_seconds_map(ids)
        active_map = self.db.get_active_session_map(ids)

        overdue_events = [e for e in events
                          if e.get('status') == 'pending'
                          and e.get('planned_start') and e['planned_start'] < now_str]
        today_events = [e for e in events
                        if (e.get('planned_start') or '').startswith(today_str)]
        timing_events = [e for e in events if e.get('status') == 'in_progress']
        today_minutes = self.db.get_today_minutes()

        # 统计卡片
        self.stat_today.set_value(len(today_events))
        self.stat_progress.set_value(len(timing_events))
        self.stat_overdue.set_value(len(overdue_events))
        self.stat_minutes.set_value(f"{today_minutes:g}")

        # ---- 已逾期 ----
        self._clear_box(self.overdue_box)
        if overdue_events:
            header_row = QWidget()
            header_row.setStyleSheet("background: transparent;")
            header_layout = QHBoxLayout(header_row)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.addWidget(SectionTitle("已逾期", DANGER))
            header_layout.addStretch()
            resolve_btn = QPushButton("批量处理…")
            resolve_btn.setCursor(Qt.PointingHandCursor)
            resolve_btn.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
            resolve_btn.setFixedHeight(26)
            resolve_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {DANGER}; background: {DANGER_LIGHT};
                    border: none; border-radius: 13px; padding: 0 14px;
                    font-size: 10px; font-weight: bold;
                }}
                QPushButton:hover {{ background: {DANGER}; color: white; }}
            """)
            resolve_btn.setToolTip("将逾期事项批量归档或迁移到其他看板")
            resolve_btn.clicked.connect(self.resolve_overdue_requested.emit)
            header_layout.addWidget(resolve_btn)
            self.overdue_box.addWidget(header_row)

            for e in overdue_events:
                row = EventRow(e, elapsed_map.get(e['id'], 0),
                               active_map.get(e['id']) is not None, overdue=True)
                self._connect_row(row)
                self.overdue_box.addWidget(row)
        else:
            self._add_section_header(self.overdue_box, "已逾期", DANGER)
            self._add_empty_hint(self.overdue_box, "没有逾期事项 👍")

        # ---- 今日计划 ----
        self._clear_box(self.today_box)
        self._add_section_header(self.today_box, "今日计划")
        if today_events:
            for e in today_events:
                row = EventRow(e, elapsed_map.get(e['id'], 0),
                               active_map.get(e['id']) is not None)
                self._connect_row(row)
                self.today_box.addWidget(row)
        else:
            self._add_empty_hint(self.today_box, "今天还没有安排，去看板或事项列表添加吧")

        # ---- 计时中 ----
        self._clear_box(self.timing_box)
        self._add_section_header(self.timing_box, "计时中", AMBER_DARK)
        if timing_events:
            for e in timing_events:
                row = EventRow(e, elapsed_map.get(e['id'], 0),
                               active_map.get(e['id']) is not None)
                self._connect_row(row)
                self.timing_box.addWidget(row)
        else:
            self._add_empty_hint(self.timing_box, "当前没有正在计时的任务")

        # ---- 即将到期看板 ----
        self._clear_box(self.boards_box)
        self._add_section_header(self.boards_box, "即将到期看板", DANGER)
        due_boards = []
        for board in self.db.get_boards():
            if board.get('closed_at'):
                continue  # 已结项看板不再提醒
            deadline = board.get('deadline', '')
            if not deadline:
                continue
            try:
                dl = datetime.strptime(deadline, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            days_left = (dl - now.date()).days
            if days_left <= 7:
                due_boards.append((board, days_left))
        if due_boards:
            for board, days_left in sorted(due_boards, key=lambda x: x[1]):
                stats = self.db.get_board_stats(board['id'])
                self.boards_box.addWidget(BoardDueRow(board, stats, days_left))
        else:
            self._add_empty_hint(self.boards_box, "7 天内没有到期的看板")

    def _connect_row(self, row):
        row.edit_requested.connect(self.event_edit_requested.emit)
        row.start_requested.connect(self.start_timer_requested.emit)
        row.stop_requested.connect(self.stop_timer_requested.emit)
        row.complete_requested.connect(self.complete_requested.emit)
        row.pin_requested.connect(self.pin_requested.emit)

"""
主窗口 - 事件管理与卡片控制中心
"""

import os
import sys


def get_resource_path(filename):
    """获取资源文件路径（兼容 PyInstaller onefile 模式）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller onefile 模式：资源在临时目录
        return os.path.join(sys._MEIPASS, filename)
    # 正常运行或开发模式
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QListWidget, QListWidgetItem,
                              QDialog, QFormLayout, QLineEdit, QTextEdit,
                              QDateTimeEdit, QSpinBox, QDoubleSpinBox, QComboBox, QColorDialog,
                              QTabWidget, QMessageBox, QSystemTrayIcon, QMenu,
                              QAction, QGroupBox, QSplitter, QHeaderView,
                              QTableWidget, QTableWidgetItem, QAbstractItemView,
                              QProgressBar, QFrame, QDateEdit, QSizePolicy,
                              QFileDialog, QGridLayout, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QSize, pyqtSignal, QRectF
from PyQt5.QtGui import QIcon, QFont, QColor, QPixmap, QPainter, QBrush, QPen

from database import Database, load_config, save_config
from sticky_note import StickyNoteCard
from notification import NotificationManager, send_windows_notification
from models import Event
from rest_reminder import RestReminderDialog


class EventDialog(QDialog):
    """事件创建/编辑对话框"""

    def __init__(self, parent=None, event_data=None, db=None, default_board_id=None):
        super().__init__(parent)
        self.event_data = event_data
        self.db = db
        self.default_board_id = default_board_id
        self.selected_color = Event.COLORS[0]
        self.setWindowTitle("新建事项" if not event_data else "编辑事项")
        self.setMinimumWidth(420)
        # 设置对话框图标
        icon_path = get_resource_path("logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self._setup_ui()
        if event_data:
            self._load_data(event_data)

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)

        # 标题
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("输入事项标题...")
        self.title_input.setFont(QFont("Microsoft YaHei", 10))
        layout.addRow("📌 标题：", self.title_input)

        # 描述
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("输入事项描述（可选）...")
        self.desc_input.setMaximumHeight(80)
        self.desc_input.setFont(QFont("Microsoft YaHei", 9))
        layout.addRow("📝 描述：", self.desc_input)

        # 计划开始时间 - 日期 + 小时/分钟下拉选择
        datetime_layout = QHBoxLayout()
        datetime_layout.setSpacing(6)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setDate(QDateTime.currentDateTime().addSecs(3600).date())
        self.date_input.setFont(QFont("Microsoft YaHei", 9))
        self.date_input.setFixedHeight(32)
        datetime_layout.addWidget(self.date_input, 2)

        # 小时选择（可编辑，支持手动输入）
        self.hour_combo = QComboBox()
        self.hour_combo.setEditable(True)
        self.hour_combo.setFont(QFont("Microsoft YaHei", 9))
        self.hour_combo.setFixedHeight(32)
        self.hour_combo.addItems([f"{h:02d}" for h in range(24)])
        next_hour = QDateTime.currentDateTime().addSecs(3600).time().hour()
        self.hour_combo.setCurrentIndex(next_hour)
        datetime_layout.addWidget(self.hour_combo, 1)

        # 冒号分隔
        colon_label = QLabel(":")
        colon_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        colon_label.setFixedWidth(8)
        colon_label.setAlignment(Qt.AlignCenter)
        datetime_layout.addWidget(colon_label)

        # 分钟选择（可编辑，支持手动输入任意分钟）
        self.minute_combo = QComboBox()
        self.minute_combo.setEditable(True)
        self.minute_combo.setFont(QFont("Microsoft YaHei", 9))
        self.minute_combo.setFixedHeight(32)
        self.minute_combo.addItems([f"{m:02d}" for m in range(0, 60, 5)])
        next_min = QDateTime.currentDateTime().addSecs(3600).time().minute()
        # 对齐到5分钟
        next_min = (next_min // 5) * 5
        idx = next_min // 5
        if idx < self.minute_combo.count():
            self.minute_combo.setCurrentIndex(idx)
        datetime_layout.addWidget(self.minute_combo, 1)

        layout.addRow("⏰ 开始时间：", datetime_layout)

        # 计划时长 - 下拉框预设 + 自定义输入
        duration_layout = QHBoxLayout()
        duration_layout.setSpacing(8)

        self.duration_combo = QComboBox()
        self.duration_combo.setEditable(True)
        self.duration_combo.setFont(QFont("Microsoft YaHei", 9))
        self.duration_combo.setFixedHeight(32)
        # 预设选项：显示文本 -> 实际分钟数
        self.duration_options = [
            ("15 分钟", 15),
            ("30 分钟", 30),
            ("1 小时", 60),
            ("1.5 小时", 90),
            ("2 小时", 120),
            ("3 小时", 180),
            ("4 小时", 240),
            ("8 小时", 480),
            ("1 天", 480),
            ("2 天", 960),
            ("3 天", 1440),
            ("5 天", 2400),
            ("7 天", 3360),
        ]
        for text, _ in self.duration_options:
            self.duration_combo.addItem(text)
        self.duration_combo.setCurrentIndex(1)  # 默认 30 分钟
        self.duration_combo.lineEdit().setValidator(None)  # 允许自由输入
        duration_layout.addWidget(self.duration_combo, 1)

        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.5, 240)  # 最大240小时(30天)
        self.duration_spin.setValue(0.5)
        self.duration_spin.setSingleStep(0.5)
        self.duration_spin.setSuffix(" 小时")
        self.duration_spin.setDecimals(1)
        self.duration_spin.setFont(QFont("Microsoft YaHei", 9))
        self.duration_spin.setFixedHeight(32)
        self.duration_spin.setFixedWidth(100)
        # 下拉框变化时同步到微调框
        self.duration_combo.currentTextChanged.connect(self._sync_duration_from_combo)
        self.duration_spin.valueChanged.connect(self._sync_duration_from_spin)
        duration_layout.addWidget(self.duration_spin)

        layout.addRow("⏱ 计划时长：", duration_layout)

        # 优先级
        self.priority_input = QComboBox()
        self.priority_input.addItems(["🔴 高", "🟡 中", "🟢 低"])
        self.priority_input.setCurrentIndex(1)
        self.priority_input.setFont(QFont("Microsoft YaHei", 9))
        layout.addRow("⚡ 优先级：", self.priority_input)

        # 颜色选择
        color_layout = QHBoxLayout()
        self.color_btn = QPushButton("  ")
        self.color_btn.setFixedSize(40, 30)
        self.color_btn.setStyleSheet(
            f"background-color: {self.selected_color}; border: 2px solid #ccc; border-radius: 4px;")
        self.color_btn.clicked.connect(self._choose_color)
        self.color_label = QLabel(self.selected_color)
        color_layout.addWidget(self.color_btn)
        color_layout.addWidget(self.color_label)
        color_layout.addStretch()
        layout.addRow("🎨 颜色：", color_layout)

        # 归属看板
        self.board_combo = QComboBox()
        self.board_combo.setFont(QFont("Microsoft YaHei", 9))
        self.board_combo.setFixedHeight(32)
        if self.db:
            boards = self.db.get_boards()
            self.board_combo.addItem("无", None)
            for board in boards:
                self.board_combo.addItem(board['name'], board['id'])
            if self.default_board_id is not None:
                for i in range(self.board_combo.count()):
                    if self.board_combo.itemData(i) == self.default_board_id:
                        self.board_combo.setCurrentIndex(i)
                        break
        else:
            self.board_combo.addItem("无", None)
        layout.addRow("📋 归属看板：", self.board_combo)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addRow(btn_layout)

        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                border-radius: 12px;
            }
            QLabel {
                color: #333;
                font-size: 12px;
            }
            QLineEdit, QTextEdit, QDateTimeEdit, QSpinBox, QComboBox {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #3498db;
            }
            #saveBtn {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: bold;
                font-size: 13px;
            }
            #saveBtn:hover {
                background-color: #2980b9;
            }
            #cancelBtn {
                background-color: #ecf0f1;
                color: #7f8c8d;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
            }
            #cancelBtn:hover {
                background-color: #bdc3c7;
            }
        """)

    def _choose_color(self):
        color = QColorDialog.getColor(QColor(self.selected_color), self, "选择便利贴颜色")
        if color.isValid():
            self.selected_color = color.name()
            self.color_btn.setStyleSheet(
                f"background-color: {self.selected_color}; border: 2px solid #ccc; border-radius: 4px;")
            self.color_label.setText(self.selected_color)

    def _sync_duration_from_combo(self, text):
        """下拉框选择时同步到微调框（微调框单位为小时）"""
        for display, minutes in self.duration_options:
            if display == text:
                self.duration_spin.blockSignals(True)
                self.duration_spin.setValue(minutes / 60.0)
                self.duration_spin.blockSignals(False)
                return
        # 如果是自定义输入，尝试解析
        try:
            text_clean = text.replace("分钟", "").replace("分", "").replace("小时", "").replace("天", "").strip()
            val = int(text_clean)
            if "天" in text:
                hours = val * 8
            elif "小时" in text:
                hours = val
            elif "分" in text or "分钟" in text:
                hours = val / 60.0
            else:
                hours = val
            self.duration_spin.blockSignals(True)
            self.duration_spin.setValue(min(max(hours, 0.5), 240))
            self.duration_spin.blockSignals(False)
        except (ValueError, TypeError):
            pass

    def _sync_duration_from_spin(self, value):
        """微调框变化时同步到下拉框"""
        minutes = int(value * 60)
        # 找到匹配的预设
        for display, mins in self.duration_options:
            if mins == minutes:
                self.duration_combo.blockSignals(True)
                self.duration_combo.setCurrentText(display)
                self.duration_combo.blockSignals(False)
                return
        # 没有匹配的预设，显示自定义值
        self.duration_combo.blockSignals(True)
        if minutes >= 480 and minutes % 480 == 0:
            self.duration_combo.setCurrentText(f"{minutes // 480} 天")
        elif minutes >= 60 and minutes % 60 == 0:
            self.duration_combo.setCurrentText(f"{minutes // 60} 小时")
        else:
            self.duration_combo.setCurrentText(f"{minutes} 分钟")
        self.duration_combo.blockSignals(False)

    def _load_data(self, data):
        """加载已有数据"""
        self.title_input.setText(data.get('title', ''))
        self.desc_input.setPlainText(data.get('description', ''))
        if data.get('planned_start'):
            dt = QDateTime.fromString(data['planned_start'], "yyyy-MM-dd HH:mm")
            if dt.isValid():
                self.date_input.setDate(dt.date())
                self.hour_combo.setCurrentIndex(dt.time().hour())
                minute_idx = dt.time().minute() // 5
                if minute_idx < self.minute_combo.count():
                    self.minute_combo.setCurrentIndex(minute_idx)
        duration = data.get('planned_duration_minutes', 30)
        self.duration_spin.setValue(duration / 60.0)
        # 同步下拉框
        self._sync_duration_from_spin(duration / 60.0)

        priority_map = {"high": 0, "medium": 1, "low": 2}
        self.priority_input.setCurrentIndex(priority_map.get(data.get('priority', 'medium'), 1))

        if data.get('color'):
            self.selected_color = data['color']
            self.color_btn.setStyleSheet(
                f"background-color: {self.selected_color}; border: 2px solid #ccc; border-radius: 4px;")
            self.color_label.setText(self.selected_color)

        # 设置归属看板
        if data.get('board_id') is not None:
            for i in range(self.board_combo.count()):
                if self.board_combo.itemData(i) == data['board_id']:
                    self.board_combo.setCurrentIndex(i)
                    break

    def get_data(self):
        """获取对话框数据"""
        priority_map = {0: "high", 1: "medium", 2: "low"}
        # 组合日期和时间
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        hour = self.hour_combo.currentText()
        minute = self.minute_combo.currentText()
        return {
            'title': self.title_input.text().strip(),
            'description': self.desc_input.toPlainText().strip(),
            'planned_start': f"{date_str} {hour}:{minute}",
            'planned_duration_minutes': int(self.duration_spin.value() * 60),
            'priority': priority_map[self.priority_input.currentIndex()],
            'color': self.selected_color,
            'board_id': self.board_combo.currentData(),
        }


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.db = Database()
        self.notification_mgr = NotificationManager()
        self.sticky_cards = {}  # event_id -> StickyNoteCard
        self._rest_reminder_active = False  # 休息提醒是否正在显示
        self._rest_reminder_event_id = None  # 休息提醒关联的事件ID
        self._last_rest_trigger_time = {}  # 记录每个事件上次触发休息时的累计秒数

        self.setWindowTitle("📌 桌面便利贴 - 计划计时系统")
        self.setMinimumSize(900, 650)

        # 设置窗口图标
        icon_path = get_resource_path("logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self._setup_ui()
        self._setup_tray_icon()
        self._setup_timers()
        self._refresh_event_list()

    def _setup_ui(self):
        """设置主界面"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部标题栏
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(56)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("📌 桌面便利贴")
        title.setObjectName("headerTitle")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        header_layout.addWidget(title)

        header_layout.addStretch()

        main_layout.addWidget(header)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")

        # Tab1: 看板
        from kanban_tab import KanbanTab
        self.kanban_tab = KanbanTab(self.db)
        self.kanban_tab.event_edit_requested.connect(self._on_kanban_edit_event)
        self.kanban_tab.event_status_changed.connect(self._on_kanban_status_changed)
        self.kanban_tab.create_event_requested.connect(self._on_kanban_create_event)
        self.kanban_tab.pin_card_to_desktop.connect(self._create_sticky_card)
        self.kanban_tab.event_duplicate.connect(self._duplicate_event)
        self.tabs.addTab(self.kanban_tab, "📋 看板")

        # Tab2: 事件列表
        self.event_tab = QWidget()
        self._setup_event_tab()
        self.tabs.addTab(self.event_tab, "📝 事项列表")

        # Tab3: 桌面卡片管理
        self.cards_tab = QWidget()
        self._setup_cards_tab()
        self.tabs.addTab(self.cards_tab, "📌 桌面卡片")

        # Tab4: 甘特图
        from gantt_tab import GanttTab
        self.gantt_tab = GanttTab(self.db)
        self.gantt_tab.event_edit_requested.connect(self._edit_event)
        self.tabs.addTab(self.gantt_tab, "📊 甘特图")

        # Tab5: 归档分析
        self.archive_tab = QWidget()
        self._setup_archive_tab()
        self.tabs.addTab(self.archive_tab, "📊 归档分析")

        # Tab6: 设置
        self.settings_tab = QWidget()
        self._setup_settings_tab()
        self.tabs.addTab(self.settings_tab, "⚙️ 设置")

        main_layout.addWidget(self.tabs)

        # 标签页切换信号
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # 初始化数据
        self._refresh_event_list()
        self._refresh_archive()

        # 底部状态栏
        self.statusBar().showMessage("就绪")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #ecf0f1;
                color: #7f8c8d;
                font-size: 11px;
                padding: 2px 10px;
            }
        """)

        # 全局样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f2f5;
            }
            #header {
                background-color: white;
                border-bottom: 1px solid #e0e0e0;
            }
            #headerTitle {
                color: #2c3e50;
            }
            QTabWidget::pane {
                border: none;
                background-color: #f0f2f5;
            }
            QTabBar::tab {
                background-color: #ecf0f1;
                color: #7f8c8d;
                padding: 10px 24px;
                font-size: 12px;
                font-weight: bold;
                border: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #3498db;
            }
            QTabBar::tab:hover {
                background-color: #dfe6e9;
            }
            QPushButton {
                font-family: "Microsoft YaHei";
            }
        """)

        # 启动时恢复桌面卡片
        QTimer.singleShot(500, self._restore_sticky_cards)

    def _restore_sticky_cards(self):
        """启动时恢复之前打开的桌面卡片"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT event_id FROM card_positions")
        rows = cursor.fetchall()
        for row in rows:
            event_id = row['event_id']
            event_data = self.db.get_event(event_id)
            if event_data and event_data.get('status') not in ('archived',):
                self._create_sticky_card(event_id)
                # 初始化休息提醒触发计数，避免启动后立刻触发
                if self.db.get_setting('rest_reminder_enabled', False):
                    elapsed = self.db.get_total_elapsed_seconds(event_id)
                    interval = int(self.db.get_setting('rest_interval_minutes', 120)) * 60
                    if interval > 0:
                        self._last_rest_trigger_time[event_id] = int(elapsed // interval)

    def _setup_event_tab(self):
        """设置事件列表标签页"""
        layout = QVBoxLayout(self.event_tab)
        layout.setContentsMargins(16, 16, 16, 16)

        # 工具栏 - 分两行：第一行基础操作，第二行批量操作
        toolbar1 = QHBoxLayout()
        toolbar1.setSpacing(6)

        # 看板过滤下拉框
        self.board_filter_combo = QComboBox()
        self.board_filter_combo.setObjectName("toolBtn")
        self.board_filter_combo.setFont(QFont("Microsoft YaHei", 10))
        self.board_filter_combo.setFixedHeight(26)
        self.board_filter_combo.setFixedWidth(120)
        self.board_filter_combo.addItem("全部看板", None)
        boards = self.db.get_boards()
        for board in boards:
            self.board_filter_combo.addItem(board['name'], board['id'])
        self.board_filter_combo.currentIndexChanged.connect(self._refresh_event_list)
        toolbar1.addWidget(self.board_filter_combo)

        add_btn = QPushButton("＋ 新建")
        add_btn.setObjectName("addBtn")
        add_btn.setFixedHeight(26)
        add_btn.clicked.connect(self._add_event)
        toolbar1.addWidget(add_btn)

        edit_btn = QPushButton("编辑")
        edit_btn.setObjectName("toolBtn")
        edit_btn.setFixedHeight(26)
        edit_btn.clicked.connect(self._edit_event)
        toolbar1.addWidget(edit_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setObjectName("deleteBtn")
        delete_btn.setFixedHeight(26)
        delete_btn.clicked.connect(self._delete_event)
        toolbar1.addWidget(delete_btn)

        pin_btn = QPushButton("Pin桌面")
        pin_btn.setObjectName("pinBtn")
        pin_btn.setFixedHeight(26)
        pin_btn.clicked.connect(self._pin_selected_event)
        toolbar1.addWidget(pin_btn)

        archive_btn = QPushButton("归档")
        archive_btn.setObjectName("archiveBtn")
        archive_btn.setFixedHeight(26)
        archive_btn.clicked.connect(self._archive_selected_events)
        toolbar1.addWidget(archive_btn)

        toolbar1.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.setObjectName("toolBtn")
        refresh_btn.setFixedHeight(26)
        refresh_btn.clicked.connect(self._refresh_event_list)
        toolbar1.addWidget(refresh_btn)

        layout.addLayout(toolbar1)

        # 第二行：批量操作
        toolbar2 = QHBoxLayout()
        toolbar2.setSpacing(6)

        batch_label = QLabel("批量操作：")
        batch_label.setStyleSheet("color: #7f8c8d; font-size: 11px; border: none;")
        toolbar2.addWidget(batch_label)

        batch_start_btn = QPushButton("▶ 开始")
        batch_start_btn.setObjectName("batchBtn")
        batch_start_btn.setFixedHeight(24)
        batch_start_btn.clicked.connect(self._batch_start)
        toolbar2.addWidget(batch_start_btn)

        batch_pause_btn = QPushButton("⏸ 暂停")
        batch_pause_btn.setObjectName("batchBtn")
        batch_pause_btn.setFixedHeight(24)
        batch_pause_btn.clicked.connect(self._batch_pause)
        toolbar2.addWidget(batch_pause_btn)

        batch_done_btn = QPushButton("✓ 完成")
        batch_done_btn.setObjectName("batchBtn")
        batch_done_btn.setFixedHeight(24)
        batch_done_btn.clicked.connect(self._batch_complete)
        toolbar2.addWidget(batch_done_btn)

        toolbar2.addStretch()

        sel_hint = QLabel("（Ctrl+点击可多选）")
        sel_hint.setStyleSheet("color: #bdc3c7; font-size: 10px; border: none;")
        toolbar2.addWidget(sel_hint)

        layout.addLayout(toolbar2)

        # 事件列表
        self.event_list = QListWidget()
        self.event_list.setObjectName("eventList")
        self.event_list.setFont(QFont("Microsoft YaHei", 10))
        self.event_list.setIconSize(QSize(16, 16))
        self.event_list.setSpacing(6)
        self.event_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # 双击触发编辑
        self.event_list.itemDoubleClicked.connect(self._edit_event)
        # 右键菜单
        self.event_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.event_list.customContextMenuRequested.connect(self._show_event_list_context_menu)
        layout.addWidget(self.event_list)

        # 样式 - 工具栏按钮（不设 min/max-height，由 setFixedHeight 控制）
        BTN_PADDING = "4px 12px"
        BTN_RADIUS = "6px"
        BTN_FONT = "11px"

        self.event_tab.setStyleSheet(f"""
            #addBtn {{
                background-color: #27ae60;
                color: white;
                border: 1px solid transparent;
                border-radius: {BTN_RADIUS};
                padding: {BTN_PADDING};
                font-weight: bold;
                font-size: {BTN_FONT};
            }}
            #addBtn:hover {{
                background-color: #2ecc71;
            }}
            #toolBtn {{
                background-color: white;
                color: #555;
                border: 1px solid transparent;
                border-radius: {BTN_RADIUS};
                padding: {BTN_PADDING};
                font-size: {BTN_FONT};
            }}
            #toolBtn:hover {{
                background-color: #ecf0f1;
                color: #3498db;
            }}
            #deleteBtn {{
                background-color: white;
                color: #555;
                border: 1px solid transparent;
                border-radius: {BTN_RADIUS};
                padding: {BTN_PADDING};
                font-size: {BTN_FONT};
            }}
            #deleteBtn:hover {{
                background-color: #fdedec;
                color: #e74c3c;
            }}
            #batchBtn {{
                background-color: #f8f9fa;
                color: #555;
                border: 1px solid transparent;
                border-radius: {BTN_RADIUS};
                padding: {BTN_PADDING};
                font-size: 11px;
            }}
            #batchBtn:hover {{
                background-color: #ecf0f1;
                color: #3498db;
            }}
            #pinBtn {{
                background-color: #3498db;
                color: white;
                border: 1px solid transparent;
                border-radius: {BTN_RADIUS};
                padding: {BTN_PADDING};
                font-weight: bold;
                font-size: {BTN_FONT};
            }}
            #pinBtn:hover {{
                background-color: #2980b9;
            }}
            #archiveBtn {{
                background-color: #8e44ad;
                color: white;
                border: 1px solid transparent;
                border-radius: {BTN_RADIUS};
                padding: {BTN_PADDING};
                font-weight: bold;
                font-size: {BTN_FONT};
            }}
            #archiveBtn:hover {{
                background-color: #9b59b6;
            }}
            #eventList {{
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
                outline: none;
            }}
            #eventList::item {{
                padding: 10px;
                border-radius: 6px;
                border: 1px solid transparent;
            }}
            #eventList::item:hover {{
                background-color: #ebf5fb;
                border-color: #aed6f1;
            }}
            #eventList::item:selected {{
                background-color: #d4e6f1;
                border-color: #3498db;
                color: #2c3e50;
            }}
        """)

    def _setup_cards_tab(self):
        """设置桌面卡片管理标签页"""
        layout = QVBoxLayout(self.cards_tab)
        layout.setContentsMargins(16, 16, 16, 16)

        # 说明
        info = QLabel("📌 已 Pin 到桌面的卡片会显示在桌面上，可自由拖拽。")
        info.setStyleSheet("color: #7f8c8d; font-size: 12px; padding: 8px;")
        layout.addWidget(info)

        # 卡片列表
        self.card_list = QListWidget()
        self.card_list.setFont(QFont("Microsoft YaHei", 10))
        self.card_list.setSpacing(4)
        layout.addWidget(self.card_list)

        # 操作按钮
        btn_layout = QHBoxLayout()

        remove_card_btn = QPushButton("❌ 取消 Pin")
        remove_card_btn.setObjectName("removeCardBtn")
        remove_card_btn.clicked.connect(self._remove_selected_card)
        btn_layout.addWidget(remove_card_btn)

        show_all_btn = QPushButton("👁️ 显示所有卡片")
        show_all_btn.setObjectName("showAllBtn")
        show_all_btn.clicked.connect(self._show_all_cards)
        btn_layout.addWidget(show_all_btn)

        hide_all_btn = QPushButton("🙈 隐藏所有卡片")
        hide_all_btn.setObjectName("hideAllBtn")
        hide_all_btn.clicked.connect(self._hide_all_cards)
        btn_layout.addWidget(hide_all_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.cards_tab.setStyleSheet("""
            #cardList {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
                outline: none;
            }
            #removeCardBtn {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            #removeCardBtn:hover {
                background-color: #c0392b;
            }
            #showAllBtn, #hideAllBtn {
                background-color: white;
                color: #555;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }
            #showAllBtn:hover, #hideAllBtn:hover {
                background-color: #ecf0f1;
                border-color: #3498db;
                color: #3498db;
            }
        """)

    def _setup_archive_tab(self):
        """设置归档分析标签页"""
        layout = QVBoxLayout(self.archive_tab)
        layout.setContentsMargins(16, 16, 16, 16)

        # 统计概览
        stats_group = QGroupBox("📈 统计概览")
        stats_group.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        stats_layout = QHBoxLayout(stats_group)

        self.total_label = QLabel("已完成: 0")
        self.total_label.setFont(QFont("Microsoft YaHei", 10))
        stats_layout.addWidget(self.total_label)

        self.avg_diff_label = QLabel("平均偏差: 0 分钟")
        self.avg_diff_label.setFont(QFont("Microsoft YaHei", 10))
        stats_layout.addWidget(self.avg_diff_label)

        self.accuracy_label = QLabel("准时率: 0%")
        self.accuracy_label.setFont(QFont("Microsoft YaHei", 10))
        stats_layout.addWidget(self.accuracy_label)

        layout.addWidget(stats_group)

        # 操作按钮栏
        archive_toolbar = QHBoxLayout()
        archive_toolbar.setSpacing(8)

        restore_btn = QPushButton("↩️ 恢复到事项列表")
        restore_btn.setObjectName("archiveToolBtn")
        restore_btn.setFixedHeight(34)
        restore_btn.clicked.connect(self._restore_selected_archive)
        archive_toolbar.addWidget(restore_btn)

        delete_archive_btn = QPushButton("🗑️ 删除归档")
        delete_archive_btn.setObjectName("archiveDelBtn")
        delete_archive_btn.setFixedHeight(34)
        delete_archive_btn.clicked.connect(self._delete_selected_archive)
        archive_toolbar.addWidget(delete_archive_btn)

        archive_toolbar.addStretch()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setObjectName("archiveToolBtn")
        refresh_btn.setFixedHeight(34)
        refresh_btn.clicked.connect(self._refresh_archive)
        archive_toolbar.addWidget(refresh_btn)

        layout.addLayout(archive_toolbar)

        # 分析表格
        self.archive_table = QTableWidget()
        self.archive_table.setColumnCount(11)
        self.archive_table.setHorizontalHeaderLabels(
            ["事项", "归属看板", "计划时长", "实际时长", "偏差", "准时率", "实际开始", "完成日期", "优先级", "状态", "备注"])
        self.archive_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.archive_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.archive_table.setAlternatingRowColors(True)
        self.archive_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.archive_table.verticalHeader().setVisible(False)
        self.archive_table.doubleClicked.connect(self._on_archive_double_click)
        layout.addWidget(self.archive_table)

        self.archive_tab.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 16px;
                margin-top: 8px;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                gridline-color: #ecf0f1;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QTableWidget::item:alternate {
                background-color: #f8f9fa;
            }
            QTableWidget::item:selected {
                background-color: #d4e6f1;
                color: #2c3e50;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                color: #2c3e50;
                padding: 8px;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }
            #archiveToolBtn {
                background-color: white;
                color: #555;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
            }
            #archiveToolBtn:hover {
                background-color: #ecf0f1;
                border-color: #3498db;
                color: #3498db;
            }
            #archiveDelBtn {
                background-color: white;
                color: #555;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
            }
            #archiveDelBtn:hover {
                background-color: #fdedec;
                border-color: #e74c3c;
                color: #e74c3c;
            }
        """)

    def _setup_settings_tab(self):
        """设置标签页"""
        outer_layout = QVBoxLayout(self.settings_tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # 滚动区域
        from PyQt5.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f0f2f5; }")

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(16, 16, 16, 16)

        # 数据存储设置
        storage_group = QGroupBox("💾 数据存储")
        storage_group.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        storage_layout = QVBoxLayout(storage_group)

        # 当前路径显示
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("当前数据库位置："))
        config = load_config()
        current_path = self.db.db_path
        self.db_path_label = QLabel(current_path)
        self.db_path_label.setStyleSheet(
            "color: #2c3e50; font-size: 11px; border: 1px solid #ddd; "
            "border-radius: 4px; padding: 4px 8px; background: white;")
        self.db_path_label.setWordWrap(True)
        path_layout.addWidget(self.db_path_label, 1)
        storage_layout.addLayout(path_layout)

        # 选择路径按钮
        btn_layout = QHBoxLayout()
        change_btn = QPushButton("📂 更改存储位置")
        change_btn.setObjectName("settingsBtn")
        change_btn.clicked.connect(self._change_db_path)
        btn_layout.addWidget(change_btn)

        reset_btn = QPushButton("↩️ 恢复默认位置")
        reset_btn.setObjectName("settingsBtn2")
        reset_btn.clicked.connect(self._reset_db_path)
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()
        storage_layout.addLayout(btn_layout)

        tip_label = QLabel(
            "💡 更改存储位置后，需要重启应用生效。\n"
            "   如需保留旧数据，请手动将旧的 sticky_notes.db 复制到新位置。")
        tip_label.setStyleSheet("color: #95a5a6; font-size: 11px; border: none; padding: 8px 0;")
        tip_label.setWordWrap(True)
        storage_layout.addWidget(tip_label)

        layout.addWidget(storage_group)

        # 休息提醒设置
        rest_group = QGroupBox("🐱 休息提醒")
        rest_group.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        rest_layout = QVBoxLayout(rest_group)

        # 开启休息提醒
        self.rest_reminder_check = QCheckBox("开启休息提醒")
        self.rest_reminder_check.setFont(QFont("Microsoft YaHei", 10))
        self.rest_reminder_check.setChecked(
            self.db.get_setting('rest_reminder_enabled', False))
        rest_layout.addWidget(self.rest_reminder_check)

        # 工作间隔设置
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("工作间隔："))
        self.rest_interval_spin = QSpinBox()
        self.rest_interval_spin.setRange(30, 480)
        self.rest_interval_spin.setSuffix(" 分钟")
        self.rest_interval_spin.setValue(
            int(self.db.get_setting('rest_interval_minutes', 120)))
        self.rest_interval_spin.setFont(QFont("Microsoft YaHei", 10))
        interval_layout.addWidget(self.rest_interval_spin)
        interval_layout.addWidget(QLabel("（30~480分钟）"))
        interval_layout.addStretch()
        rest_layout.addLayout(interval_layout)

        # 休息时长设置
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("休息时长："))
        self.rest_duration_spin = QSpinBox()
        self.rest_duration_spin.setRange(1, 60)
        self.rest_duration_spin.setSuffix(" 分钟")
        self.rest_duration_spin.setValue(
            int(self.db.get_setting('rest_duration_minutes', 10)))
        self.rest_duration_spin.setFont(QFont("Microsoft YaHei", 10))
        duration_layout.addWidget(self.rest_duration_spin)
        duration_layout.addWidget(QLabel("（1~60分钟）"))
        duration_layout.addStretch()
        rest_layout.addLayout(duration_layout)

        # 自定义背景图片
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel("休息图片："))
        self.rest_bg_path_label = QLabel("(默认猫咪)")
        self.rest_bg_path_label.setStyleSheet("color: #7f8c8d; border: none;")
        self.rest_bg_path_label.setFont(QFont("Microsoft YaHei", 9))
        bg_layout.addWidget(self.rest_bg_path_label, 1)
        bg_select_btn = QPushButton("选择")
        bg_select_btn.setFixedWidth(50)
        bg_select_btn.setFont(QFont("Microsoft YaHei", 9))
        bg_select_btn.clicked.connect(self._select_rest_bg_image)
        bg_layout.addWidget(bg_select_btn)
        bg_clear_btn = QPushButton("恢复默认")
        bg_clear_btn.setFixedWidth(70)
        bg_clear_btn.setFont(QFont("Microsoft YaHei", 9))
        bg_clear_btn.clicked.connect(self._clear_rest_bg_image)
        bg_layout.addWidget(bg_clear_btn)
        rest_layout.addLayout(bg_layout)

        # 加载已保存的背景图片路径
        saved_bg = self.db.get_setting('rest_bg_image_path', '')
        if saved_bg:
            self.rest_bg_path_label.setText(saved_bg)
            self.rest_bg_path_label.setToolTip(saved_bg)

        # 保存按钮
        save_rest_btn = QPushButton("保存休息提醒设置")
        save_rest_btn.setObjectName("settingsBtn")
        save_rest_btn.clicked.connect(self._save_rest_reminder_settings)
        rest_layout.addWidget(save_rest_btn)

        # 提示
        rest_tip = QLabel(
            "💡 开启后，连续计时达到设定间隔将自动弹出休息提醒。\n"
            "   休息期间无法跳过，倒计时结束后自动恢复计时。\n"
            "   自定义图片推荐横版（16:9），分辨率不低于 1920×1080。")
        rest_tip.setStyleSheet(
            "color: #95a5a6; font-size: 11px; border: none; padding: 8px 0;")
        rest_tip.setWordWrap(True)
        rest_layout.addWidget(rest_tip)

        layout.addWidget(rest_group)

        # 关于信息
        about_group = QGroupBox("ℹ️ 关于")
        about_group.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        about_layout = QVBoxLayout(about_group)
        about_label = QLabel(
            "📌 桌面便利贴 - 计划计时系统 v1.0\n\n"
            "功能：事项管理 · 桌面卡片 · 计时器 · 归档分析 · 智能提醒")
        about_label.setStyleSheet("color: #555; font-size: 12px; border: none;")
        about_layout.addWidget(about_label)
        layout.addWidget(about_group)

        layout.addStretch()

        scroll.setWidget(scroll_content)
        outer_layout.addWidget(scroll)

        self.settings_tab.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 16px;
                margin-top: 8px;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }
            QLabel {
                border: none;
            }
            #settingsBtn {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 12px;
            }
            #settingsBtn:hover {
                background-color: #2980b9;
            }
            #settingsBtn2 {
                background-color: #ecf0f1;
                color: #555;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
            }
            #settingsBtn2:hover {
                background-color: #dfe6e9;
                border-color: #3498db;
                color: #3498db;
            }
        """)

    def _change_db_path(self):
        """更改数据库存储位置"""
        try:
            start_dir = ""
            if self.db.db_path:
                start_dir = os.path.dirname(self.db.db_path)
            folder = QFileDialog.getExistingDirectory(
                self, "选择数据存储文件夹", start_dir)
        except Exception:
            folder = QFileDialog.getExistingDirectory(
                self, "选择数据存储文件夹", "")

        if not folder:
            return

        try:
            # 先检查新路径是否可写
            test_file = os.path.join(folder, "sticky_notes.db")
            # 如果新路径已有数据库文件，提示用户
            if os.path.exists(test_file):
                reply = QMessageBox.question(
                    self, "发现已有数据库",
                    "所选文件夹中已存在 sticky_notes.db 文件。\n"
                    "是否使用该数据库？（旧数据将被替换）",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return

            # 保存配置
            config = load_config()
            config["db_path"] = folder
            save_config(config)

            # 更新界面显示
            self.db_path_label.setText(test_file)

            old_path = self.db.db_path
            QMessageBox.information(
                self, "设置已保存",
                "数据存储位置已更改为：\n"
                + folder
                + "\n\n请重启应用以使更改生效。\n"
                + "如需保留旧数据，请手动将以下文件复制到新位置：\n"
                + str(old_path))
        except Exception as e:
            QMessageBox.warning(self, "保存失败", "保存设置时出错：\n" + str(e))

    def _reset_db_path(self):
        """恢复默认存储位置"""
        try:
            config = load_config()
            config["db_path"] = ""
            save_config(config)
            from database import Database as DB
            default_path = DB._get_default_db_path()
            self.db_path_label.setText(default_path)
            QMessageBox.information(
                self, "设置已保存", "已恢复默认存储位置。\n\n请重启应用以使更改生效。")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存设置时出错：\n{e}")

    def _save_rest_reminder_settings(self):
        """保存休息提醒设置"""
        try:
            self.db.set_setting(
                'rest_reminder_enabled',
                self.rest_reminder_check.isChecked())
            self.db.set_setting(
                'rest_interval_minutes',
                self.rest_interval_spin.value())
            self.db.set_setting(
                'rest_duration_minutes',
                self.rest_duration_spin.value())
            QMessageBox.information(self, "设置已保存", "休息提醒设置已保存。")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存设置时出错：\n{e}")

    def _select_rest_bg_image(self):
        """选择休息提醒背景图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择休息提醒图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*)")
        if file_path:
            # 验证图片是否可加载
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                QMessageBox.warning(self, "图片无效", "无法加载该图片，请选择其他文件。")
                return
            # 显示图片信息
            info = os.path.basename(file_path)
            info += f" ({pixmap.width()}×{pixmap.height()})"
            self.rest_bg_path_label.setText(info)
            self.rest_bg_path_label.setToolTip(file_path)
            # 保存到数据库
            self.db.set_setting('rest_bg_image_path', file_path)

    def _clear_rest_bg_image(self):
        """恢复默认背景图片"""
        self.rest_bg_path_label.setText("(默认猫咪)")
        self.rest_bg_path_label.setToolTip("")
        self.db.set_setting('rest_bg_image_path', '')

    def _setup_tray_icon(self):
        """设置系统托盘图标"""
        # 创建一个简单的图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        # 绘制一个黄色便利贴图标
        painter.setBrush(QBrush(QColor("#FFF9C4")))
        painter.setPen(QPen(QColor("#F9A825"), 2))
        painter.drawRoundedRect(QRectF(2, 2, 28, 28), 4, 4)
        painter.setPen(QPen(QColor("#F9A825"), 1))
        painter.drawLine(QRectF(8, 10, 16, 10).topLeft(),
                         QRectF(8, 10, 16, 10).bottomRight())
        painter.drawLine(QRectF(8, 15, 12, 15).topLeft(),
                         QRectF(8, 15, 12, 15).bottomRight())
        painter.end()

        icon = QIcon(pixmap)
        self.tray_icon = QSystemTrayIcon(icon, self)

        # 托盘菜单
        tray_menu = QMenu()

        show_action = QAction("📌 显示主窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        add_action = QAction("➕ 新建事项", self)
        add_action.triggered.connect(self._add_event)
        tray_menu.addAction(add_action)

        tray_menu.addSeparator()

        quit_action = QAction("❌ 退出", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.setToolTip("桌面便利贴 - 计划计时系统")
        self.tray_icon.show()

    def _setup_timers(self):
        """设置定时器"""
        # 每分钟检查一次是否有事件需要通知
        self.notify_timer = QTimer(self)
        self.notify_timer.timeout.connect(self._check_notifications)
        self.notify_timer.start(30000)  # 30秒检查一次

        # 每秒更新状态栏
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)

    # ==================== 事件操作 ====================

    def _add_event(self):
        """新建事件"""
        board_id = self.board_filter_combo.currentData()
        dialog = EventDialog(self, db=self.db, default_board_id=board_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['title']:
                QMessageBox.warning(self, "提示", "请输入事项标题！")
                return
            self.db.add_event(**data)
            self._refresh_event_list()
            self.statusBar().showMessage(f"✅ 已添加事项: {data['title']}", 3000)

    def _edit_event(self, event_id=None):
        """编辑事件"""
        if event_id is None:
            current = self.event_list.currentItem()
            if not current:
                QMessageBox.information(self, "提示", "请先选择一个事项")
                return
            event_id = current.data(Qt.UserRole)

        event_data = self.db.get_event(event_id)
        if not event_data:
            return

        dialog = EventDialog(self, event_data, db=self.db)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['title']:
                QMessageBox.warning(self, "提示", "请输入事项标题！")
                return
            self.db.update_event(event_id, **data)
            # 如果修改了开始时间，重置通知状态以允许重新触发提醒
            if data.get('planned_start') != event_data.get('planned_start'):
                self.notification_mgr.reset_notification(event_id)
            self._refresh_event_list()
            self.statusBar().showMessage(f"✅ 已更新事项: {data['title']}", 3000)

    def _duplicate_event(self, event_id):
        """复制事件（弹出编辑对话框让用户确认）"""
        event_data = self.db.get_event(event_id)
        if not event_data:
            return

        # 准备复制的数据：标题加"(副本)"，状态重置
        copy_data = dict(event_data)
        copy_data['title'] = event_data['title'] + " (副本)" if event_data.get('title') else "(副本)"
        copy_data['status'] = 'pending'
        # 清除计时相关字段
        copy_data['actual_start_at'] = None
        copy_data['actual_duration_seconds'] = 0

        # 弹出编辑对话框让用户确认/修改
        dialog = EventDialog(self, copy_data, db=self.db)
        dialog.setWindowTitle("复制事项")
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['title']:
                QMessageBox.warning(self, "提示", "请输入事项标题！")
                return
            # 创建新事件
            new_id = self.db.add_event(**data)
            self._refresh_event_list()
            # 同步刷新看板
            if hasattr(self, 'kanban_tab'):
                self.kanban_tab.refresh()
            self.statusBar().showMessage(f"✅ 已复制事项: {data['title']}", 3000)

    def _delete_event(self):
        """删除事件"""
        current = self.event_list.currentItem()
        if not current:
            QMessageBox.information(self, "提示", "请先选择一个事项")
            return

        event_id = current.data(Qt.UserRole)
        if not event_id:
            QMessageBox.warning(self, "提示", "无法获取事项ID，请重新选择")
            return

        title = current.text().split('\n')[0]

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除事项「{title}」吗？\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # 如果有对应的卡片，先关闭
            if event_id in self.sticky_cards:
                self.sticky_cards[event_id].close()
                del self.sticky_cards[event_id]

            self.db.delete_event(event_id)
            self._refresh_event_list()
            # 同步刷新看板
            if hasattr(self, 'kanban_tab'):
                self.kanban_tab.refresh()
            self.statusBar().showMessage(f"🗑️ 已删除事项: {title}", 3000)

    def _show_event_list_context_menu(self, pos):
        """事项列表右键菜单"""
        current = self.event_list.currentItem()
        if not current:
            return

        event_id = current.data(Qt.UserRole)
        if not event_id:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                padding: 6px;
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        edit_action = menu.addAction("✏️ 编辑事项")
        menu.addSeparator()
        copy_action = menu.addAction("📋 复制事件")
        menu.addSeparator()
        delete_action = menu.addAction("🗑 删除事项")

        action = menu.exec_(self.event_list.mapToGlobal(pos))
        if action == edit_action:
            self._edit_event(event_id)
        elif action == copy_action:
            self._duplicate_event(event_id)
        elif action == delete_action:
            self._delete_event()

    def _get_selected_event_ids(self):
        """获取列表中所有选中事项的 ID"""
        ids = []
        for item in self.event_list.selectedItems():
            eid = item.data(Qt.UserRole)
            if eid:
                ids.append(eid)
        return ids

    def _archive_selected_events(self):
        """归档选中的事件"""
        ids = self._get_selected_event_ids()
        if not ids:
            QMessageBox.information(self, "提示", "请先选择要归档的事项（可 Ctrl+点击多选）")
            return

        reply = QMessageBox.question(
            self, "📦 归档确认",
            f"确定要归档选中的 {len(ids)} 个事项吗？\n"
            "归档后可在「归档分析」中查看或恢复。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if reply == QMessageBox.Yes:
            for eid in ids:
                # 暂停计时（如果有）
                self.db.pause_timer(eid)
                # 关闭卡片
                if eid in self.sticky_cards:
                    self.sticky_cards[eid].close()
                    del self.sticky_cards[eid]
                self.db.archive_event(eid)
            self._refresh_event_list()
            self._refresh_archive()
            self.statusBar().showMessage(f"📦 已归档 {len(ids)} 个事项", 3000)

    def _batch_start(self):
        """批量开始计时"""
        ids = self._get_selected_event_ids()
        if not ids:
            QMessageBox.information(self, "提示", "请先选择事项（可 Ctrl+点击多选）")
            return
        for eid in ids:
            self._on_start_timer(eid)
        self.statusBar().showMessage(f"▶ 已开始 {len(ids)} 个事项的计时", 3000)

    def _batch_pause(self):
        """批量暂停计时"""
        ids = self._get_selected_event_ids()
        if not ids:
            QMessageBox.information(self, "提示", "请先选择事项（可 Ctrl+点击多选）")
            return
        for eid in ids:
            self._on_stop_timer(eid)
        self.statusBar().showMessage(f"⏸ 已暂停 {len(ids)} 个事项的计时", 3000)

    def _batch_complete(self):
        """批量完成并归档"""
        ids = self._get_selected_event_ids()
        if not ids:
            QMessageBox.information(self, "提示", "请先选择事项（可 Ctrl+点击多选）")
            return
        reply = QMessageBox.question(
            self, "✓ 批量完成确认",
            f"确定要完成并归档选中的 {len(ids)} 个事项吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            for eid in ids:
                self._on_complete_event(eid)
            self.statusBar().showMessage(f"✓ 已完成并归档 {len(ids)} 个事项", 3000)

    def _refresh_event_list(self):
        """刷新事件列表"""
        self.event_list.clear()
        board_id = self.board_filter_combo.currentData()
        events = self.db.get_all_events(board_id=board_id)

        priority_labels = {
            "high": ("高优先", "#e74c3c", "#fdecea"),
            "medium": ("中优先", "#f39c12", "#fef9e7"),
            "low": ("低优先", "#27ae60", "#eafaf1")
        }
        status_labels = {
            "pending": ("⏳ 待开始", "#95a5a6"),
            "in_progress": ("▶ 进行中", "#27ae60"),
            "completed": ("✅ 已完成", "#3498db")
        }

        for event in events:
            title = event.get('title', '未命名')
            priority = event.get('priority', 'medium')
            status = event.get('status', 'pending')
            planned_start = event.get('planned_start', '')
            duration = event.get('planned_duration_minutes', 30)

            # 格式化时间
            time_display = "未设定"
            if planned_start:
                try:
                    dt = QDateTime.fromString(planned_start, "yyyy-MM-dd HH:mm")
                    time_display = dt.toString("MM/dd HH:mm")
                except Exception:
                    pass

            # 时长格式化
            if duration >= 60:
                h = duration // 60
                m = duration % 60
                duration_text = f"{h}h{m}m" if m > 0 else f"{h}h"
            else:
                duration_text = f"{duration}m"

            # 检查是否有进行中的计时会话（区分"开始"和"继续"）
            is_actively_timing = self.db.get_timer_record(event['id']) is not None

            # 单行表格化布局：状态 | 标题 | 时间 | 时长 | 优先级 | 操作
            item_widget = QWidget()
            item_widget.setStyleSheet("background: transparent;")
            row = QHBoxLayout(item_widget)
            row.setContentsMargins(10, 0, 10, 0)
            row.setSpacing(0)
            row.setAlignment(Qt.AlignVCenter)

            # 状态标签（固定宽度+高度）
            s_text, s_color = status_labels.get(status, ("⏳ 待开始", "#95a5a6"))
            status_label = QLabel(s_text)
            status_label.setFixedSize(70, 22)
            status_label.setAlignment(Qt.AlignCenter)
            status_label.setStyleSheet(
                f"color: white; background-color: {s_color}; "
                f"font-size: 10px; font-weight: bold; border: none; "
                f"border-radius: 10px; padding: 0px 4px; margin: 0px;")
            row.addWidget(status_label)

            # 间隔
            s1 = QLabel(""); s1.setFixedWidth(6); s1.setStyleSheet("border:none;"); row.addWidget(s1)

            # 标题（自动填充宽度，固定高度对齐）
            title_label = QLabel(title)
            title_label.setFixedHeight(22)
            title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            title_label.setStyleSheet(
                "color: #2c3e50; font-size: 12px; font-weight: bold; "
                "border: none; background: transparent; margin: 0px; padding: 0px 4px;")
            title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(title_label, 1)

            # 间隔
            s2 = QLabel(""); s2.setFixedWidth(8); s2.setStyleSheet("border:none;"); row.addWidget(s2)

            # 时间（固定宽度+高度）
            time_label = QLabel(f"📅 {time_display}")
            time_label.setFixedSize(110, 22)
            time_label.setAlignment(Qt.AlignCenter)
            time_label.setStyleSheet(
                "color: #555; font-size: 10px; border: none; background: transparent; margin: 0px; padding: 0px;")
            row.addWidget(time_label)

            # 间隔
            s3 = QLabel(""); s3.setFixedWidth(8); s3.setStyleSheet("border:none;"); row.addWidget(s3)

            # 时长（固定宽度+高度）
            dur_label = QLabel(f"⏱ {duration_text}")
            dur_label.setFixedSize(60, 22)
            dur_label.setAlignment(Qt.AlignCenter)
            dur_label.setStyleSheet(
                "color: #555; font-size: 10px; border: none; background: transparent; margin: 0px; padding: 0px;")
            row.addWidget(dur_label)

            # 间隔
            s4 = QLabel(""); s4.setFixedWidth(8); s4.setStyleSheet("border:none;"); row.addWidget(s4)

            # 优先级标签（固定宽度+高度）
            p_text, p_color, p_bg = priority_labels.get(priority, ("中优先", "#f39c12", "#fef9e7"))
            priority_label = QLabel(p_text)
            priority_label.setFixedSize(56, 22)
            priority_label.setAlignment(Qt.AlignCenter)
            priority_label.setStyleSheet(
                f"color: {p_color}; background-color: {p_bg}; "
                f"font-size: 10px; font-weight: bold; border: none; "
                f"border-radius: 3px; padding: 0px 4px; margin: 0px;")
            row.addWidget(priority_label)

            # 间隔
            s5 = QLabel(""); s5.setFixedWidth(8); s5.setStyleSheet("border:none;"); row.addWidget(s5)

            # 操作按钮区域（固定宽度）
            btn_w = QWidget()
            btn_w.setFixedWidth(120)
            btn_w.setStyleSheet("background: transparent; border: none;")
            btn_l = QHBoxLayout(btn_w)
            btn_l.setContentsMargins(0, 0, 0, 0)
            btn_l.setSpacing(4)
            btn_l.setAlignment(Qt.AlignVCenter)

            if status == "pending":
                # 待开始/已暂停：显示开始或继续按钮
                has_history = self.db.get_total_elapsed_seconds(event['id']) > 0
                if has_history:
                    btn_text = "▶ 继续"
                else:
                    btn_text = "▶ 开始"
                start_btn = QPushButton(btn_text)
                start_btn.setFixedSize(52, 22)
                start_btn.setStyleSheet(
                    "QPushButton{color:#27ae60;background:#eafaf1;border:none;"
                    "border-radius:10px;font-size:10px;font-weight:bold;padding:0 6px;margin:0px;}"
                    "QPushButton:hover{background:#27ae60;color:white;}")
                start_btn.clicked.connect(lambda c, eid=event['id']: self._on_start_timer(eid))
                btn_l.addWidget(start_btn)
            elif status == "in_progress":
                if is_actively_timing:
                    # 正在计时：显示暂停
                    pause_btn = QPushButton("⏸ 暂停")
                    pause_btn.setFixedSize(52, 22)
                    pause_btn.setStyleSheet(
                        "QPushButton{color:#e67e22;background:#fef9e7;border:none;"
                        "border-radius:10px;font-size:10px;font-weight:bold;padding:0 6px;margin:0px;}"
                        "QPushButton:hover{background:#e67e22;color:white;}")
                    pause_btn.clicked.connect(lambda c, eid=event['id']: self._on_stop_timer(eid))
                    btn_l.addWidget(pause_btn)
                else:
                    # 已暂停但状态还是in_progress：显示继续
                    resume_btn = QPushButton("▶ 继续")
                    resume_btn.setFixedSize(52, 22)
                    resume_btn.setStyleSheet(
                        "QPushButton{color:#27ae60;background:#eafaf1;border:none;"
                        "border-radius:10px;font-size:10px;font-weight:bold;padding:0 6px;margin:0px;}"
                        "QPushButton:hover{background:#27ae60;color:white;}")
                    resume_btn.clicked.connect(lambda c, eid=event['id']: self._on_start_timer(eid))
                    btn_l.addWidget(resume_btn)

                done_btn = QPushButton("✓ 完成")
                done_btn.setFixedSize(52, 22)
                done_btn.setStyleSheet(
                    "QPushButton{color:#2980b9;background:#ebf5fb;border:none;"
                    "border-radius:10px;font-size:10px;font-weight:bold;padding:0 6px;margin:0px;}"
                    "QPushButton:hover{background:#2980b9;color:white;}")
                done_btn.clicked.connect(lambda c, eid=event['id']: self._on_complete_event(eid))
                btn_l.addWidget(done_btn)

            row.addWidget(btn_w)

            # 创建 QListWidgetItem
            item = QListWidgetItem(self.event_list)
            item.setSizeHint(QSize(0, 46))
            item.setData(Qt.UserRole, event['id'])
            self.event_list.setItemWidget(item, item_widget)

        self._refresh_card_list()

    def _refresh_card_list(self):
        """刷新卡片列表"""
        self.card_list.clear()
        for event_id, card in self.sticky_cards.items():
            item = QListWidgetItem()
            item.setText(f"📌 {card.event_data.get('title', '未命名')}")
            item.setData(Qt.UserRole, event_id)
            self.card_list.addItem(item)

    # ==================== 卡片操作 ====================

    def _pin_selected_event(self):
        """将选中事件 Pin 到桌面"""
        current = self.event_list.currentItem()
        if not current:
            QMessageBox.information(self, "提示", "请先选择一个事项")
            return

        event_id = current.data(Qt.UserRole)
        self._create_sticky_card(event_id)

    def _create_sticky_card(self, event_id):
        """创建便利贴卡片"""
        if event_id in self.sticky_cards:
            self.sticky_cards[event_id].show()
            self.sticky_cards[event_id].raise_()
            QMessageBox.information(self, "提示", "该事项已在桌面上")
            return

        event_data = self.db.get_event(event_id)
        if not event_data:
            return

        card = StickyNoteCard(event_data)

        # 连接信号
        card.start_timer_signal.connect(self._on_start_timer)
        card.stop_timer_signal.connect(self._on_stop_timer)
        card.complete_signal.connect(self._on_complete_event)
        card.close_signal.connect(self._on_close_card)
        card.position_changed.connect(self._on_card_position_changed)
        card.size_changed.connect(self._on_card_size_changed)

        # 恢复位置和大小
        pos = self.db.get_card_position(event_id)
        if pos:
            card.move(pos['x_position'], pos['y_position'])
            if pos.get('width') and pos.get('height'):
                card.resize(pos['width'], pos['height'])
        else:
            # 默认位置：屏幕右侧
            from PyQt5.QtWidgets import QDesktopWidget
            screen = QDesktopWidget().availableGeometry()
            x = screen.width() - 300
            y = 100 + len(self.sticky_cards) * 240
            card.move(x, y)

        # 如果事件正在进行中，恢复计时状态
        if event_data['status'] == 'in_progress':
            session_info = self.db.get_current_session_info(event_id)
            if session_info:
                card.resume_timing(
                    accumulated_seconds=session_info['accumulated_seconds'],
                    session_start_str=session_info['actual_start']
                )
            else:
                # 没有进行中的会话，但有累计时间（暂停状态）
                total = self.db.get_total_elapsed_seconds(event_id)
                if total > 0:
                    card.resume_timing(accumulated_seconds=total)

        card.show()
        self.sticky_cards[event_id] = card
        self._refresh_card_list()

        # 保存位置
        self.db.save_card_position(event_id, card.x(), card.y())

        self.statusBar().showMessage(
            f"📌 已 Pin: {event_data.get('title', '')}", 3000)

    def _remove_selected_card(self):
        """移除选中的卡片"""
        current = self.card_list.currentItem()
        if not current:
            QMessageBox.information(self, "提示", "请先选择一个卡片")
            return

        event_id = current.data(Qt.UserRole)
        if event_id in self.sticky_cards:
            self.sticky_cards[event_id].close()
            del self.sticky_cards[event_id]
            self.db.remove_card_position(event_id)
            self._refresh_card_list()

    def _show_all_cards(self):
        """显示所有卡片"""
        for card in self.sticky_cards.values():
            card.show()
            card.raise_()

    def _hide_all_cards(self):
        """隐藏所有卡片"""
        for card in self.sticky_cards.values():
            card.hide()

    def _on_close_card(self, event_id):
        """关闭卡片"""
        if event_id in self.sticky_cards:
            self.sticky_cards[event_id].close()
            del self.sticky_cards[event_id]
            self.db.remove_card_position(event_id)
            self._refresh_card_list()

    def _on_card_position_changed(self, event_id, x, y):
        """卡片位置变化"""
        pos = self.db.get_card_position(event_id)
        w = pos['width'] if pos else 280
        h = pos['height'] if pos else 220
        self.db.save_card_position(event_id, x, y, w, h)

    def _on_card_size_changed(self, event_id, w, h):
        """卡片大小变化"""
        pos = self.db.get_card_position(event_id)
        x = pos['x_position'] if pos else 100
        y = pos['y_position'] if pos else 100
        self.db.save_card_position(event_id, x, y, w, h)

    # ==================== 计时操作 ====================

    def _calc_sleep_minutes(self, start_dt, end_dt):
        """
        计算两个时间点之间的睡眠时间（分钟）
        睡眠时段：每天 23:00 ~ 08:00（8小时）
        """
        from datetime import datetime, timedelta

        SLEEP_START = 23  # 23:00
        SLEEP_END = 8     # 08:00

        total_sleep = 0
        current = start_dt.replace(second=0, microsecond=0)

        while current < end_dt:
            hour = current.hour
            if hour >= SLEEP_START:
                # 进入睡眠时段，计算到午夜的时间
                tonight_end = current.replace(hour=23, minute=59, second=59)
                if end_dt <= tonight_end:
                    total_sleep += (end_dt - current).total_seconds() / 60
                    break
                else:
                    # 到午夜
                    midnight = current.replace(hour=23, minute=59, second=59)
                    total_sleep += (midnight - current).total_seconds() / 60 + 1
                    # 跳到第二天 00:00
                    current = (current + timedelta(days=1)).replace(hour=0, minute=0)
            elif hour < SLEEP_END:
                # 在早晨睡眠时段内
                morning_end = current.replace(hour=SLEEP_END, minute=0)
                if end_dt <= morning_end:
                    total_sleep += (end_dt - current).total_seconds() / 60
                    break
                else:
                    total_sleep += (morning_end - current).total_seconds() / 60
                    current = morning_end
            else:
                # 非睡眠时段，跳到当天 23:00
                tonight_start = current.replace(hour=SLEEP_START, minute=0)
                if end_dt <= tonight_start:
                    break
                current = tonight_start

        return int(total_sleep)

    def _on_start_timer(self, event_id):
        """开始/恢复计时"""
        timer_record = self.db.get_timer_record(event_id)

        if timer_record:
            # 已有进行中的会话（恢复计时）- 不需要操作数据库
            pass
        else:
            # 没有进行中的会话
            total = self.db.get_total_elapsed_seconds(event_id)

            if total > 0:
                # 之前暂停过，创建新会话继续
                self.db.resume_timer(event_id)
            else:
                # 首次开始 - 检查迟到补偿
                event_data = self.db.get_event(event_id)
                if event_data and event_data.get('planned_start'):
                    from datetime import datetime
                    try:
                        planned = datetime.strptime(
                            event_data['planned_start'], "%Y-%m-%d %H:%M")
                        now = datetime.now()
                        diff_minutes = (now - planned).total_seconds() / 60

                        if diff_minutes > 5:
                            diff_int = int(diff_minutes)

                            # 计算有效工作时长（扣除睡眠时间 23:00~08:00）
                            from datetime import datetime, timedelta
                            planned_dt = datetime.strptime(
                                event_data['planned_start'], "%Y-%m-%d %H:%M")
                            now_dt = datetime.now()
                            sleep_minutes = self._calc_sleep_minutes(
                                planned_dt, now_dt)
                            effective_minutes = diff_int - sleep_minutes
                            if effective_minutes < 0:
                                effective_minutes = 0

                            sleep_str = ""
                            if sleep_minutes > 0:
                                sleep_str = (
                                    f"\n（已扣除睡眠时间 {sleep_minutes // 60}小时"
                                    f"{sleep_minutes % 60}分钟）")

                            reply = QMessageBox.question(
                                self, "⏰ 迟到补偿",
                                f"计划开始时间: {event_data['planned_start']}\n"
                                f"当前时间: {now_dt.strftime('%H:%M')}\n"
                                f"迟到间隔: {diff_int} 分钟\n"
                                f"有效工作时长: {effective_minutes} 分钟"
                                f"{sleep_str}\n\n"
                                f"是否将有效工作时长计入实际耗时？",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

                            if reply == QMessageBox.Yes:
                                offset = effective_minutes * 60
                                self.db.start_timer(event_id, manual_offset_seconds=offset)
                                self.db.update_event(event_id, actual_start_at=event_data['planned_start'])
                            else:
                                self.db.start_timer(event_id)
                                # 不计入 → 实际开始时间 = 当前时间
                                from datetime import datetime
                                self.db.update_event(event_id, actual_start_at=now.strftime("%Y-%m-%d %H:%M"))
                        else:
                            self.db.start_timer(event_id)
                    except (ValueError, TypeError):
                        self.db.start_timer(event_id)
                        self.db.update_event(event_id, actual_start_at=now.strftime("%Y-%m-%d %H:%M"))
                else:
                    self.db.start_timer(event_id)
                    self.db.update_event(event_id, actual_start_at=datetime.now().strftime("%Y-%m-%d %H:%M"))

        self._refresh_event_list()

        # 同步卡片状态
        if event_id in self.sticky_cards:
            card = self.sticky_cards[event_id]
            card.sync_start()
            # 同步迟到补偿的累计时间到卡片显示
            session_info = self.db.get_current_session_info(event_id)
            if session_info and session_info['accumulated_seconds'] > 0:
                card.accumulated_seconds = session_info['accumulated_seconds']

        # 首次开始时，同步事项状态 pending → in_progress
        event_data = self.db.get_event(event_id)
        if event_data and event_data['status'] == 'pending':
            self.db.update_event(event_id, status='in_progress')
            # 状态变更，移动到对应甬道
            if hasattr(self, 'kanban_tab'):
                self.kanban_tab.move_event_to_status_lane(event_id, 'in_progress')

    def _on_stop_timer(self, event_id):
        """暂停计时"""
        self.db.pause_timer(event_id)
        self._refresh_event_list()
        # 同步卡片状态
        if event_id in self.sticky_cards:
            self.sticky_cards[event_id].sync_pause()

    def _on_complete_event(self, event_id):
        """完成事件"""
        total_seconds = self.db.stop_timer(event_id)
        event_data = self.db.get_event(event_id)
        session_count = self.db.get_session_count(event_id)

        if event_data and total_seconds > 0:
            planned = event_data.get('planned_duration_minutes', 0)
            actual = round(total_seconds / 60, 1)
            diff = planned - actual

            if diff > 0:
                msg = f"🎉 太棒了！提前 {diff:.1f} 分钟完成！\n\n"
            elif diff < 0:
                msg = f"⚠️ 超时 {abs(diff):.1f} 分钟\n\n"
            else:
                msg = f"🎉 刚好按时完成！\n\n"

            msg += f"计划时长: {planned} 分钟\n"
            msg += f"实际时长: {actual} 分钟\n"
            msg += f"计时会话: {session_count} 次"

            if session_count > 1:
                hours = int(total_seconds // 3600)
                mins = int((total_seconds % 3600) // 60)
                msg += f"\n(跨多次会话累计)"

            # 更新卡片显示
            if event_id in self.sticky_cards:
                card = self.sticky_cards[event_id]
                card.show_completion_summary(planned, total_seconds)

                # 5秒后自动关闭卡片
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(5000, lambda: self._on_close_card(event_id))

            QMessageBox.information(self, "✅ 事项完成", msg)

        # 更新事项状态为 completed（不直接归档）
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.db.update_event(event_id, status='completed', completed_at=now_str)
        self._refresh_event_list()
        # 将已完成事件移到对应甬道
        if hasattr(self, 'kanban_tab'):
            self.kanban_tab.move_event_to_status_lane(event_id, 'completed')

    # ==================== 通知检查 ====================

    def _check_notifications(self):
        """检查是否需要发送通知"""
        # 检查所有 pending 状态的事件（包括已过开始时间的）
        all_pending = self.db.get_all_events(status="pending")
        self.notification_mgr.check_and_notify(
            all_pending,
            callback=self._on_event_notification
        )

    def _on_event_notification(self, event):
        """收到事件通知的回调"""
        event_id = event['id']

        # 如果卡片已经在桌面上，不再弹窗
        if event_id in self.sticky_cards:
            return

        reply = QMessageBox.question(
            self, "📋 事项提醒",
            f"「{event.get('title', '未命名')}」已到达计划开始时间！\n"
            f"计划时间: {event.get('planned_start', '')}\n\n"
            f"是否将其 Pin 到桌面？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if reply == QMessageBox.Yes:
            self._create_sticky_card(event_id)
            self.tabs.setCurrentIndex(1)

    # ==================== 归档分析 ====================

    def _show_archive(self):
        """显示归档分析"""
        self.tabs.setCurrentIndex(2)
        self._refresh_archive()

    def _refresh_archive(self):
        """刷新归档数据"""
        stats = self.db.get_time_diff_stats()

        if not stats:
            self.archive_table.setRowCount(0)
            self.total_label.setText("已完成: 0")
            self.avg_diff_label.setText("平均偏差: 0 小时")
            self.accuracy_label.setText("准时率: 0%")
            return

        self.archive_table.setRowCount(len(stats))

        total_diff = 0
        on_time_count = 0
        priority_map = {"high": "🔴 高", "medium": "🟡 中", "low": "🟢 低"}
        status_map = {"archived": "已归档", "completed": "已完成"}

        # 获取看板名称映射
        boards = self.db.get_boards()
        board_map = {b['id']: b['name'] for b in boards}

        for i, stat in enumerate(stats):
            planned_min = stat.get('planned_duration_minutes', 0)
            actual_min = round(stat.get('actual_minutes', 0), 1)
            diff_min = round(stat.get('diff_minutes', 0), 1)

            # 按小时显示（保留1位小数）
            planned_h = round(planned_min / 60, 1)
            actual_h = round(actual_min / 60, 1)
            diff_h = round(diff_min / 60, 1)

            if abs(diff_min) <= 5:
                on_time_count += 1

            total_diff += diff_min

            # 事项名称
            item0 = QTableWidgetItem(stat.get('title', '未命名'))
            item0.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.archive_table.setItem(i, 0, item0)

            # 归属看板
            board_id = stat.get('board_id')
            board_name = board_map.get(board_id, "未分配") if board_id else "未分配"
            item1 = QTableWidgetItem(board_name)
            item1.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.archive_table.setItem(i, 1, item1)

            # 计划时长（小时）
            item2 = QTableWidgetItem(f"{planned_h}h")
            item2.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.archive_table.setItem(i, 2, item2)

            # 实际时长（小时）
            item3 = QTableWidgetItem(f"{actual_h}h")
            item3.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.archive_table.setItem(i, 3, item3)

            # 偏差（小时）
            diff_item = QTableWidgetItem(
                f"{'+' if diff_h > 0 else ''}{diff_h}h")
            diff_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            if diff_h > 0:
                diff_item.setForeground(QColor("#27ae60"))
            elif diff_h < 0:
                diff_item.setForeground(QColor("#e74c3c"))
            else:
                diff_item.setForeground(QColor("#2980b9"))
            self.archive_table.setItem(i, 4, diff_item)

            # 准时率
            if planned_min > 0:
                rate = min(actual_min / planned_min * 100, 999)
                rate_text = f"{rate:.0f}%"
            else:
                rate_text = "N/A"
            item5 = QTableWidgetItem(rate_text)
            item5.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.archive_table.setItem(i, 5, item5)

            # 实际开始时间
            actual_start = stat.get('actual_start_at', '')
            if actual_start:
                try:
                    from datetime import datetime
                    dt = datetime.strptime(actual_start, "%Y-%m-%d %H:%M")
                    start_text = dt.strftime("%Y/%m/%d %H:%M")
                except Exception:
                    start_text = actual_start or "未记录"
            else:
                start_text = "未记录"
            start_item = QTableWidgetItem(start_text)
            start_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            if start_text == "未记录":
                start_item.setForeground(QColor("#bdc3c7"))
            self.archive_table.setItem(i, 6, start_item)

            # 完成日期
            completed_at = stat.get('completed_at', '')
            if completed_at:
                try:
                    from datetime import datetime
                    dt = datetime.strptime(completed_at, "%Y-%m-%d %H:%M")
                    completed_text = dt.strftime("%Y/%m/%d %H:%M")
                except Exception:
                    completed_text = completed_at or "未记录"
            else:
                completed_text = "未记录"
            completed_item = QTableWidgetItem(completed_text)
            completed_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            if completed_text == "未记录":
                completed_item.setForeground(QColor("#bdc3c7"))
            self.archive_table.setItem(i, 7, completed_item)

            # 优先级
            item8 = QTableWidgetItem(
                priority_map.get(stat.get('priority', 'medium'), '🟡 中'))
            item8.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.archive_table.setItem(i, 8, item8)

            # 状态
            item9 = QTableWidgetItem(
                status_map.get(stat.get('status', ''), stat.get('status', '')))
            item9.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.archive_table.setItem(i, 9, item9)

            # 备注（显示前20个字符）
            note = stat.get('archive_note', '') or ''
            note_display = note[:20] + '...' if len(note) > 20 else note
            note_item = QTableWidgetItem(note_display)
            note_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if not note:
                note_item.setForeground(QColor("#bdc3c7"))
            self.archive_table.setItem(i, 10, note_item)

            # 存储事件 ID 到第0列的 data
            self.archive_table.item(i, 0).setData(Qt.UserRole, stat.get('id'))

        # 更新统计
        total = len(stats)
        avg_diff_h = round(total_diff / total / 60, 1) if total > 0 else 0
        accuracy = round(on_time_count / total * 100, 1) if total > 0 else 0

        self.total_label.setText(f"已完成: {total} 项")
        self.avg_diff_label.setText(
            f"平均偏差: {'+' if avg_diff_h > 0 else ''}{avg_diff_h} 小时")
        self.accuracy_label.setText(f"准时率(±5分钟): {accuracy}%")

    def _on_archive_double_click(self, index):
        """双击归档表格 - 弹出详情卡片"""
        try:
            row = index.row()
            item = self.archive_table.item(row, 0)
            if not item:
                return
            event_id = item.data(Qt.UserRole)
            if not event_id:
                return

            # 从表格获取当前数据（安全获取，防止 None）
            def safe_text(col):
                it = self.archive_table.item(row, col)
                return it.text() if it else ""

            title = safe_text(0)
            board_name = safe_text(1)
            planned = safe_text(2)
            actual = safe_text(3)
            diff = safe_text(4)
            rate = safe_text(5)
            actual_start = safe_text(6)
            completed = safe_text(7)
            priority = safe_text(8)
            status = safe_text(9)
            note = safe_text(10)

            # 获取完整备注
            event_data = self.db.get_event(event_id)
            full_note = event_data.get('archive_note', '') if event_data else ''

            # 弹出详情卡片
            dialog = QDialog(self)
            dialog.setWindowTitle(f"归档详情 - {title}")
            dialog.setFixedSize(460, 520)
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(28, 24, 28, 24)
            layout.setSpacing(14)

            # 标题
            title_label = QLabel(title)
            title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
            title_label.setStyleSheet("color: #2c3e50;")
            title_label.setWordWrap(True)
            layout.addWidget(title_label)

            # 分隔线
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("color: #ecf0f1;")
            layout.addWidget(sep)

            # 信息网格
            info_grid = QGridLayout()
            info_grid.setHorizontalSpacing(12)
            info_grid.setVerticalSpacing(10)

            def add_info_row(row_idx, label, value):
                lbl = QLabel(label)
                lbl.setFont(QFont("Microsoft YaHei", 10))
                lbl.setStyleSheet("color: #7f8c8d;")
                val = QLabel(value)
                val.setFont(QFont("Microsoft YaHei", 10))
                val.setStyleSheet("color: #2c3e50;")
                val.setWordWrap(True)
                info_grid.addWidget(lbl, row_idx, 0, Qt.AlignLeft | Qt.AlignVCenter)
                info_grid.addWidget(val, row_idx, 1, Qt.AlignLeft | Qt.AlignVCenter)

            add_info_row(0, "归属看板:", board_name)
            add_info_row(1, "优先级:", priority)
            add_info_row(2, "状态:", status)
            add_info_row(3, "计划时长:", planned)
            add_info_row(4, "实际时长:", actual)
            add_info_row(5, "偏差:", diff)
            add_info_row(6, "准时率:", rate)
            add_info_row(7, "实际开始:", actual_start)

            layout.addLayout(info_grid)

            # 完成日期编辑
            date_layout = QHBoxLayout()
            date_label = QLabel("完成日期:")
            date_label.setFont(QFont("Microsoft YaHei", 10))
            date_label.setStyleSheet("color: #7f8c8d;")
            date_layout.addWidget(date_label)

            dt_edit = QDateTimeEdit()
            dt_edit.setCalendarPopup(True)
            dt_edit.setDisplayFormat("yyyy/MM/dd HH:mm")
            dt_edit.setFixedWidth(160)
            if completed and completed != "未记录":
                try:
                    dt = QDateTime.fromString(completed, "yyyy/MM/dd HH:mm")
                    dt_edit.setDateTime(dt)
                except Exception:
                    dt_edit.setDateTime(QDateTime.currentDateTime())
            else:
                dt_edit.setDateTime(QDateTime.currentDateTime())
            date_layout.addWidget(dt_edit)
            date_layout.addStretch()
            layout.addLayout(date_layout)

            # 备注编辑
            note_label = QLabel("归档备注:")
            note_label.setFont(QFont("Microsoft YaHei", 10))
            note_label.setStyleSheet("color: #7f8c8d;")
            layout.addWidget(note_label)

            note_edit = QTextEdit()
            note_edit.setPlaceholderText("填写归档说明（如：无疾而终、需求取消等）")
            note_edit.setPlainText(full_note)
            note_edit.setMaximumHeight(80)
            note_edit.setStyleSheet("""
                QTextEdit {
                    background-color: #f8f9fa;
                    border: 1px solid #dcdde1;
                    border-radius: 6px;
                    padding: 8px;
                    font-family: "Microsoft YaHei";
                    font-size: 11px;
                }
                QTextEdit:focus {
                    border-color: #3498db;
                }
            """)
            layout.addWidget(note_edit)

            # 按钮
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(12)

            cancel_btn = QPushButton("取消")
            cancel_btn.setFont(QFont("Microsoft YaHei", 10))
            cancel_btn.setFixedHeight(34)
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #555;
                    border: 1px solid #dcdde1;
                    border-radius: 6px;
                    padding: 0 20px;
                }
                QPushButton:hover {
                    background-color: #f0f4f8;
                }
            """)
            cancel_btn.clicked.connect(dialog.reject)
            btn_layout.addWidget(cancel_btn)

            save_btn = QPushButton("保存")
            save_btn.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
            save_btn.setFixedHeight(34)
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 0 24px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            save_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(save_btn)

            layout.addLayout(btn_layout)

            if dialog.exec_() == QDialog.Accepted:
                new_dt = dt_edit.dateTime().toString("yyyy-MM-dd HH:mm")
                new_note = note_edit.toPlainText()
                self.db.update_event_completed_at(event_id, new_dt)
                self.db.update_event_archive_note(event_id, new_note)
                self._refresh_archive()
                self.statusBar().showMessage("✅ 已更新归档信息", 3000)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.statusBar().showMessage(f"❌ 打开详情失败: {e}", 0)

    def _get_selected_archive_ids(self):
        """获取归档表格中选中的事件 ID 列表"""
        ids = []
        for row in self.archive_table.selectionModel().selectedRows():
            item = self.archive_table.item(row.row(), 0)
            if item:
                eid = item.data(Qt.UserRole)
                if eid:
                    ids.append(eid)
        return ids

    def _restore_selected_archive(self):
        """将选中的归档事件恢复到事项列表"""
        ids = self._get_selected_archive_ids()
        if not ids:
            QMessageBox.warning(self, "提示", "请先在表格中选择要恢复的事件")
            return

        reply = QMessageBox.question(
            self, "↩️ 恢复确认",
            f"确定要将选中的 {len(ids)} 个事件恢复到事项列表吗？\n"
            "恢复后状态将变为「待开始」。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if reply == QMessageBox.Yes:
            for eid in ids:
                self.db.update_event(eid, status="pending")
            self._refresh_archive()
            self._refresh_event_list()
            QMessageBox.information(self, "恢复成功",
                f"已将 {len(ids)} 个事件恢复到事项列表。")

    def _delete_selected_archive(self):
        """删除选中的归档事件"""
        ids = self._get_selected_archive_ids()
        if not ids:
            QMessageBox.warning(self, "提示", "请先在表格中选择要删除的事件")
            return

        reply = QMessageBox.question(
            self, "🗑️ 删除确认",
            f"确定要永久删除选中的 {len(ids)} 个事件吗？\n"
            "此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            for eid in ids:
                self.db.delete_event(eid)
            self._refresh_archive()
            QMessageBox.information(self, "删除成功",
                f"已删除 {len(ids)} 个事件。")

    def _on_kanban_edit_event(self, event_id):
        """看板中双击卡片编辑事件"""
        event_data = self.db.get_event(event_id)
        if not event_data:
            return
        dialog = EventDialog(self, event_data, db=self.db, default_board_id=self.kanban_tab.current_board_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['title']:
                QMessageBox.warning(self, "提示", "请输入事项标题！")
                return
            self.db.update_event(event_id, **data)
            if data.get('planned_start') != event_data.get('planned_start'):
                self.notification_mgr.reset_notification(event_id)
            self._refresh_event_list()
            self.kanban_tab.refresh()
            self.statusBar().showMessage(f"✅ 已更新事项: {data['title']}", 3000)

    def _on_kanban_status_changed(self):
        """看板拖拽导致状态变更，刷新事项列表"""
        self._refresh_event_list()

    def _on_kanban_create_event(self, board_id):
        """看板中新建事件"""
        dialog = EventDialog(self, db=self.db, default_board_id=board_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['title']:
                QMessageBox.warning(self, "提示", "请输入事项标题！")
                return
            event_id = self.db.add_event(
                data['title'], data.get('description', ''),
                data.get('planned_start'), data.get('planned_duration_minutes', 30),
                data.get('priority', 'medium'), data.get('color', '#FFF9C4'),
                board_id=data.get('board_id'))
            if data.get('planned_start'):
                self.notification_mgr.reset_notification(event_id)
            self._refresh_event_list()
            if hasattr(self.kanban_tab, 'current_board_id') and self.kanban_tab.current_board_id:
                self.kanban_tab.refresh()
            self.statusBar().showMessage(f"✅ 已创建事项: {data['title']}", 3000)

    # ==================== 标签页切换 ====================

    def _on_tab_changed(self, index):
        """标签页切换时刷新对应数据"""
        # 获取甘特图标签的索引
        for i in range(self.tabs.count()):
            if self.tabs.widget(i) is self.gantt_tab:
                if index == i:
                    self.gantt_tab.load_boards()
                break

    # ==================== 状态更新 ====================

    def _update_status(self):
        """更新状态栏"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        active_count = len(self.sticky_cards)
        timing_count = sum(1 for c in self.sticky_cards.values() if c.is_timing)
        self.statusBar().showMessage(
            f"🕐 {now}  |  📌 桌面卡片: {active_count}  |  ▶️ 计时中: {timing_count}")

        # 休息提醒检测
        if self._rest_reminder_active:
            return  # 休息提醒正在显示，不重复触发

        if not self.db.get_setting('rest_reminder_enabled', False):
            return  # 休息提醒未开启

        # 遍历所有正在计时的卡片，检查是否达到休息间隔
        interval_seconds = int(self.db.get_setting('rest_interval_minutes', 120)) * 60
        for event_id, card in self.sticky_cards.items():
            if not card.is_timing:
                continue
            elapsed = self.db.get_total_elapsed_seconds(event_id)
            # 计算应该触发休息的次数
            expected_triggers = int(elapsed // interval_seconds)
            actual_triggers = self._last_rest_trigger_time.get(event_id, 0)
            if expected_triggers > actual_triggers:
                self._last_rest_trigger_time[event_id] = expected_triggers
                self._trigger_rest_reminder(event_id)
                break

    def _trigger_rest_reminder(self, event_id):
        """触发休息提醒"""
        self._rest_reminder_active = True
        self._rest_reminder_event_id = event_id

        # 暂停计时
        try:
            self._on_stop_timer(event_id)
        except Exception:
            pass

        # 弹出休息提醒对话框（模态，确保可见）
        rest_duration = int(self.db.get_setting('rest_duration_minutes', 10))
        custom_bg = self.db.get_setting('rest_bg_image_path', '')
        try:
            self._rest_dialog = RestReminderDialog(
                rest_duration, custom_bg_path=custom_bg, parent=self)
            self._rest_dialog.rest_finished.connect(
                lambda: self._on_rest_finished(event_id)
            )
            self._rest_dialog.exec_()
        except Exception as e:
            print(f"[休息提醒] 显示对话框出错: {e}")

    def _on_rest_finished(self, event_id):
        """休息结束，恢复计时"""
        self._rest_reminder_active = False
        self._rest_reminder_event_id = None

        # 恢复计时
        self._on_start_timer(event_id)

    # ==================== 系统托盘 ====================

    def _tray_activated(self, reason):
        """托盘图标激活"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def _quit_app(self):
        """退出应用"""
        # 关闭所有卡片
        for card in self.sticky_cards.values():
            card.close()
        self.db.close()
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """关闭事件 - 最小化到托盘"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "桌面便利贴",
            "程序已最小化到系统托盘，双击图标可重新打开。",
            QSystemTrayIcon.Information,
            2000
        )


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

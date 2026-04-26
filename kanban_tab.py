"""
看板标签页 - 支持多看板，水平滚动甬道，支持拖拽卡片
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# ==================== 看板事件卡片 ====================

class KanbanCard(QFrame):
    """看板事件卡片 - 可拖拽"""

    event_edit_requested = pyqtSignal(int)
    pin_to_desktop = pyqtSignal(int)  # Pin到桌面信号

    PRIORITY_COLORS = {
        "high": "#e74c3c",
        "medium": "#f39c12",
        "low": "#27ae60",
    }

    def __init__(self, event_data, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.event_id = event_data['id']
        self.setMinimumHeight(60)
        self.setCursor(Qt.OpenHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_card_context_menu)
        self._drag_start_pos = None

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧优先级色条
        self.priority_bar = QFrame()
        self.priority_bar.setFixedWidth(5)
        priority = self.event_data.get('priority', 'medium')
        color = self.PRIORITY_COLORS.get(priority, self.PRIORITY_COLORS['medium'])
        self.priority_bar.setStyleSheet(
            f"background-color: {color}; border: none; border-radius: 2px;"
        )
        main_layout.addWidget(self.priority_bar)

        # 内容区域
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 8, 10, 8)
        content_layout.setSpacing(4)

        # 标题
        self.title_label = QLabel(self.event_data.get('title', '未命名'))
        self.title_label.setWordWrap(True)
        self.title_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.title_label.setStyleSheet("color: #2c3e50; background: transparent; border: none;")
        content_layout.addWidget(self.title_label)

        # 计划时间
        duration = self.event_data.get('planned_duration_minutes', 30)
        planned_start = self.event_data.get('planned_start', '')
        if planned_start:
            try:
                dt = QDateTime.fromString(planned_start, "yyyy-MM-dd HH:mm")
                time_str = dt.toString("HH:mm")
                date_str = dt.toString("MM/dd")
                time_text = f"{date_str} {time_str} | {duration}分钟"
            except Exception:
                time_text = f"计划 {duration} 分钟"
        else:
            time_text = f"计划 {duration} 分钟"

        self.time_label = QLabel(time_text)
        self.time_label.setFont(QFont("Microsoft YaHei", 9))
        self.time_label.setStyleSheet("color: #7f8c8d; background: transparent; border: none;")
        content_layout.addWidget(self.time_label)

        main_layout.addWidget(content, 1)

    def _apply_style(self):
        self.setStyleSheet("""
            KanbanCard {
                background-color: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 6px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(4)
        shadow.setOffset(1, 1)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)

    def apply_zoom(self, zoom_level):
        """缩放卡片内的字体和间距"""
        title_size = max(int(11 * zoom_level), 6)
        self.title_label.setFont(QFont("Microsoft YaHei", title_size, QFont.Bold))
        time_size = max(int(9 * zoom_level), 5)
        self.time_label.setFont(QFont("Microsoft YaHei", time_size))
        # 调整内容区域间距
        margin = max(int(10 * zoom_level), 4)
        spacing = max(int(4 * zoom_level), 2)
        # 找到 content widget 的 layout
        for child in self.findChildren(QWidget):
            if child.objectName() == "" and child.layout() and child != self:
                child.layout().setContentsMargins(margin, int(8 * zoom_level), margin, int(8 * zoom_level))
                child.layout().setSpacing(spacing)
                break

    def enterEvent(self, event):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setOffset(2, 2)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(shadow)
        self.setCursor(Qt.OpenHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(4)
        shadow.setOffset(1, 1)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is None:
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
        # 触发拖拽
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self.event_id))
        drag.setMimeData(mime_data)
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.exec_(Qt.MoveAction)
        self._drag_start_pos = None

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def _show_card_context_menu(self, pos):
        """卡片右键菜单"""
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
        pin_action = menu.addAction("📌 Pin 到桌面")

        action = menu.exec_(self.mapToGlobal(pos))
        if action == edit_action:
            self.event_edit_requested.emit(self.event_id)
        elif action == pin_action:
            self.pin_to_desktop.emit(self.event_id)

    def mouseDoubleClickEvent(self, event):
        self.event_edit_requested.emit(self.event_id)
        super().mouseDoubleClickEvent(event)


# ==================== 看板甬道 ====================

class KanbanLane(QWidget):
    """看板甬道 - 包含标题和卡片列表，接受拖放"""

    pin_to_desktop = pyqtSignal(int)  # 转发卡片Pin信号

    def __init__(self, lane_data, db, board_id, parent=None):
        super().__init__(parent)
        self.lane_data = lane_data
        self.lane_id = lane_data['id']
        self.lane_name = lane_data['name']
        self.lane_color = lane_data.get('color', '#ecf0f1')
        self.db = db
        self.board_id = board_id
        self.setAcceptDrops(True)
        self.setFixedWidth(280)

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 甬道容器
        self.container = QFrame()
        self.container.setObjectName("laneContainer")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 甬道标题栏
        self.header = QFrame()
        self.header.setObjectName("laneHeader")
        self.header.setFixedHeight(40)
        self.header.setCursor(Qt.PointingHandCursor)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        self.header_label = QLabel(self.lane_name)
        self.header_label.setObjectName("titleLabel")
        self.header_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()

        # 卡片数量标签
        self.count_label = QLabel("0")
        self.count_label.setObjectName("countLabel")
        self.count_label.setFont(QFont("Microsoft YaHei", 9))
        header_layout.addWidget(self.count_label)

        container_layout.addWidget(self.header)

        # 卡片滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #cccccc;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(8, 8, 8, 8)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        container_layout.addWidget(self.scroll_area, 1)

        main_layout.addWidget(self.container)

        # 右键菜单
        self.header.setContextMenuPolicy(Qt.CustomContextMenu)
        self.header.customContextMenuRequested.connect(self._show_context_menu)

    def _apply_style(self):
        shadow = QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(6)
        shadow.setOffset(1, 2)
        shadow.setColor(QColor(0, 0, 0, 25))
        self.container.setGraphicsEffect(shadow)

    def apply_zoom(self, zoom_level):
        """缩放甬道内的字体和间距"""
        # 标题字体
        header_size = max(int(12 * zoom_level), 7)
        self.header_label.setFont(QFont("Microsoft YaHei", header_size, QFont.Bold))
        # 计数标签
        count_size = max(int(9 * zoom_level), 6)
        self.count_label.setFont(QFont("Microsoft YaHei", count_size))
        # 标题栏高度
        self.header.setFixedHeight(int(40 * zoom_level))
        # 卡片间距
        card_spacing = max(int(8 * zoom_level), 4)
        self.cards_layout.setSpacing(card_spacing)
        self.cards_layout.setContentsMargins(
            int(8 * zoom_level), int(8 * zoom_level),
            int(8 * zoom_level), int(8 * zoom_level))
        # 缩放每个卡片
        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), KanbanCard):
                item.widget().apply_zoom(zoom_level)
        self._update_header_color()

    def _update_header_color(self):
        color = self.lane_color
        r = int(color[1:3], 16) if len(color) >= 7 else 200
        g = int(color[3:5], 16) if len(color) >= 7 else 200
        b = int(color[5:7], 16) if len(color) >= 7 else 200
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = "#ffffff" if brightness < 160 else "#2c3e50"
        count_bg = "rgba(255,255,255,0.2)" if brightness < 160 else "rgba(0,0,0,0.08)"
        count_color = "rgba(255,255,255,0.8)" if brightness < 160 else "rgba(0,0,0,0.5)"

        # 统一设置 container 的样式（包含 header 和 label），避免样式被覆盖
        self.container.setStyleSheet(f"""
            #laneContainer {{
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
            }}
            #laneHeader {{
                background-color: {color};
                border: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            #titleLabel {{
                color: {text_color};
                background: transparent;
                border: none;
                padding: 2px;
            }}
            #countLabel {{
                color: {count_color};
                background: {count_bg};
                border: none;
                border-radius: 10px;
                padding: 1px 8px;
            }}
        """)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 4px;
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

        rename_action = menu.addAction("重命名甬道")
        delete_action = menu.addAction("删除甬道")

        action = menu.exec_(self.header.mapToGlobal(pos))
        if action == rename_action:
            self._rename_lane()
        elif action == delete_action:
            self._delete_lane()

    def _rename_lane(self):
        new_name, ok = QInputDialog.getText(
            self, "重命名甬道", "请输入新名称：",
            text=self.lane_name
        )
        if ok and new_name.strip():
            self.db.update_kanban_lane(self.lane_id, name=new_name.strip())
            parent = self.parent()
            while parent and not isinstance(parent, KanbanTab):
                parent = parent.parent()
            if parent:
                parent.refresh()

    def _delete_lane(self):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除甬道「{self.lane_name}」吗？\n甬道中的卡片不会被删除，但会从甬道中移出。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_kanban_lane(self.lane_id)
            parent = self.parent()
            while parent and not isinstance(parent, KanbanTab):
                parent = parent.parent()
            if parent:
                parent.refresh()

    def load_cards(self, event_edit_callback):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        events = self.db.get_lane_events(self.lane_id)
        for event in events:
            card = KanbanCard(event, self)
            card.event_edit_requested.connect(event_edit_callback)
            card.pin_to_desktop.connect(self.pin_to_desktop.emit)
            self.cards_layout.addWidget(card)

        self.count_label.setText(str(len(events)))
        self.cards_layout.addStretch()

    # ---- 拖放 ----

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            event_id = int(event.mimeData().text())
            self.db.move_event_to_lane(event_id, self.lane_id)
            event.acceptProposedAction()

            # 同步更新事项状态：根据目标甬道位置
            self._sync_event_status(event_id)

            parent = self.parent()
            while parent and not isinstance(parent, KanbanTab):
                parent = parent.parent()
            if parent:
                parent.refresh()
                parent.event_status_changed.emit()
        else:
            event.ignore()

    def _sync_event_status(self, event_id):
        """根据甬道位置同步事项状态
        甬道1 -> pending
        甬道2~N-1 -> in_progress
        甬道N（最后一个）-> completed
        """
        lanes = self.db.get_kanban_lanes(self.board_id)
        if not lanes:
            return

        lane_ids = [l['id'] for l in lanes]
        lane_count = len(lane_ids)
        pos = lane_ids.index(self.lane_id) if self.lane_id in lane_ids else 0

        if pos == 0:
            new_status = "pending"
        elif pos == lane_count - 1:
            new_status = "completed"
        elif pos >= lane_count:
            new_status = "archived"
        else:
            new_status = "in_progress"

        event = self.db.get_event(event_id)
        if event and event['status'] != new_status:
            self.db.update_event(event_id, status=new_status)


# ==================== 模板选择对话框 ====================

class TemplateSelectDialog(QDialog):
    """模板选择对话框（仅显示预设模板）"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.selected_template = None
        self.setWindowTitle("选择看板模板")
        self.setFixedSize(460, 380)
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        # 标题
        title = QLabel("选择看板模板")
        title.setFont(QFont("Microsoft YaHei", 15, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; background: transparent; border: none;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("选择一个预设模板来快速初始化看板甬道")
        desc.setFont(QFont("Microsoft YaHei", 10))
        desc.setStyleSheet("color: #7f8c8d; background: transparent; border: none;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(8)

        # 模板列表（用卡片式布局）
        self.template_group = QButtonGroup(self)
        self.template_buttons = {}

        for template_name in self.db.KANBAN_TEMPLATES:
            lanes = self.db.KANBAN_TEMPLATES[template_name]
            lane_desc = "、".join([name for name, _ in lanes])

            # 模板卡片容器
            card = QFrame()
            card.setObjectName("templateCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(6)

            # 单选按钮 + 模板名
            btn = QRadioButton(template_name)
            btn.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            btn.setStyleSheet("""
                QRadioButton {
                    color: #2c3e50;
                    background: transparent;
                    border: none;
                    spacing: 10px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #bdc3c7;
                    border-radius: 9px;
                }
                QRadioButton::indicator:checked {
                    border: 2px solid #3498db;
                    background-color: #3498db;
                }
            """)
            card_layout.addWidget(btn)

            # 甬道预览
            preview = QLabel(f"甬道：{lane_desc}")
            preview.setFont(QFont("Microsoft YaHei", 10))
            preview.setStyleSheet("color: #7f8c8d; background: transparent; border: none; padding-left: 28px;")
            preview.setWordWrap(True)
            card_layout.addWidget(preview)

            self.template_group.addButton(btn)
            self.template_buttons[template_name] = btn
            layout.addWidget(card)

        # 默认选中第一个
        if self.template_buttons:
            list(self.template_buttons.values())[0].setChecked(True)

        layout.addSpacing(12)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("dialogCancelBtn")
        cancel_btn.setFont(QFont("Microsoft YaHei", 11))
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确认选择")
        confirm_btn.setObjectName("dialogConfirmBtn")
        confirm_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        confirm_btn.setFixedHeight(36)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def _on_confirm(self):
        """确认选择"""
        checked = self.template_group.checkedButton()
        if checked:
            for name, btn in self.template_buttons.items():
                if btn == checked:
                    self.selected_template = name
                    break
        self.accept()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            #templateCard {
                background-color: #f8f9fa;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
            }
            #templateCard:hover {
                background-color: #f0f4f8;
                border-color: #3498db;
            }
            #dialogCancelBtn {
                background-color: #ffffff;
                color: #555;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                padding: 6px 20px;
            }
            #dialogCancelBtn:hover {
                background-color: #f0f4f8;
                border-color: #e74c3c;
                color: #e74c3c;
            }
            #dialogConfirmBtn {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
            }
            #dialogConfirmBtn:hover {
                background-color: #2980b9;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)


# ==================== 新建看板对话框 ====================

class NewBoardDialog(QDialog):
    """新建看板对话框 - 输入名称并选择模板"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.board_name = ""
        self.template_name = None
        self.setWindowTitle("新建看板")
        self.setFixedSize(500, 480)
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)

        # 标题
        title = QLabel("新建看板")
        title.setFont(QFont("Microsoft YaHei", 15, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; background: transparent; border: none;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(4)

        # 名称输入
        name_label = QLabel("看板名称")
        name_label.setFont(QFont("Microsoft YaHei", 11))
        name_label.setStyleSheet("color: #2c3e50; background: transparent; border: none;")
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入看板名称")
        self.name_input.setFont(QFont("Microsoft YaHei", 12))
        self.name_input.setFixedHeight(40)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #f8f9fa;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                padding: 0 12px;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border-color: #3498db;
                background-color: #ffffff;
            }
        """)
        layout.addWidget(self.name_input)

        layout.addSpacing(8)

        # 模板选择
        tmpl_label = QLabel("选择模板")
        tmpl_label.setFont(QFont("Microsoft YaHei", 11))
        tmpl_label.setStyleSheet("color: #2c3e50; background: transparent; border: none;")
        layout.addWidget(tmpl_label)

        # 模板列表
        self.template_group = QButtonGroup(self)
        self.template_buttons = {}

        for template_name in self.db.KANBAN_TEMPLATES:
            lanes = self.db.KANBAN_TEMPLATES[template_name]
            lane_desc = " → ".join([name for name, _ in lanes])

            card = QFrame()
            card.setObjectName("templateCard")
            card.setFixedHeight(56)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 8, 16, 8)
            card_layout.setSpacing(2)

            btn = QRadioButton(template_name)
            btn.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            btn.setStyleSheet("""
                QRadioButton {
                    color: #2c3e50;
                    background: transparent;
                    border: none;
                    spacing: 8px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #bdc3c7;
                    border-radius: 9px;
                }
                QRadioButton::indicator:checked {
                    border: 2px solid #3498db;
                    background-color: #3498db;
                }
            """)
            card_layout.addWidget(btn)

            preview = QLabel(f"甬道：{lane_desc}")
            preview.setFont(QFont("Microsoft YaHei", 10))
            preview.setStyleSheet("color: #555555; background: transparent; border: none; padding-left: 26px;")
            preview.setWordWrap(True)
            card_layout.addWidget(preview)

            self.template_group.addButton(btn)
            self.template_buttons[template_name] = btn
            layout.addWidget(card)

        # 默认选中"项目管理"
        if "项目管理" in self.template_buttons:
            self.template_buttons["项目管理"].setChecked(True)

        layout.addSpacing(8)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("dialogCancelBtn")
        cancel_btn.setFont(QFont("Microsoft YaHei", 11))
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("创建")
        confirm_btn.setObjectName("dialogConfirmBtn")
        confirm_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        confirm_btn.setFixedHeight(36)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def _on_confirm(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入看板名称")
            return

        checked = self.template_group.checkedButton()
        if checked:
            for tmpl_name, btn in self.template_buttons.items():
                if btn == checked:
                    self.template_name = tmpl_name
                    break

        self.board_name = name
        self.accept()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            #templateCard {
                background-color: #f8f9fa;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
            }
            #templateCard:hover {
                background-color: #f0f4f8;
                border-color: #3498db;
            }
            #dialogCancelBtn {
                background-color: #ffffff;
                color: #555;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                padding: 6px 20px;
            }
            #dialogCancelBtn:hover {
                background-color: #f0f4f8;
                border-color: #e74c3c;
                color: #e74c3c;
            }
            #dialogConfirmBtn {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
            }
            #dialogConfirmBtn:hover {
                background-color: #2980b9;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)


# ==================== 看板卡片（看板列表页中的卡片） ====================

class BoardCard(QFrame):
    """看板列表中的单个看板卡片"""

    def __init__(self, board_data, stats, parent=None):
        super().__init__(parent)
        self.board_data = board_data
        self.board_id = board_data['id']
        self.board_name = board_data['name']
        self.stats = stats
        self.setFixedHeight(140)
        self.setCursor(Qt.PointingHandCursor)

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # 看板名称
        self.name_label = QLabel(self.board_name)
        self.name_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.name_label.setStyleSheet("color: #2c3e50; background: transparent; border: none;")
        layout.addWidget(self.name_label)

        # 统计信息
        lane_count = self.stats.get('lane_count', 0)
        event_count = self.stats.get('event_count', 0)
        stats_text = f"{lane_count} 个甬道  |  {event_count} 个事项"
        self.stats_label = QLabel(stats_text)
        self.stats_label.setFont(QFont("Microsoft YaHei", 10))
        self.stats_label.setStyleSheet("color: #7f8c8d; background: transparent; border: none;")
        layout.addWidget(self.stats_label)

        # 创建日期
        created_at = self.board_data.get('created_at', '')
        if created_at:
            # 只取日期部分
            date_str = created_at.split(' ')[0] if ' ' in created_at else created_at
            self.date_label = QLabel(f"创建于 {date_str}")
        else:
            self.date_label = QLabel("")
        self.date_label.setFont(QFont("Microsoft YaHei", 9))
        self.date_label.setStyleSheet("color: #bdc3c7; background: transparent; border: none;")
        layout.addWidget(self.date_label)

        layout.addStretch()

    def _apply_style(self):
        self.setStyleSheet("""
            BoardCard {
                background-color: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 10px;
            }
            BoardCard:hover {
                border-color: #3498db;
                background-color: #f8fbff;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(6)
        shadow.setOffset(1, 2)
        shadow.setColor(QColor(0, 0, 0, 20))
        self.setGraphicsEffect(shadow)

    def enterEvent(self, event):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(2, 4)
        shadow.setColor(QColor(0, 0, 0, 35))
        self.setGraphicsEffect(shadow)
        super().enterEvent(event)

    def leaveEvent(self, event):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(6)
        shadow.setOffset(1, 2)
        shadow.setColor(QColor(0, 0, 0, 20))
        self.setGraphicsEffect(shadow)
        super().leaveEvent(event)


# ==================== 看板列表页 ====================

class BoardListPage(QWidget):
    """看板列表页 - 显示所有看板卡片"""

    board_opened = pyqtSignal(int)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.board_cards = []

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 16, 24, 16)
        main_layout.setSpacing(16)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        title_label = QLabel("我的看板")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50; background: transparent; border: none;")
        toolbar.addWidget(title_label)

        toolbar.addStretch()

        self.add_btn = QPushButton("+ 新建看板")
        self.add_btn.setObjectName("addBoardBtn")
        self.add_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.add_btn.setFixedHeight(40)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_board)
        toolbar.addWidget(self.add_btn)

        main_layout.addLayout(toolbar)

        # 看板卡片网格区域（带滚动）
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
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
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll_area, 1)

    def _apply_style(self):
        self.setStyleSheet("""
            BoardListPage {
                background-color: #f0f2f5;
            }
            #addBoardBtn {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 24px;
            }
            #addBoardBtn:hover {
                background-color: #2980b9;
            }
            #addBoardBtn:pressed {
                background-color: #2471a3;
            }
        """)

    def refresh(self):
        """刷新看板列表"""
        # 清除旧卡片
        for card in self.board_cards:
            card.deleteLater()
        self.board_cards.clear()

        # 清除 grid_layout 中的所有项
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 获取所有看板
        boards = self.db.get_boards()
        col_count = 3  # 每行最多3个卡片

        for i, board in enumerate(boards):
            stats = self.db.get_board_stats(board['id'])
            card = BoardCard(board, stats, self.grid_container)
            card.mouseDoubleClickEvent = lambda event, bid=board['id']: self.board_opened.emit(bid)
            card.setContextMenuPolicy(Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(
                lambda pos, bid=board['id'], bname=board['name'], c=card: self._show_board_context_menu(pos, bid, bname, c)
            )
            row = i // col_count
            col = i % col_count
            self.grid_layout.addWidget(card, row, col)
            self.board_cards.append(card)

        # 设置列拉伸
        for col in range(col_count):
            self.grid_layout.setColumnStretch(col, 1)

    def _on_add_board(self):
        """新建看板"""
        dialog = NewBoardDialog(self.db, self)
        if dialog.exec_() == QDialog.Accepted:
            board_id = self.db.create_board(dialog.board_name, dialog.template_name)
            self.refresh()
            self.board_opened.emit(board_id)

    def _show_board_context_menu(self, pos, board_id, board_name, card_widget):
        """显示看板右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 4px;
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

        open_action = menu.addAction("打开看板")
        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除看板")

        action = menu.exec_(card_widget.mapToGlobal(pos))
        if action == open_action:
            self.board_opened.emit(board_id)
        elif action == rename_action:
            self._rename_board(board_id, board_name)
        elif action == delete_action:
            self._delete_board(board_id, board_name)

    def _rename_board(self, board_id, old_name):
        """重命名看板"""
        new_name, ok = QInputDialog.getText(
            self, "重命名看板", "请输入新名称：",
            text=old_name
        )
        if ok and new_name.strip():
            self.db.update_board(board_id, name=new_name.strip())
            self.refresh()

    def _delete_board(self, board_id, board_name):
        """删除看板"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除看板「{board_name}」吗？\n看板中的甬道配置将被清除，但事项不会被删除。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_board(board_id)
            self.refresh()


# ==================== 看板标签页 ====================

class KanbanTab(QWidget):
    """看板标签页 - 支持多看板切换"""

    event_edit_requested = pyqtSignal(int)
    event_status_changed = pyqtSignal()
    create_event_requested = pyqtSignal(int)
    pin_card_to_desktop = pyqtSignal(int)  # Pin卡片到桌面

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.lanes = []
        self.current_board_id = None
        self._zoom_level = 1.0  # 缩放级别
        self._min_zoom = 0.5
        self._max_zoom = 1.5

        self._setup_ui()

        # 连接信号
        self.board_list_page.board_opened.connect(self.open_board)

        # 显示看板列表
        self._show_board_list()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 看板列表页
        self.board_list_page = BoardListPage(self.db, self)
        main_layout.addWidget(self.board_list_page)

        # 看板视图（甬道区域）
        self.board_view = QWidget()
        board_view_layout = QVBoxLayout(self.board_view)
        board_view_layout.setContentsMargins(12, 8, 12, 8)
        board_view_layout.setSpacing(8)

        # 看板视图工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.back_btn = QPushButton("<< 返回列表")
        self.back_btn.setFont(QFont("Microsoft YaHei", 11))
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_to_list)
        toolbar.addWidget(self.back_btn)

        self.board_title_label = QLabel("")
        self.board_title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.board_title_label.setStyleSheet("color: #2c3e50; background: transparent; border: none;")
        toolbar.addWidget(self.board_title_label)

        toolbar.addStretch()

        self.add_lane_btn = QPushButton("+ 添加甬道")
        self.add_lane_btn.setFont(QFont("Microsoft YaHei", 11))
        self.add_lane_btn.setCursor(Qt.PointingHandCursor)
        self.add_lane_btn.clicked.connect(self._on_add_lane)
        toolbar.addWidget(self.add_lane_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFont(QFont("Microsoft YaHei", 11))
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        self.create_event_btn = QPushButton("➕ 新建事件")
        self.create_event_btn.setFont(QFont("Microsoft YaHei", 11))
        self.create_event_btn.setCursor(Qt.PointingHandCursor)
        self.create_event_btn.clicked.connect(self._on_create_event)
        toolbar.addWidget(self.create_event_btn)

        self.import_events_btn = QPushButton("📥 导入事件")
        self.import_events_btn.setFont(QFont("Microsoft YaHei", 11))
        self.import_events_btn.setCursor(Qt.PointingHandCursor)
        self.import_events_btn.clicked.connect(self._on_import_events)
        toolbar.addWidget(self.import_events_btn)

        board_view_layout.addLayout(toolbar)

        # 甬道滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f5f6fa;
                border-radius: 8px;
            }
            QScrollBar:horizontal {
                height: 8px;
                background: transparent;
                margin: 0 4px;
            }
            QScrollBar::handle:horizontal {
                background: #cccccc;
                border-radius: 4px;
                min-width: 30px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)

        self.lanes_container = QWidget()
        self.lanes_container.setStyleSheet("background-color: #f5f6fa;")
        self.lanes_layout = QHBoxLayout(self.lanes_container)
        self.lanes_layout.setContentsMargins(8, 8, 8, 8)
        self.lanes_layout.setSpacing(12)
        self.lanes_layout.addStretch()

        self.scroll_area.setWidget(self.lanes_container)
        board_view_layout.addWidget(self.scroll_area, 1)

        self.board_view.setStyleSheet("""
            QWidget#boardView {
                background-color: #f5f6fa;
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
            QPushButton:pressed {
                background-color: #e8f0fe;
            }
        """)

        main_layout.addWidget(self.board_view)
        self.board_view.hide()

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet("""
            KanbanTab {
                background-color: #f0f2f5;
            }
        """)

    def _show_board_list(self):
        """显示看板列表页"""
        self.board_view.hide()
        self.board_list_page.show()
        self.board_list_page.refresh()
        self.current_board_id = None

    def open_board(self, board_id):
        """打开指定看板"""
        self.current_board_id = board_id
        board = self.db.get_board(board_id)
        if board:
            self.board_title_label.setText(board['name'])

        self.board_list_page.hide()
        self.board_view.show()
        self.refresh()

    def back_to_list(self):
        """返回看板列表"""
        self._show_board_list()

    def refresh(self):
        """刷新当前看板的甬道和卡片"""
        if self.current_board_id is None:
            return

        # 清空旧甬道
        for lane in self.lanes:
            lane.setParent(None)
            lane.deleteLater()
        self.lanes.clear()

        # 清空 layout 中的剩余项（如 stretch）
        while self.lanes_layout.count():
            item = self.lanes_layout.takeAt(0)

        lanes_data = self.db.get_kanban_lanes(self.current_board_id)
        for lane_data in lanes_data:
            lane = KanbanLane(lane_data, self.db, self.current_board_id, self.lanes_container)
            lane.load_cards(self.event_edit_requested.emit)
            lane.pin_to_desktop.connect(self.pin_card_to_desktop.emit)
            self.lanes_layout.addWidget(lane)
            self.lanes.append(lane)

        self.lanes_layout.addStretch()

        # 统一刷新所有甬道样式（确保外框和标题颜色正确显示）
        for lane in self.lanes:
            lane._update_header_color()

        # 自动分配：将未分配到任何看板甬道的事件放入第一个甬道
        self._auto_assign_unassigned_events()

    def _auto_assign_unassigned_events(self):
        """将未分配到任何看板任何甬道的事件按状态分配到当前看板的对应甬道"""
        if self.current_board_id is None:
            return

        lanes = self.db.get_kanban_lanes(self.current_board_id)
        if not lanes:
            return

        lane_ids = [l['id'] for l in lanes]

        # 1. 清理：移除当前看板甬道中不属于当前看板的事件
        if lane_ids:
            placeholders = ','.join(['?'] * len(lane_ids))
            cursor = self.db.conn.cursor()
            cursor.execute(
                f"""DELETE FROM kanban_lane_items
                    WHERE lane_id IN ({placeholders})
                    AND event_id NOT IN (
                        SELECT id FROM events WHERE board_id = ? OR (board_id IS NULL AND ? = 0)
                    )""",
                lane_ids + [self.current_board_id, 0])
            # 也移除 board_id IS NULL 的事件（归属看板为"无"的不应在任何看板中）
            cursor.execute(
                f"""DELETE FROM kanban_lane_items
                    WHERE lane_id IN ({placeholders})
                    AND event_id IN (
                        SELECT id FROM events WHERE board_id IS NULL
                    )""",
                lane_ids)
            self.db.conn.commit()

        # 2. 获取当前看板的非归档事件（board_id 匹配）
        all_events = self.db.get_all_events(board_id=self.current_board_id)
        # 获取已在当前看板任何甬道中的事件ID
        if lane_ids:
            placeholders = ','.join(['?'] * len(lane_ids))
            cursor = self.db.conn.cursor()
            cursor.execute(f"SELECT DISTINCT event_id FROM kanban_lane_items WHERE lane_id IN ({placeholders})", lane_ids)
            assigned_ids = set(row[0] for row in cursor.fetchall())
        else:
            assigned_ids = set()

        first_lane_id = lanes[0]['id']
        mid_lane_id = lanes[1]['id'] if len(lanes) >= 2 else lanes[0]['id']
        last_lane_id = lanes[-1]['id']

        # 按甬道名称关键词匹配目标甬道
        completed_lane_id = last_lane_id
        progress_lane_id = mid_lane_id
        pending_lane_id = first_lane_id
        for lane in lanes:
            name = lane['name'].lower()
            if any(kw in name for kw in ['完成', 'done', '上线', 'closed', '已上线', '已完成']):
                completed_lane_id = lane['id']
            elif any(kw in name for kw in ['进行', '开发', 'doing', 'progress', 'wip', '开发中', '测试中', '审核中', '进行中', '下一步', '等待中']):
                progress_lane_id = lane['id']
            elif any(kw in name for kw in ['待办', '待处理', '待开始', 'todo', 'backlog', 'pending', '收集箱', '需求分析']):
                pending_lane_id = lane['id']

        # 3. 状态变更重分配：已在甬道中的事件，如果状态变了，移到对应甬道
        if lane_ids:
            placeholders = ','.join(['?'] * len(lane_ids))
            cursor = self.db.conn.cursor()
            # 已完成的事件移到匹配的甬道
            cursor.execute(
                f"""DELETE FROM kanban_lane_items
                    WHERE lane_id IN ({placeholders}) AND lane_id != ?
                    AND event_id IN (SELECT id FROM events WHERE status = 'completed')""",
                lane_ids + [completed_lane_id])
            cursor.execute(
                f"""INSERT OR IGNORE INTO kanban_lane_items (lane_id, event_id)
                    SELECT ?, id FROM events
                    WHERE status = 'completed' AND board_id = ?
                    AND id NOT IN (SELECT event_id FROM kanban_lane_items WHERE lane_id = ?)""",
                [completed_lane_id, self.current_board_id, completed_lane_id])
            # 进行中的事件移到匹配的甬道
            cursor.execute(
                f"""DELETE FROM kanban_lane_items
                    WHERE lane_id IN ({placeholders}) AND lane_id != ?
                    AND event_id IN (SELECT id FROM events WHERE status = 'in_progress')""",
                lane_ids + [progress_lane_id])
            cursor.execute(
                f"""INSERT OR IGNORE INTO kanban_lane_items (lane_id, event_id)
                    SELECT ?, id FROM events
                    WHERE status = 'in_progress' AND board_id = ?
                    AND id NOT IN (SELECT event_id FROM kanban_lane_items WHERE lane_id = ?)""",
                [progress_lane_id, self.current_board_id, progress_lane_id])
            self.db.conn.commit()

        unassigned = [e for e in all_events if e['id'] not in assigned_ids and e['status'] != 'archived']
        if not unassigned:
            # 即使没有新事件要分配，也要刷新（可能清理了旧卡片或状态变更）
            for lane_widget in self.lanes:
                lane_widget.load_cards(self.event_edit_requested.emit)
            return

        # 4. 按状态分配未分配事件（同样按名称匹配）
        for event in unassigned:
            status = event.get('status', 'pending')
            if status == 'completed':
                self.db.add_event_to_lane(completed_lane_id, event['id'])
            elif status == 'in_progress':
                self.db.add_event_to_lane(progress_lane_id, event['id'])
            else:
                self.db.add_event_to_lane(pending_lane_id, event['id'])

        # 重新加载卡片
        for lane_widget in self.lanes:
            lane_widget.load_cards(self.event_edit_requested.emit)

    def _on_add_lane(self):
        """添加甬道到当前看板"""
        if self.current_board_id is None:
            return
        name, ok = QInputDialog.getText(
            self, "添加甬道", "请输入甬道名称："
        )
        if ok and name.strip():
            self.db.add_kanban_lane(self.current_board_id, name.strip())
            self.refresh()

    def _on_create_event(self):
        """在看板中新建事件"""
        self.create_event_requested.emit(self.current_board_id)

    def _on_import_events(self):
        """导入事项列表中的事件到当前看板"""
        dialog = ImportEventsDialog(self.db, self.current_board_id, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh()
            self.event_status_changed.emit()

    def wheelEvent(self, event):
        """Ctrl+滚轮缩放看板甬道大小"""
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom_level = min(self._zoom_level + 0.1, self._max_zoom)
            else:
                self._zoom_level = max(self._zoom_level - 0.1, self._min_zoom)
            self._apply_zoom()
            event.accept()
        else:
            super().wheelEvent(event)

    def _apply_zoom(self):
        """应用缩放：调整甬道宽度、间距和字体大小"""
        base_width = 280
        base_spacing = 12
        new_width = int(base_width * self._zoom_level)
        new_spacing = int(base_spacing * self._zoom_level)
        for lane_widget in self.lanes:
            lane_widget.setFixedWidth(new_width)
            lane_widget.apply_zoom(self._zoom_level)
        if hasattr(self, 'lanes_layout'):
            self.lanes_layout.setSpacing(new_spacing)


# ==================== 导入事件对话框 ====================

class ImportEventsDialog(QDialog):
    """导入事件对话框 - 从事项列表勾选事件导入当前看板"""

    def __init__(self, db, board_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.board_id = board_id
        self.setWindowTitle("导入事件")
        self.setMinimumSize(520, 480)
        self._setup_ui()
        self._load_events()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # 标题
        title = QLabel("导入事件到看板")
        title.setFont(QFont("Microsoft YaHei", 15, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; background: transparent; border: none;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("选择要导入到当前看板的事项")
        desc.setFont(QFont("Microsoft YaHei", 10))
        desc.setStyleSheet("color: #7f8c8d; background: transparent; border: none;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(4)

        # 全选复选框
        self.select_all_cb = QCheckBox("全选")
        self.select_all_cb.setFont(QFont("Microsoft YaHei", 11))
        self.select_all_cb.setStyleSheet("color: #2c3e50; background: transparent; border: none;")
        self.select_all_cb.stateChanged.connect(self._on_select_all)
        layout.addWidget(self.select_all_cb)

        # 事件列表（使用 QTableWidget）
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", "标题", "优先级", "计划时间"])
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        # 列宽设置
        self.table.setColumnWidth(0, 36)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 120)
        layout.addWidget(self.table, 1)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("dialogCancelBtn")
        cancel_btn.setFont(QFont("Microsoft YaHei", 11))
        cancel_btn.setFixedHeight(36)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.import_btn = QPushButton("导入")
        self.import_btn.setObjectName("dialogConfirmBtn")
        self.import_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.import_btn.setFixedHeight(36)
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.clicked.connect(self._on_import)
        btn_layout.addWidget(self.import_btn)

        layout.addLayout(btn_layout)

    def _load_events(self):
        """加载可导入的事件列表"""
        # 获取当前看板的甬道ID列表
        lanes = self.db.get_kanban_lanes(self.board_id)
        lane_ids = [l['id'] for l in lanes]

        # 获取已在当前看板甬道中的事件ID
        cursor = self.db.conn.cursor()
        if lane_ids:
            placeholders = ",".join(["?"] * len(lane_ids))
            cursor.execute(
                f"SELECT DISTINCT event_id FROM kanban_lane_items WHERE lane_id IN ({placeholders})",
                lane_ids)
            assigned_ids = set(row[0] for row in cursor.fetchall())
        else:
            assigned_ids = set()

        # 获取可导入的事件：board_id IS NULL OR board_id = 当前看板，且未在当前看板甬道中
        cursor.execute("""
            SELECT * FROM events
            WHERE status != 'archived'
              AND (board_id IS NULL OR board_id = ?)
            ORDER BY planned_start ASC
        """, (self.board_id,))
        all_rows = cursor.fetchall()
        importable = [dict(row) for row in all_rows if dict(row)['id'] not in assigned_ids]

        self.table.setRowCount(len(importable))
        priority_map = {"high": "高", "medium": "中", "low": "低"}

        for row_idx, event in enumerate(importable):
            # 复选框列
            cb = QCheckBox()
            cb.setFont(QFont("Microsoft YaHei", 9))
            cb_container = QWidget()
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.addWidget(cb)
            self.table.setCellWidget(row_idx, 0, cb_container)

            # 标题列
            title_item = QTableWidgetItem(event.get('title', '未命名'))
            title_item.setFont(QFont("Microsoft YaHei", 10))
            title_item.setData(Qt.UserRole, event['id'])
            self.table.setItem(row_idx, 1, title_item)

            # 优先级列
            priority = event.get('priority', 'medium')
            priority_item = QTableWidgetItem(priority_map.get(priority, "中"))
            priority_item.setFont(QFont("Microsoft YaHei", 10))
            priority_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 2, priority_item)

            # 计划时间列
            planned_start = event.get('planned_start', '')
            duration = event.get('planned_duration_minutes', 30)
            if planned_start:
                try:
                    dt = QDateTime.fromString(planned_start, "yyyy-MM-dd HH:mm")
                    time_str = dt.toString("MM/dd HH:mm")
                except Exception:
                    time_str = planned_start[:16] if planned_start else "未设定"
            else:
                time_str = "未设定"
            time_text = f"{time_str} | {duration}分钟"
            time_item = QTableWidgetItem(time_text)
            time_item.setFont(QFont("Microsoft YaHei", 9))
            self.table.setItem(row_idx, 3, time_item)

        # 调整行高
        for row_idx in range(self.table.rowCount()):
            self.table.setRowHeight(row_idx, 36)

    def _on_select_all(self, state):
        """全选/取消全选"""
        checked = state == Qt.Checked
        for row_idx in range(self.table.rowCount()):
            cb_container = self.table.cellWidget(row_idx, 0)
            if cb_container:
                cb = cb_container.findChild(QCheckBox)
                if cb:
                    cb.blockSignals(True)
                    cb.setChecked(checked)
                    cb.blockSignals(False)

    def _on_import(self):
        """执行导入操作"""
        lanes = self.db.get_kanban_lanes(self.board_id)
        if not lanes:
            QMessageBox.warning(self, "提示", "当前看板没有甬道，请先添加甬道。")
            return

        first_lane_id = lanes[0]['id']
        imported_count = 0

        for row_idx in range(self.table.rowCount()):
            cb_container = self.table.cellWidget(row_idx, 0)
            if cb_container:
                cb = cb_container.findChild(QCheckBox)
                if cb and cb.isChecked():
                    title_item = self.table.item(row_idx, 1)
                    if title_item:
                        event_id = title_item.data(Qt.UserRole)
                        # 设置事件的 board_id
                        self.db.update_event(event_id, board_id=self.board_id)
                        # 添加到第一个甬道
                        self.db.add_event_to_lane(first_lane_id, event_id)
                        imported_count += 1

        if imported_count == 0:
            QMessageBox.information(self, "提示", "请至少选择一个事项。")
            return

        self.accept()

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QCheckBox {
                color: #2c3e50;
                background: transparent;
                border: none;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #bdc3c7;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #3498db;
                background-color: #3498db;
            }
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                gridline-color: transparent;
                font-family: "Microsoft YaHei";
            }
            QTableWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:alternate {
                background-color: #f8f9fa;
            }
            QHeaderView::section {
                background-color: #f0f2f5;
                color: #7f8c8d;
                border: none;
                border-bottom: 1px solid #e0e0e0;
                padding: 8px 6px;
                font-family: "Microsoft YaHei";
                font-size: 11px;
                font-weight: bold;
            }
            #dialogCancelBtn {
                background-color: #ffffff;
                color: #555;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                padding: 6px 20px;
            }
            #dialogCancelBtn:hover {
                background-color: #f0f4f8;
                border-color: #e74c3c;
                color: #e74c3c;
            }
            #dialogConfirmBtn {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
            }
            #dialogConfirmBtn:hover {
                background-color: #2980b9;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

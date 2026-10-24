"""
Design System - Premium Theme for Desktop Sticky Notes
A warm, sophisticated palette inspired by physical sticky notes and modern productivity apps.
"""

from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QApplication, QStyle


# ============================================================
# Color Palette
# ============================================================

class Colors:
    """Premium color palette — warm slate + amber accent"""
    
    # Primary brand — warm amber/gold (sticky note identity)
    AMBER_50 = "#FFFBEB"
    AMBER_100 = "#FEF3C7"
    AMBER_200 = "#FDE68A"
    AMBER_300 = "#FCD34D"
    AMBER_400 = "#FBBF24"
    AMBER_500 = "#F59E0B"
    AMBER_600 = "#D97706"
    AMBER_700 = "#B45309"

    # Neutral slate
    SLATE_50 = "#F8FAFC"
    SLATE_100 = "#F1F5F9"
    SLATE_200 = "#E2E8F0"
    SLATE_300 = "#CBD5E1"
    SLATE_400 = "#94A3B8"
    SLATE_500 = "#64748B"
    SLATE_600 = "#475569"
    SLATE_700 = "#334155"
    SLATE_800 = "#1E293B"
    SLATE_900 = "#0F172A"

    # Surface
    WHITE = "#FFFFFF"
    BACKGROUND = "#F5F5F0"  # Warm off-white
    SURFACE = "#FFFFFF"
    SURFACE_HOVER = "#FAFAF7"

    # Text
    TEXT_PRIMARY = "#1C1917"
    TEXT_SECONDARY = "#57534E"
    TEXT_TERTIARY = "#78716C"
    TEXT_DISABLED = "#A8A29E"

    # Semantic
    SUCCESS = "#059669"
    SUCCESS_LIGHT = "#D1FAE5"
    WARNING = "#D97706"
    WARNING_LIGHT = "#FEF3C7"
    DANGER = "#DC2626"
    DANGER_LIGHT = "#FEE2E2"
    INFO = "#2563EB"
    INFO_LIGHT = "#DBEAFE"

    # Priority
    PRIORITY_HIGH = "#DC2626"
    PRIORITY_MEDIUM = "#F59E0B"
    PRIORITY_LOW = "#059669"

    # Borders
    BORDER_LIGHT = "#E7E5E4"
    BORDER_DEFAULT = "#D6D3D1"
    BORDER_FOCUS = "#F59E0B"

    # Shadow
    SHADOW_COLOR = QColor(0, 0, 0)
    SHADOW_SUBTLE = (2, 4, QColor(0, 0, 0, 15))
    SHADOW_CARD = (2, 8, QColor(0, 0, 0, 25))
    SHADOW_ELEVATED = (4, 16, QColor(0, 0, 0, 40))


# ============================================================
# Typography
# ============================================================

class Fonts:
    """Typography scale"""
    
    FAMILY = "Microsoft YaHei"
    FAMILY_MONO = "Consolas"
    
    @staticmethod
    def size(size, weight=QFont.Normal):
        f = QFont(Fonts.FAMILY, size, weight)
        return f
    
    @staticmethod
    def bold(size):
        return QFont(Fonts.FAMILY, size, QFont.Bold)
    
    @staticmethod
    def mono(size, weight=QFont.Normal):
        return QFont(Fonts.FAMILY_MONO, size, weight)


# ============================================================
# Spacing
# ============================================================

class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


# ============================================================
# Border Radius
# ============================================================

class Radius:
    SM = "4px"
    MD = "6px"
    LG = "10px"
    XL = "14px"
    FULL = "9999px"


# ============================================================
# Icon Helper — Uses Qt Standard Icons
# ============================================================

class Icons:
    """Professional icon system using Qt StandardPixmap"""
    
    @staticmethod
    def get_standard_pixmap(style, standard_pixmap):
        """Get a standard pixmap from the application style"""
        return style.standardPixmap(standard_pixmap)
    
    @staticmethod
    def get_icon(style, icon_name):
        """Map logical icon names to Qt StandardPixmap"""
        mapping = {
            # Actions
            "add": QStyle.SP_FileDialogNewFolder,
            "edit": QStyle.SP_FileDialogDetailedView,
            "delete": QStyle.SP_TrashIcon,
            "close": QStyle.SP_DialogCloseButton,
            "save": QStyle.SP_DialogSaveButton,
            "cancel": QStyle.SP_DialogCancelButton,
            "ok": QStyle.SP_DialogOkButton,
            "apply": QStyle.SP_DialogApplyButton,
            "refresh": QStyle.SP_BrowserReload,
            "search": QStyle.SP_FileDialogContentsView,
            
            # Media
            "play": QStyle.SP_MediaPlay,
            "pause": QStyle.SP_MediaPause,
            "stop": QStyle.SP_MediaStop,
            
            # Arrows
            "arrow_down": QStyle.SP_ArrowDown,
            "arrow_up": QStyle.SP_ArrowUp,
            "arrow_right": QStyle.SP_ArrowRight,
            "arrow_left": QStyle.SP_ArrowLeft,
            
            # File/Folder
            "file": QStyle.SP_FileIcon,
            "folder": QStyle.SP_DirIcon,
            "folder_open": QStyle.SP_DirOpenIcon,
            
            # Window
            "window_close": QStyle.SP_TitleBarCloseButton,
            "window_min": QStyle.SP_TitleBarMinButton,
            "window_max": QStyle.SP_TitleBarMaxButton,
            
            # Info
            "info": QStyle.SP_MessageBoxInformation,
            "warning": QStyle.SP_MessageBoxWarning,
            "error": QStyle.SP_MessageBoxCritical,
            "question": QStyle.SP_MessageBoxQuestion,
            
            # Misc
            "pin": QStyle.SP_DialogYesButton,  # Using checkmark as proxy
            "settings": QStyle.SP_FileDialogListView,
            "combo": QStyle.SP_ToolBarVerticalExtensionButton,
        }
        
        sp = mapping.get(icon_name)
        if sp is not None:
            return style.standardPixmap(sp)
        return None


# ============================================================
# Sticky Note Colors (Physical-inspired)
# ============================================================

class NoteColors:
    """Physical sticky note inspired colors"""
    
    YELLOW = "#FEF9C4"
    ORANGE = "#FED7AA"
    GREEN = "#BBF7D0"
    BLUE = "#BFDBFE"
    PURPLE = "#DDD6FE"
    PINK = "#FBCFE8"
    MINT = "#A7F3D0"
    PEACH = "#FDE68A"
    
    @classmethod
    def get_all(cls):
        return [
            cls.YELLOW, cls.ORANGE, cls.GREEN, cls.BLUE,
            cls.PURPLE, cls.PINK, cls.MINT, cls.PEACH
        ]
    
    @classmethod
    def get_darker(cls, color_hex, amount=30):
        """Get a slightly darker version for header"""
        c = QColor(color_hex)
        h, s, l, a = c.getHslF()
        l = max(0, l - amount / 255)
        c.setHslF(h, s, l, a)
        return c.name()


# ============================================================
# Stylesheet Templates
# ============================================================

class Styles:
    """Reusable stylesheet fragments"""
    
    BUTTON_PRIMARY = f"""
        QPushButton {{
            background-color: {Colors.AMBER_500};
            color: {Colors.WHITE};
            border: none;
            border-radius: {Radius.MD};
            padding: 8px 20px;
            font-family: {Fonts.FAMILY};
            font-weight: 600;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {Colors.AMBER_600};
        }}
        QPushButton:pressed {{
            background-color: {Colors.AMBER_700};
        }}
        QPushButton:disabled {{
            background-color: {Colors.SLATE_200};
            color: {Colors.SLATE_400};
        }}
    """
    
    BUTTON_SECONDARY = f"""
        QPushButton {{
            background-color: {Colors.WHITE};
            color: {Colors.SLATE_700};
            border: 1px solid {Colors.SLATE_200};
            border-radius: {Radius.MD};
            padding: 8px 20px;
            font-family: {Fonts.FAMILY};
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {Colors.SLATE_50};
            border-color: {Colors.AMBER_400};
            color: {Colors.AMBER_700};
        }}
    """
    
    BUTTON_DANGER = f"""
        QPushButton {{
            background-color: {Colors.WHITE};
            color: {Colors.DANGER};
            border: 1px solid {Colors.SLATE_200};
            border-radius: {Radius.MD};
            padding: 8px 20px;
            font-family: {Fonts.FAMILY};
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {Colors.DANGER_LIGHT};
            border-color: {Colors.DANGER};
        }}
    """
    
    BUTTON_GHOST = f"""
        QPushButton {{
            background-color: transparent;
            color: {Colors.SLATE_500};
            border: none;
            border-radius: {Radius.MD};
            padding: 4px 8px;
            font-family: {Fonts.FAMILY};
        }}
        QPushButton:hover {{
            background-color: {Colors.SLATE_100};
            color: {Colors.SLATE_700};
        }}
    """
    
    INPUT = f"""
        QLineEdit, QTextEdit {{
            background-color: {Colors.WHITE};
            border: 1px solid {Colors.SLATE_200};
            border-radius: {Radius.MD};
            padding: 8px 12px;
            font-family: {Fonts.FAMILY};
            font-size: 13px;
            color: {Colors.TEXT_PRIMARY};
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border-color: {Colors.AMBER_400};
            background-color: {Colors.AMBER_50};
        }}
        QLineEdit::placeholder, QTextEdit::placeholder {{
            color: {Colors.TEXT_DISABLED};
        }}
    """
    
    COMBOBOX = f"""
        QComboBox {{
            background-color: {Colors.WHITE};
            border: 1px solid {Colors.SLATE_200};
            border-radius: {Radius.MD};
            padding: 6px 12px;
            font-family: {Fonts.FAMILY};
            color: {Colors.TEXT_PRIMARY};
        }}
        QComboBox:focus {{
            border-color: {Colors.AMBER_400};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
    """
    
    SCROLLBAR = f"""
        QScrollBar:vertical {{
            width: 6px;
            background: transparent;
        }}
        QScrollBar::handle:vertical {{
            background: {Colors.SLATE_300};
            border-radius: 3px;
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {Colors.SLATE_400};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            height: 6px;
            background: transparent;
        }}
        QScrollBar::handle:horizontal {{
            background: {Colors.SLATE_300};
            border-radius: 3px;
            min-width: 24px;
        }}
    """
    
    MENU = f"""
        QMenu {{
            background-color: {Colors.WHITE};
            border: 1px solid {Colors.SLATE_200};
            border-radius: {Radius.LG};
            padding: 6px;
            font-family: {Fonts.FAMILY};
            font-size: 12px;
        }}
        QMenu::item {{
            padding: 8px 24px;
            border-radius: {Radius.SM};
            color: {Colors.TEXT_PRIMARY};
        }}
        QMenu::item:selected {{
            background-color: {Colors.AMBER_50};
            color: {Colors.AMBER_700};
        }}
        QMenu::separator {{
            height: 1px;
            background: {Colors.SLATE_100};
            margin: 4px 12px;
        }}
    """
    
    CHECKBOX = f"""
        QCheckBox {{
            color: {Colors.TEXT_PRIMARY};
            background: transparent;
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {Colors.SLATE_300};
            border-radius: {Radius.SM};
        }}
        QCheckBox::indicator:checked {{
            border-color: {Colors.AMBER_500};
            background-color: {Colors.AMBER_500};
        }}
    """
    
    TABLE = f"""
        QTableWidget {{
            background-color: {Colors.WHITE};
            border: 1px solid {Colors.SLATE_200};
            border-radius: {Radius.LG};
            gridline-color: transparent;
            font-family: {Fonts.FAMILY};
        }}
        QTableWidget::item {{
            padding: 8px 12px;
            border-bottom: 1px solid {Colors.SLATE_100};
        }}
        QTableWidget::item:alternate {{
            background-color: {Colors.SLATE_50};
        }}
        QTableWidget::item:selected {{
            background-color: {Colors.AMBER_50};
            color: {Colors.TEXT_PRIMARY};
        }}
        QHeaderView::section {{
            background-color: {Colors.SLATE_50};
            color: {Colors.SLATE_600};
            padding: 10px 12px;
            border: none;
            border-bottom: 2px solid {Colors.SLATE_200};
            font-family: {Fonts.FAMILY};
            font-weight: 600;
            font-size: 11px;
        }}
    """


# ============================================================
# Main Application Stylesheet
# ============================================================

MAIN_STYLESHEET = f"""
    QMainWindow {{
        background-color: {Colors.BACKGROUND};
    }}
    
    /* Tab Widget */
    QTabWidget::pane {{
        border: none;
        background-color: {Colors.BACKGROUND};
    }}
    QTabBar::tab {{
        background: transparent;
        color: {Colors.SLATE_500};
        padding: 14px 32px;
        font-size: 14px;
        font-weight: 500;
        border: none;
        border-bottom: 3px solid transparent;
        min-width: 80px;
    }}
    QTabBar::tab:selected {{
        color: {Colors.AMBER_600};
        border-bottom-color: {Colors.AMBER_500};
    }}
    QTabBar::tab:hover {{
        color: {Colors.SLATE_700};
        border-bottom-color: {Colors.SLATE_300};
    }}
    
    /* Group Box */
    QGroupBox {{
        background-color: {Colors.WHITE};
        border: 1px solid {Colors.SLATE_200};
        border-radius: {Radius.LG};
        margin-top: 14px;
        padding-top: 20px;
        font-weight: 600;
        color: {Colors.TEXT_PRIMARY};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 16px;
        color: {Colors.TEXT_SECONDARY};
    }}
    
    /* Status Bar */
    QStatusBar {{
        background-color: {Colors.SLATE_100};
        color: {Colors.TEXT_TERTIARY};
        font-size: 11px;
        border-top: 1px solid {Colors.SLATE_200};
    }}
    
    /* Scroll Area */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    
    /* Progress Bar */
    QProgressBar {{
        border: none;
        border-radius: 4px;
        background-color: {Colors.SLATE_100};
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {Colors.AMBER_500};
        border-radius: 4px;
    }}
    
    /* SpinBox */
    QSpinBox, QDoubleSpinBox {{
        background-color: {Colors.WHITE};
        border: 1px solid {Colors.SLATE_200};
        border-radius: {Radius.MD};
        padding: 4px 8px;
        font-family: {Fonts.FAMILY};
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {Colors.AMBER_400};
    }}
    
    /* DateEdit */
    QDateEdit, QDateTimeEdit {{
        background-color: {Colors.WHITE};
        border: 1px solid {Colors.SLATE_200};
        border-radius: {Radius.MD};
        padding: 6px 12px;
        font-family: {Fonts.FAMILY};
    }}
    QDateEdit:focus, QDateTimeEdit:focus {{
        border-color: {Colors.AMBER_400};
    }}
"""

# ============================================================
# Export
# ============================================================

# Convenient access
C = Colors
F = Fonts
S = Styles
I = Icons
R = Radius
SP = Spacing
NC = NoteColors

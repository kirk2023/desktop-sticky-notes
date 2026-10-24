"""
桌面便利贴 - 计划计时系统
应用入口

使用方法:
    python main.py

依赖安装:
    pip install -r requirements.txt
"""

import sys
import os
import traceback
import datetime

# 确保应用目录在路径中
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# 全局异常捕获，写入日志文件
LOG_FILE = os.path.join(app_dir, "error.log")

def global_exception_hook(exc_type, exc_value, exc_tb):
    """捕获未处理异常，写入日志文件"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log_entry = f"\n{'='*60}\n[{timestamp}] {exc_type.__name__}: {exc_value}\n{msg}{'='*60}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = global_exception_hook

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QAbstractNativeEventFilter
from PyQt5.QtGui import QFont


class WindowsHotkeyFilter(QAbstractNativeEventFilter):
    """
    Windows 全局热键过滤器：系统级 Ctrl+Alt+N 呼出快速新建。
    非 Windows 平台自动跳过（应用内有同快捷键的 QShortcut 兜底）。
    """

    WM_HOTKEY = 0x0312
    HOTKEY_ID = 0xB00F
    MOD_CONTROL = 0x0002
    MOD_ALT = 0x0001
    VK_N = 0x4E  # 'N'

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self._registered = False

    def register(self):
        if sys.platform != "win32":
            return False
        try:
            import ctypes
            ok = ctypes.windll.user32.RegisterHotKey(
                None, self.HOTKEY_ID, self.MOD_CONTROL | self.MOD_ALT, self.VK_N)
            self._registered = bool(ok)
            return self._registered
        except Exception as e:
            print(f"[热键] 注册全局热键失败（可忽略）: {e}")
            return False

    def unregister(self):
        if self._registered and sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.UnregisterHotKey(None, self.HOTKEY_ID)
            except Exception:
                pass
            self._registered = False

    def nativeEventFilter(self, eventType, message):
        if sys.platform == "win32" and eventType == b"windows_generic_MSG":
            try:
                import ctypes.wintypes
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == self.WM_HOTKEY and msg.wParam == self.HOTKEY_ID:
                    if self.callback:
                        self.callback()
                    return True, 0
            except Exception:
                pass
        return False, 0


def main():
    # 高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 设置应用信息
    app.setApplicationName("桌面便利贴")
    app.setOrganizationName("StickyNotes")

    # 设置默认字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 导入并创建主窗口
    from main_window import MainWindow

    window = MainWindow()
    window.show()

    # 系统级全局热键：Ctrl+Alt+N 快速新建
    hotkey_filter = WindowsHotkeyFilter(window.show_quick_add)
    if hotkey_filter.register():
        app.installNativeEventFilter(hotkey_filter)
        app.aboutToQuit.connect(hotkey_filter.unregister)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

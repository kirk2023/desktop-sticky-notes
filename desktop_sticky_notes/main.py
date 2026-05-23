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
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


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

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

"""
Windows 系统托盘通知模块
"""

import platform


def send_windows_notification(title, message, icon_path=None):
    """
    发送 Windows 系统托盘通知（静默提示，不弹阻塞窗口）

    Args:
        title: 通知标题
        message: 通知内容
        icon_path: 图标路径（可选）
    """
    if platform.system() != "Windows":
        print(f"[通知] {title}: {message}")
        return

    try:
        # 方法1: 使用 win10toast（如果可用）- 非阻塞通知
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                title,
                message,
                icon_path=icon_path,
                duration=5,
                threaded=True
            )
            return
        except ImportError:
            pass

        # 方法2: 使用 plyer（跨平台）- 非阻塞通知
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="桌面便利贴",
                timeout=5
            )
            return
        except ImportError:
            pass

        # 回退: 打印到控制台（不弹窗，避免阻塞）
        print(f"[通知] {title}: {message}")

    except Exception as e:
        print(f"[通知错误] {e}")
        print(f"[通知] {title}: {message}")


class NotificationManager:
    """通知管理器"""

    def __init__(self):
        self._notified_events = set()  # 已通知的事件ID，避免重复通知

    def check_and_notify(self, events, callback=None):
        """
        检查是否有事件需要通知

        通知条件：
        - 事件开始时间在当前时间之前（已到达但未通知过）
        - 或事件开始时间在当前时间之后5分钟内（即将到达）

        Args:
            events: 事件列表
            callback: 回调函数，接收事件数据

        Returns:
            需要通知的事件列表
        """
        from datetime import datetime
        now = datetime.now()
        need_notify = []

        for event in events:
            event_id = event['id']
            planned_start = event.get('planned_start')

            if not planned_start:
                continue

            if event_id in self._notified_events:
                continue

            try:
                start_time = datetime.strptime(planned_start, "%Y-%m-%d %H:%M")
                diff = (start_time - now).total_seconds()

                # 已到达开始时间（最多延迟30分钟内提醒）
                # 或即将在5分钟内到达
                if -1800 <= diff <= 300:
                    need_notify.append(event)
                    self._notified_events.add(event_id)

                    # 发送系统通知
                    send_windows_notification(
                        "📋 事项提醒",
                        f"「{event.get('title', '未命名')}」到达计划开始时间！\n"
                        f"计划时间: {planned_start}\n"
                        f"是否将其 Pin 到桌面？"
                    )

                    if callback:
                        callback(event)

            except (ValueError, TypeError):
                continue

        return need_notify

    def reset_notification(self, event_id):
        """重置事件的通知状态（允许再次通知）"""
        self._notified_events.discard(event_id)

    def clear_all(self):
        """清除所有通知记录"""
        self._notified_events.clear()

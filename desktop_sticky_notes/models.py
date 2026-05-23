"""
数据模型定义
"""


class Event:
    """计划事项模型"""

    # 状态常量
    STATUS_PENDING = "pending"       # 待开始
    STATUS_IN_PROGRESS = "in_progress"  # 进行中
    STATUS_COMPLETED = "completed"   # 已完成
    STATUS_ARCHIVED = "archived"     # 已归档

    # 优先级
    PRIORITY_HIGH = "high"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_LOW = "low"

    # 便利贴颜色
    COLORS = [
        "#FFF9C4",  # 淡黄
        "#FFCCBC",  # 淡橙
        "#C8E6C9",  # 淡绿
        "#BBDEFB",  # 淡蓝
        "#E1BEE7",  # 淡紫
        "#F8BBD0",  # 淡粉
        "#B2EBF2",  # 淡青
        "#D7CCC8",  # 淡棕
    ]

    def __init__(self, id=None, title="", description="",
                 planned_start=None, planned_duration_minutes=30,
                 status=STATUS_PENDING, priority=PRIORITY_MEDIUM,
                 color=None, created_at=None):
        self.id = id
        self.title = title
        self.description = description
        self.planned_start = planned_start  # datetime string "YYYY-MM-DD HH:MM"
        self.planned_duration_minutes = planned_duration_minutes
        self.status = status
        self.priority = priority
        self.color = color or self.COLORS[0]
        self.created_at = created_at

    @property
    def planned_end(self):
        """计算计划结束时间"""
        if self.planned_start and self.planned_duration_minutes:
            from datetime import datetime, timedelta
            try:
                start = datetime.strptime(self.planned_start, "%Y-%m-%d %H:%M")
                end = start + timedelta(minutes=self.planned_duration_minutes)
                return end.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                return None
        return None

    @property
    def is_active(self):
        return self.status in (self.STATUS_PENDING, self.STATUS_IN_PROGRESS)


class TimerRecord:
    """计时记录模型"""

    def __init__(self, id=None, event_id=None,
                 actual_start=None, actual_end=None,
                 actual_duration_seconds=0,
                 created_at=None):
        self.id = id
        self.event_id = event_id
        self.actual_start = actual_start
        self.actual_end = actual_end
        self.actual_duration_seconds = actual_duration_seconds
        self.created_at = created_at

    @property
    def actual_duration_minutes(self):
        return round(self.actual_duration_seconds / 60, 1)

    @property
    def actual_duration_hours(self):
        return round(self.actual_duration_seconds / 3600, 2)

"""
Data Models
"""


class Event:
    """Plan Event Model"""

    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_ARCHIVED = "archived"

    PRIORITY_HIGH = "high"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_LOW = "low"

    # Premium note colors
    COLORS = [
        "#FEF9C4",  # Classic Yellow
        "#FED7AA",  # Warm Orange
        "#BBF7D0",  # Soft Green
        "#BFDBFE",  # Sky Blue
        "#DDD6FE",  # Lavender
        "#FBCFE8",  # Pink
        "#A7F3D0",  # Mint
        "#FDE68A",  # Peach
    ]

    def __init__(self, id=None, title="", description="",
                 planned_start=None, planned_duration_minutes=30,
                 status=STATUS_PENDING, priority=PRIORITY_MEDIUM,
                 color=None, created_at=None):
        self.id = id
        self.title = title
        self.description = description
        self.planned_start = planned_start
        self.planned_duration_minutes = planned_duration_minutes
        self.status = status
        self.priority = priority
        self.color = color or self.COLORS[0]
        self.created_at = created_at

    @property
    def planned_end(self):
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

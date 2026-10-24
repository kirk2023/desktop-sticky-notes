"""
自动排期引擎 - 按个人工作日历为新事项建议开始时间

规则：
- 工作日历：工作日（默认周一至五）、工作时间 09:00-18:00、午休 12:00-13:00
- 事项时长按"工作时间"计算：9:00 开始的 4 小时任务占用 9:00-14:00（自动跨午休），
  下班没做完的顺延到下一工作日 9:00，周末跳过
- 新事项排在第一个不与已有计划（全部未归档事项，跨看板）冲突的工作时段
"""

from datetime import datetime, timedelta

# 设置键前缀 schedule_，默认值
DEFAULTS = {
    'work_start': "09:00",
    'work_end': "18:00",
    'lunch_start': "12:00",
    'lunch_end': "13:00",
    'work_days': "0,1,2,3,4",  # 0=周一 ... 6=周日
}


def get_work_config(db):
    """从设置读取工作日历配置"""
    cfg = {}
    for key, default in DEFAULTS.items():
        cfg[key] = db.get_setting('schedule_' + key, default)
    cfg['work_days'] = set(int(d) for d in str(cfg['work_days']).split(',')
                           if d.strip() != '')
    for key in ('work_start', 'work_end', 'lunch_start', 'lunch_end'):
        h, m = str(cfg[key]).split(':')
        cfg[key] = (int(h), int(m))
    return cfg


def _dt_on(date, hm):
    return datetime(date.year, date.month, date.day, hm[0], hm[1])


def _is_workday(dt, cfg):
    return dt.weekday() in cfg['work_days']


def snap_forward(dt, cfg):
    """把时间点推到下一个可开始工作的时刻（跳过周末、午休、下班后）"""
    while not _is_workday(dt, cfg):
        dt = dt.replace(hour=cfg['work_start'][0], minute=cfg['work_start'][1],
                        second=0, microsecond=0) + timedelta(days=1)
    ws = _dt_on(dt.date(), cfg['work_start'])
    we = _dt_on(dt.date(), cfg['work_end'])
    ls = _dt_on(dt.date(), cfg['lunch_start'])
    le = _dt_on(dt.date(), cfg['lunch_end'])

    if dt < ws:
        return ws
    if ls <= dt < le:
        return le
    if dt >= we:
        nxt = dt.replace(hour=cfg['work_start'][0], minute=cfg['work_start'][1],
                         second=0, microsecond=0) + timedelta(days=1)
        return snap_forward(nxt, cfg)
    return dt.replace(second=0, microsecond=0)


def add_work_minutes(start, minutes, cfg):
    """从 start 起推进 minutes 个工作时长（跳过午休/下班/周末），返回结束时刻"""
    end = snap_forward(start, cfg)
    remaining = int(minutes)
    guard = 0
    while remaining > 0 and guard < 500:
        guard += 1
        end = snap_forward(end, cfg)
        we = _dt_on(end.date(), cfg['work_end'])
        ls = _dt_on(end.date(), cfg['lunch_start'])
        le = _dt_on(end.date(), cfg['lunch_end'])

        # 当前窗口：到午休开始或下班为止（取更近者）
        if end < ls:
            win_end = min(we, ls)
        else:
            win_end = we
        avail = int((win_end - end).total_seconds() // 60)
        if avail <= 0:
            end = end + timedelta(minutes=1)
            continue
        take = min(avail, remaining)
        end = end + timedelta(minutes=take)
        remaining -= take
    return end


def effective_window(start_dt, minutes, cfg):
    """事项的实际占用区间 [开始, 按工作时长推进的结束]"""
    return start_dt, add_work_minutes(start_dt, minutes, cfg)


def suggest_start(db, duration_minutes, after=None, exclude_event_id=None):
    """
    为一件 duration_minutes（工作时长）的事项建议开始时间：
    从 after（默认现在）起，找第一个不与已有计划冲突的工作时段。

    Args:
        db: Database 实例
        duration_minutes: 工作时长（分钟）
        after: 起始锚点 datetime，默认现在
        exclude_event_id: 编辑场景排除自身

    Returns:
        datetime 建议开始时间
    """
    cfg = get_work_config(db)
    duration = max(int(duration_minutes or 30), 1)
    candidate = snap_forward(after or datetime.now(), cfg)

    # 收集所有未归档事项的占用区间（跨看板——个人日历全局冲突）
    occupied = []
    for e in db.get_all_events():
        if exclude_event_id is not None and e['id'] == exclude_event_id:
            continue
        ps = e.get('planned_start')
        if not ps:
            continue
        try:
            s = datetime.strptime(ps, "%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            continue
        dur = e.get('planned_duration_minutes') or 30
        occupied.append(effective_window(s, dur, cfg))
    occupied.sort(key=lambda x: x[0])

    guard = 0
    while guard < 200:
        guard += 1
        _, c_end = effective_window(candidate, duration, cfg)
        conflict = None
        for s, e_end in occupied:
            if s < c_end and candidate < e_end:
                conflict = e_end
                break
        if conflict is None:
            return candidate
        candidate = snap_forward(conflict, cfg)
    return candidate


def format_suggestion(dt):
    """建议时间的展示文本：10/26 14:00 · 周一"""
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return f"{dt.month}/{dt.day} {dt.strftime('%H:%M')} · {weekdays[dt.weekday()]}"

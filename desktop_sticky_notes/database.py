"""
SQLite 数据库操作层
"""

import sqlite3
import os
import sys
import json
from datetime import datetime

# 数据库版本号（表结构变更时递增）
DB_VERSION = 14

# 配置文件路径
CONFIG_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "DesktopStickyNotes", "config.json"
)


def load_config():
    """加载配置"""
    default = {"db_path": ""}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                default.update(cfg)
    except Exception:
        pass
    return default


def save_config(config):
    """保存配置"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


class Database:
    """数据库管理类"""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = self._get_db_path()
        self.db_path = db_path
        self.conn = None
        self._connect()
        # 先建表再迁移：否则全新数据库上 ALTER 会因表不存在而静默失败
        self._create_tables()
        self._migrate()
        self._auto_backup()

    @staticmethod
    def _get_db_path():
        """获取数据库路径：优先使用用户自定义路径，否则使用默认路径"""
        config = load_config()
        custom = config.get("db_path", "")
        if custom and os.path.isdir(custom):
            custom_db = os.path.join(custom, "sticky_notes.db")
            # 安全检查：自定义路径下必须有数据库文件，否则回退到默认路径
            if os.path.exists(custom_db):
                return custom_db
            else:
                # 自定义路径下没有数据库，清除无效配置
                config["db_path"] = ""
                save_config(config)
        return Database._get_default_db_path()

    @staticmethod
    def _get_default_db_path():
        """获取默认数据库路径 - 固定在 %APPDATA% 下"""
        app_name = "DesktopStickyNotes"
        if sys.platform == "win32":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
        elif sys.platform == "darwin":
            base = os.path.expanduser("~/Library/Application Support")
        else:
            base = os.path.expanduser("~/.local/share")

        app_dir = os.path.join(base, app_name)
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, "sticky_notes.db")

    def _connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

    def _migrate(self):
        """数据库迁移 - 版本升级时保留数据"""
        cursor = self.conn.cursor()

        # 创建版本表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _db_version (
                version INTEGER NOT NULL
            )
        """)

        # 获取当前版本
        cursor.execute("SELECT version FROM _db_version ORDER BY version DESC LIMIT 1")
        row = cursor.fetchone()
        current_version = row['version'] if row else 0

        if current_version < DB_VERSION:
            print(f"[DB] 迁移数据库: v{current_version} -> v{DB_VERSION}")

            # v1 -> v2: timer_records 表新增 actual_duration_seconds 列
            if current_version < 2:
                try:
                    cursor.execute("ALTER TABLE timer_records ADD COLUMN actual_duration_seconds INTEGER DEFAULT 0")
                except Exception:
                    pass

            # v2 -> v3: 新增看板甬道表和甬道-事件关联表
            if current_version < 3:
                pass  # 由 _create_tables 处理（CREATE IF NOT EXISTS）

            # v3 -> v4: 新增看板表，kanban_lanes 加 board_id
            if current_version < 4:
                # 新增看板表
                try:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS kanban_boards (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            sort_order INTEGER DEFAULT 0,
                            is_default INTEGER DEFAULT 0,
                            created_at TEXT DEFAULT (datetime('now', 'localtime'))
                        )
                    """)
                except Exception:
                    pass
                # 给已有 kanban_lanes 表添加 board_id 列
                try:
                    cursor.execute("ALTER TABLE kanban_lanes ADD COLUMN board_id INTEGER NOT NULL DEFAULT 1")
                except Exception:
                    pass  # 列已存在则跳过

            # v4 -> v5: 确保旧数据库的 board_id 列存在（修复迁移遗漏）
            if current_version < 5:
                try:
                    cursor.execute("ALTER TABLE kanban_lanes ADD COLUMN board_id INTEGER NOT NULL DEFAULT 1")
                except Exception:
                    pass
                # 确保看板表存在
                try:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS kanban_boards (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            sort_order INTEGER DEFAULT 0,
                            is_default INTEGER DEFAULT 0,
                            created_at TEXT DEFAULT (datetime('now', 'localtime'))
                        )
                    """)
                except Exception:
                    pass

            # v5 -> v6: events 表加 board_id 字段
            if current_version < 6:
                try:
                    cursor.execute("ALTER TABLE events ADD COLUMN board_id INTEGER DEFAULT NULL")
                except Exception:
                    pass

            # v6 -> v7: events 表加 completed_at 字段
            if current_version < 7:
                try:
                    cursor.execute("ALTER TABLE events ADD COLUMN completed_at TEXT DEFAULT NULL")
                except Exception:
                    pass

            # v7 -> v8: events 表加 archive_note 备注字段
            if current_version < 8:
                try:
                    cursor.execute("ALTER TABLE events ADD COLUMN archive_note TEXT DEFAULT ''")
                except Exception:
                    pass

            # v8 -> v9: events 表加 actual_start_at 实际开始时间
            if current_version < 9:
                try:
                    cursor.execute("ALTER TABLE events ADD COLUMN actual_start_at TEXT DEFAULT NULL")
                except Exception:
                    pass

            # v9 -> v10: kanban_boards 表加 deadline 截止日期
            if current_version < 10:
                try:
                    cursor.execute("ALTER TABLE kanban_boards ADD COLUMN deadline TEXT DEFAULT NULL")
                except Exception:
                    pass

            # v10 -> v11: 新增 app_settings 通用设置表
            if current_version < 11:
                try:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS app_settings (
                            key TEXT PRIMARY KEY,
                            value TEXT
                        )
                    """)
                except Exception:
                    pass

            # v11 -> v12: events 表加 actual_duration_minutes 实际时长（分钟）
            if current_version < 12:
                try:
                    cursor.execute("ALTER TABLE events ADD COLUMN actual_duration_minutes INTEGER DEFAULT NULL")
                except Exception:
                    pass

            # v12 -> v13: kanban_lanes 表加 role 角色（start/progress/done），替代关键词猜测
            if current_version < 13:
                try:
                    cursor.execute("ALTER TABLE kanban_lanes ADD COLUMN role TEXT DEFAULT NULL")
                except Exception:
                    pass
                self._backfill_lane_roles(cursor)

            # v13 -> v14: kanban_boards 表加 closed_at 结项时间（看板生命周期闭环）
            if current_version < 14:
                try:
                    cursor.execute("ALTER TABLE kanban_boards ADD COLUMN closed_at TEXT DEFAULT NULL")
                except Exception:
                    pass

            # 更新版本号
            cursor.execute("DELETE FROM _db_version")
            cursor.execute("INSERT INTO _db_version (version) VALUES (?)", (DB_VERSION,))
            self.conn.commit()
            print(f"[DB] 迁移完成")

    @staticmethod
    def _backfill_lane_roles(cursor):
        """为已有甬道按位置回填角色：首列 start，末列 done，中间 progress"""
        try:
            cursor.execute("SELECT DISTINCT board_id FROM kanban_lanes")
            board_ids = [r['board_id'] for r in cursor.fetchall()]
            for bid in board_ids:
                cursor.execute(
                    "SELECT id FROM kanban_lanes WHERE board_id=? ORDER BY sort_order ASC", (bid,))
                lane_ids = [r['id'] for r in cursor.fetchall()]
                n = len(lane_ids)
                for i, lid in enumerate(lane_ids):
                    if n == 1:
                        role = 'start'
                    elif i == 0:
                        role = 'start'
                    elif i == n - 1:
                        role = 'done'
                    else:
                        role = 'progress'
                    cursor.execute("UPDATE kanban_lanes SET role=? WHERE id=?", (role, lid))
        except Exception as e:
            print(f"[DB] 甬道角色回填失败（可忽略）: {e}")

    def _create_tables(self):
        """创建数据表"""
        cursor = self.conn.cursor()

        # 事件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                planned_start TEXT,
                planned_duration_minutes INTEGER DEFAULT 30,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                color TEXT DEFAULT '#FFF9C4',
                board_id INTEGER DEFAULT NULL,
                completed_at TEXT DEFAULT NULL,
                archive_note TEXT DEFAULT '',
                actual_start_at TEXT DEFAULT NULL,
                actual_duration_minutes INTEGER DEFAULT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 计时记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timer_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                actual_start TEXT,
                actual_end TEXT,
                actual_duration_seconds INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
        """)

        # 卡片位置表（记住用户拖拽的位置）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS card_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER UNIQUE NOT NULL,
                x_position INTEGER DEFAULT 100,
                y_position INTEGER DEFAULT 100,
                width INTEGER DEFAULT 280,
                height INTEGER DEFAULT 220,
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
        """)

        # ==================== 看板相关表 ====================

        # 看板表（支持多看板）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                is_default INTEGER DEFAULT 0,
                deadline TEXT DEFAULT NULL,
                closed_at TEXT DEFAULT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 看板甬道表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_lanes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id INTEGER NOT NULL DEFAULT 1,
                name TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                color TEXT DEFAULT '#ecf0f1',
                role TEXT DEFAULT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (board_id) REFERENCES kanban_boards(id)
            )
        """)

        # 甬道-事件关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_lane_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lane_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (lane_id) REFERENCES kanban_lanes(id),
                FOREIGN KEY (event_id) REFERENCES events(id),
                UNIQUE(lane_id, event_id)
            )
        """)

        # 看板配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # 自定义模板快照表（保存用户修改过的甬道配置）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanban_custom_snapshot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lane_id INTEGER,
                name TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                color TEXT DEFAULT '#ecf0f1'
            )
        """)

        # 通用应用设置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        self.conn.commit()

    # ==================== 事件 CRUD ====================

    def add_event(self, title, description="", planned_start=None,
                  planned_duration_minutes=30, priority="medium", color="#FFF9C4",
                  board_id=None, actual_start=None):
        """添加新事件"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO events (title, description, planned_start, actual_start_at,
                              planned_duration_minutes, priority, color, board_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, planned_start, actual_start,
              planned_duration_minutes, priority, color, board_id))
        self.conn.commit()
        return cursor.lastrowid

    def get_event(self, event_id):
        """获取单个事件"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_all_events(self, status=None, board_id=None):
        """获取所有事件，可按状态和看板筛选"""
        cursor = self.conn.cursor()
        conditions = []
        params = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        else:
            conditions.append("status != 'archived'")
        if board_id is not None:
            conditions.append("board_id = ?")
            params.append(board_id)

        where = " AND ".join(conditions)
        cursor.execute(f"SELECT * FROM events WHERE {where} ORDER BY planned_start ASC", params)
        return [dict(row) for row in cursor.fetchall()]

    def get_active_events(self):
        """获取活跃事件（待开始 + 进行中）"""
        return self.get_all_events()  # 已排除 archived

    def get_upcoming_events(self):
        """获取即将到来的事件（计划开始时间在当前之后）"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE status = 'pending' AND planned_start > ?
            ORDER BY planned_start ASC
        """, (now,))
        return [dict(row) for row in cursor.fetchall()]

    def get_next_event(self):
        """获取下一个即将开始的事件"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE status = 'pending' AND planned_start > ?
            ORDER BY planned_start ASC
            LIMIT 1
        """, (now,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_event(self, event_id, **kwargs):
        """更新事件"""
        allowed_fields = ['title', 'description', 'planned_start',
                         'planned_duration_minutes', 'status', 'priority', 'color', 'board_id',
                         'completed_at', 'archive_note', 'actual_start_at']
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if updates:
            updates.append("updated_at = datetime('now', 'localtime')")
            values.append(event_id)
            cursor = self.conn.cursor()
            cursor.execute(
                f"UPDATE events SET {', '.join(updates)} WHERE id = ?",
                values)
            self.conn.commit()
            return True
        return False

    def delete_event(self, event_id):
        """删除事件（同时删除关联记录）"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kanban_lane_items WHERE event_id = ?", (event_id,))
        cursor.execute("DELETE FROM timer_records WHERE event_id = ?", (event_id,))
        cursor.execute("DELETE FROM card_positions WHERE event_id = ?", (event_id,))
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self.conn.commit()

    def duplicate_event(self, event_id):
        """
        复制事件（创建新事件，复制除状态/计时外的所有属性）

        Returns:
            新事件的ID，失败返回None
        """
        event = self.get_event(event_id)
        if not event:
            return None

        cursor = self.conn.cursor()
        # 复制事件，标题加"(副本)"，状态重置为pending
        new_title = event['title'] + " (副本)" if event.get('title') else "(副本)"
        cursor.execute("""
            INSERT INTO events (
                title, description, priority, color, status,
                planned_start, planned_duration_minutes,
                board_id
            ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
        """, (
            new_title,
            event.get('description'),
            event.get('priority', 'medium'),
            event.get('color'),
            event.get('planned_start'),
            event.get('planned_duration_minutes'),
            event.get('board_id')
        ))
        new_id = cursor.lastrowid
        self.conn.commit()
        return new_id

    def archive_event(self, event_id):
        """归档事件"""
        self.update_event(event_id, status="archived")

    # ==================== 计时记录 ====================

    def start_timer(self, event_id, manual_offset_seconds=0):
        """
        开始一个新的计时会话

        Args:
            event_id: 事件ID
            manual_offset_seconds: 手动补偿的秒数（迟到补偿）
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO timer_records (event_id, actual_start, actual_duration_seconds)
            VALUES (?, ?, ?)
        """, (event_id, now, manual_offset_seconds))
        self.conn.commit()
        self.update_event(event_id, status="in_progress")
        return cursor.lastrowid

    def pause_timer(self, event_id):
        """
        暂停当前计时会话（关闭当前记录，但不标记完成）

        Returns:
            本次会话的秒数（不含之前的累计）
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT id, actual_start, actual_duration_seconds FROM timer_records
            WHERE event_id = ? AND actual_end IS NULL
            ORDER BY id DESC LIMIT 1
        """, (event_id,))
        record = cursor.fetchone()

        if record:
            start_time = datetime.strptime(record['actual_start'], "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
            session_seconds = int((end_time - start_time).total_seconds())
            total_seconds = (record['actual_duration_seconds'] or 0) + session_seconds

            cursor.execute("""
                UPDATE timer_records
                SET actual_end = ?, actual_duration_seconds = ?
                WHERE id = ?
            """, (now, total_seconds, record['id']))
            self.conn.commit()
            return total_seconds
        return 0

    def resume_timer(self, event_id):
        """
        恢复计时（创建新会话，actual_duration_seconds 设为 0）

        历史累计时间由卡片的 accumulated_seconds 维护，
        数据库只记录每个独立会话的实际时长，避免双重计算。

        Returns:
            新会话的 record id
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO timer_records (event_id, actual_start, actual_duration_seconds)
            VALUES (?, ?, 0)
        """, (event_id, now))
        self.conn.commit()
        self.update_event(event_id, status="in_progress")
        return cursor.lastrowid

    def stop_timer(self, event_id):
        """
        完成计时 - 关闭当前会话并返回总累计时间

        Returns:
            所有会话的总秒数
        """
        # 先暂停当前会话
        self.pause_timer(event_id)
        # 获取总累计时间
        total = self.get_total_elapsed_seconds(event_id)
        self.update_event(event_id, status="completed")
        return total

    def get_total_elapsed_seconds(self, event_id):
        """获取事件的所有计时会话的总秒数（含正在进行的会话）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(actual_duration_seconds), 0) as total
            FROM (
                SELECT actual_duration_seconds FROM timer_records
                WHERE event_id = ? AND actual_end IS NOT NULL
                UNION ALL
                SELECT actual_duration_seconds FROM timer_records
                WHERE event_id = ? AND actual_end IS NULL
            )
        """, (event_id, event_id))
        row = cursor.fetchone()
        total = row['total'] if row else 0

        # 加上正在进行的会话从 actual_start 到现在的时间
        cursor.execute("""
            SELECT actual_start FROM timer_records
            WHERE event_id = ? AND actual_end IS NULL
            ORDER BY id DESC LIMIT 1
        """, (event_id,))
        active_row = cursor.fetchone()
        if active_row and active_row['actual_start']:
            try:
                start_dt = datetime.strptime(active_row['actual_start'], "%Y-%m-%d %H:%M:%S")
                active_seconds = int((datetime.now() - start_dt).total_seconds())
                total += max(active_seconds, 0)
            except (ValueError, TypeError):
                pass

        return total

    def get_elapsed_seconds_map(self, event_ids):
        """
        批量获取多个事件的累计耗时（秒），避免列表渲染时 N+1 查询

        Returns:
            dict {event_id: seconds}，未有任何耗时的 ID 对应 0
        """
        ids = [i for i in event_ids if i is not None]
        if not ids:
            return {}
        placeholders = ",".join(["?"] * len(ids))
        result = {eid: 0 for eid in ids}
        cursor = self.conn.cursor()

        cursor.execute(f"""
            SELECT event_id, COALESCE(SUM(actual_duration_seconds), 0) as total
            FROM timer_records
            WHERE event_id IN ({placeholders}) AND actual_end IS NOT NULL
            GROUP BY event_id
        """, ids)
        for row in cursor.fetchall():
            result[row['event_id']] = row['total'] or 0

        # 加上正在进行的会话从 actual_start 到现在的时间
        cursor.execute(f"""
            SELECT event_id, actual_start FROM timer_records
            WHERE event_id IN ({placeholders}) AND actual_end IS NULL
        """, ids)
        now_dt = datetime.now()
        for row in cursor.fetchall():
            if row['actual_start']:
                try:
                    start_dt = datetime.strptime(row['actual_start'], "%Y-%m-%d %H:%M:%S")
                    result[row['event_id']] += max(int((now_dt - start_dt).total_seconds()), 0)
                except (ValueError, TypeError):
                    pass
        return result

    def get_active_session_map(self, event_ids):
        """
        批量获取正在计时的会话

        Returns:
            dict {event_id: actual_start_str}，仅包含有进行中会话的事件
        """
        ids = [i for i in event_ids if i is not None]
        if not ids:
            return {}
        placeholders = ",".join(["?"] * len(ids))
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT event_id, MAX(actual_start) as actual_start
            FROM timer_records
            WHERE event_id IN ({placeholders}) AND actual_end IS NULL
            GROUP BY event_id
        """, ids)
        return {row['event_id']: row['actual_start'] for row in cursor.fetchall()}

    def get_current_session_info(self, event_id):
        """
        获取当前正在进行的会话信息

        Returns:
            dict with 'record_id', 'actual_start', 'accumulated_seconds'
            or None if no active session
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, actual_start, actual_duration_seconds
            FROM timer_records
            WHERE event_id = ? AND actual_end IS NULL
            ORDER BY id DESC LIMIT 1
        """, (event_id,))
        record = cursor.fetchone()
        if record:
            # 累计之前所有已完成会话的时长
            cursor.execute("""
                SELECT COALESCE(SUM(actual_duration_seconds), 0) as total
                FROM timer_records
                WHERE event_id = ? AND actual_end IS NOT NULL
            """, (event_id,))
            prev_row = cursor.fetchone()
            prev_accumulated = prev_row['total'] if prev_row else 0
            return {
                'record_id': record['id'],
                'actual_start': record['actual_start'],
                'accumulated_seconds': (record['actual_duration_seconds'] or 0) + prev_accumulated
            }
        return None

    def get_timer_record(self, event_id):
        """获取事件的当前未关闭计时记录"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM timer_records
            WHERE event_id = ? AND actual_end IS NULL
            ORDER BY id DESC LIMIT 1
        """, (event_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_timer_records(self, event_id):
        """获取事件的所有计时记录"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM timer_records WHERE event_id = ? ORDER BY id
        """, (event_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_session_count(self, event_id):
        """获取事件的计时会话数量"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM timer_records WHERE event_id = ?
        """, (event_id,))
        row = cursor.fetchone()
        return row['cnt'] if row else 0

    # ==================== 卡片位置 ====================

    def save_card_position(self, event_id, x, y, width=280, height=220):
        """保存卡片位置"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO card_positions
            (event_id, x_position, y_position, width, height)
            VALUES (?, ?, ?, ?, ?)
        """, (event_id, x, y, width, height))
        self.conn.commit()

    def get_card_position(self, event_id):
        """获取卡片位置"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM card_positions WHERE event_id = ?", (event_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def remove_card_position(self, event_id):
        """移除卡片位置记录"""
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM card_positions WHERE event_id = ?", (event_id,))
        self.conn.commit()

    # ==================== 统计分析 ====================

    def get_completed_events_with_stats(self):
        """获取已完成事件及其统计信息"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT e.*, tr.actual_duration_seconds,
                   tr.actual_start, tr.actual_end
            FROM events e
            LEFT JOIN timer_records tr ON tr.id = (
                SELECT id FROM timer_records
                WHERE event_id = e.id AND actual_end IS NOT NULL
                ORDER BY id DESC LIMIT 1
            )
            WHERE e.status = 'completed' OR e.status = 'archived'
            ORDER BY e.updated_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_time_diff_stats(self):
        """获取时间差异统计（包含所有已归档和已完成事件）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT e.id, e.title, e.status,
                   e.planned_duration_minutes,
                   e.priority,
                   e.color,
                   e.board_id,
                   e.completed_at,
                   e.archive_note,
                   e.actual_start_at,
                   e.actual_duration_minutes,
                   COALESCE(
                       (SELECT SUM(actual_duration_seconds)
                        FROM timer_records
                        WHERE event_id = e.id), 0
                   ) / 60.0 as timer_minutes
            FROM events e
            WHERE e.status IN ('completed', 'archived')
            ORDER BY e.updated_at DESC
        """)
        results = []
        for row in cursor.fetchall():
            d = dict(row)
            # 优先使用手动填写的实际时长
            if d.get('actual_duration_minutes') is not None and d['actual_duration_minutes'] > 0:
                d['actual_minutes'] = d['actual_duration_minutes']
            else:
                # 如果没有手动填写，尝试用时间差计算
                if d.get('actual_start_at') and d.get('completed_at'):
                    try:
                        from datetime import datetime
                        start = datetime.strptime(d['actual_start_at'], "%Y-%m-%d %H:%M")
                        end = datetime.strptime(d['completed_at'], "%Y-%m-%d %H:%M")
                        d['actual_minutes'] = (end - start).total_seconds() / 60.0
                    except Exception:
                        d['actual_minutes'] = d.get('timer_minutes', 0)
                else:
                    d['actual_minutes'] = d.get('timer_minutes', 0)
            d['diff_minutes'] = d['planned_duration_minutes'] - d['actual_minutes']
            results.append(d)
        return results

    def update_event_archive_note(self, event_id, note):
        """更新事项的归档备注"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE events SET archive_note = ? WHERE id = ?", (note, event_id))
        self.conn.commit()

    def update_event_completed_at(self, event_id, completed_at):
        """更新事项的完成日期"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE events SET completed_at = ? WHERE id = ?", (completed_at, event_id))
        self.conn.commit()

    def update_event_actual_start(self, event_id, actual_start):
        """更新事项的实际开始日期"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE events SET actual_start_at = ? WHERE id = ?", (actual_start, event_id))
        self.conn.commit()

    def update_event_actual_duration(self, event_id, duration_minutes):
        """更新事项的实际时长（分钟）"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE events SET actual_duration_minutes = ? WHERE id = ?", (duration_minutes, event_id))
        self.conn.commit()

    def get_setting(self, key, default=None):
        """获取应用设置值"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row is None:
            return default
        value = row['value']
        # 尝试类型转换
        if isinstance(default, bool):
            return value.lower() in ('true', '1', 'yes')
        if isinstance(default, int):
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        return value

    def set_setting(self, key, value):
        """设置应用设置值"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        self.conn.commit()

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    # ==================== 看板 CRUD（支持多看板） ====================

    # 预设模板
    KANBAN_TEMPLATES = {
        "研发流程": [
            ("需求分析", "#e8f5e9"), ("开发中", "#fff3e0"),
            ("测试中", "#e3f2fd"), ("已上线", "#f3e5f5")
        ],
        "项目管理": [
            ("待办", "#fce4ec"), ("进行中", "#fff8e1"),
            ("审核中", "#e8eaf6"), ("已完成", "#e0f2f1")
        ],
        "个人GTD": [
            ("收集箱", "#fff3e0"), ("下一步行动", "#e8f5e9"),
            ("等待中", "#e3f2fd"), ("已完成", "#f5f5f5")
        ],
    }

    # ---- 看板（Board）CRUD ----

    def create_board(self, name, template_name=None):
        """创建新看板。如果 template_name 给定，从模板创建甬道。"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(sort_order) as max_order FROM kanban_boards")
        row = cursor.fetchone()
        max_order = row['max_order'] if row and row['max_order'] is not None else -1

        cursor.execute(
            "INSERT INTO kanban_boards (name, sort_order) VALUES (?, ?)",
            (name, max_order + 1))
        board_id = cursor.lastrowid
        self.conn.commit()

        if template_name and template_name in self.KANBAN_TEMPLATES:
            self.init_board_template(board_id, template_name)

        return board_id

    def get_boards(self):
        """获取所有看板：未结项在前（按 sort_order），已结项沉底"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM kanban_boards
            ORDER BY CASE WHEN closed_at IS NULL THEN 0 ELSE 1 END, sort_order ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_board(self, board_id):
        """获取单个看板"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM kanban_boards WHERE id = ?", (board_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_board(self, board_id, name=None, deadline=None):
        """更新看板（重命名、设置截止日期）"""
        updates = []
        values = []
        if name is not None:
            updates.append("name=?")
            values.append(name)
        if deadline is not None:
            updates.append("deadline=?")
            values.append(deadline)
        if not updates:
            return
        values.append(board_id)
        cursor = self.conn.cursor()
        cursor.execute(
            f"UPDATE kanban_boards SET {', '.join(updates)} WHERE id=?",
            values)
        self.conn.commit()

    def set_board_closed(self, board_id, closed=True):
        """标记看板结项/重新打开"""
        cursor = self.conn.cursor()
        closed_at = datetime.now().strftime("%Y-%m-%d %H:%M") if closed else None
        cursor.execute("UPDATE kanban_boards SET closed_at=? WHERE id=?",
                       (closed_at, board_id))
        self.conn.commit()

    def delete_board(self, board_id):
        """删除看板及其甬道和甬道-事件关联"""
        cursor = self.conn.cursor()
        # 获取该看板的所有甬道ID
        cursor.execute("SELECT id FROM kanban_lanes WHERE board_id=?", (board_id,))
        lane_ids = [row['id'] for row in cursor.fetchall()]
        # 删除甬道-事件关联
        for lid in lane_ids:
            cursor.execute("DELETE FROM kanban_lane_items WHERE lane_id=?", (lid,))
        # 删除甬道
        cursor.execute("DELETE FROM kanban_lanes WHERE board_id=?", (board_id,))
        # 删除看板
        cursor.execute("DELETE FROM kanban_boards WHERE id=?", (board_id,))
        self.conn.commit()

    def get_default_board_id(self):
        """获取或创建默认看板"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM kanban_boards WHERE is_default=1 LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row['id']

        # 没有默认看板，检查是否有任何看板
        cursor.execute("SELECT id FROM kanban_boards ORDER BY sort_order ASC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row['id']

        # 没有任何看板，创建默认看板
        board_id = self.create_board("默认看板", "项目管理")
        # 标记为默认
        cursor.execute("UPDATE kanban_boards SET is_default=1 WHERE id=?", (board_id,))
        self.conn.commit()
        return board_id

    # ---- 甬道（Lane）CRUD（需要 board_id） ----

    def get_kanban_lanes(self, board_id):
        """获取指定看板的所有甬道（按 sort_order 排序）"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM kanban_lanes WHERE board_id=? ORDER BY sort_order ASC",
            (board_id,))
        return [dict(row) for row in cursor.fetchall()]

    def add_kanban_lane(self, board_id, name, color="#ecf0f1"):
        """向指定看板添加甬道"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT MAX(sort_order) as max_order FROM kanban_lanes WHERE board_id=?",
            (board_id,))
        row = cursor.fetchone()
        max_order = row['max_order'] if row and row['max_order'] is not None else -1
        cursor.execute(
            "INSERT INTO kanban_lanes (board_id, name, sort_order, color) VALUES (?, ?, ?, ?)",
            (board_id, name, max_order + 1, color))
        self.conn.commit()
        return cursor.lastrowid

    def update_kanban_lane(self, lane_id, name=None, color=None):
        """更新甬道"""
        if name is None and color is None:
            return
        cursor = self.conn.cursor()
        if name and color:
            cursor.execute("UPDATE kanban_lanes SET name=?, color=? WHERE id=?", (name, color, lane_id))
        elif name:
            cursor.execute("UPDATE kanban_lanes SET name=? WHERE id=?", (name, lane_id))
        else:
            cursor.execute("UPDATE kanban_lanes SET color=? WHERE id=?", (color, lane_id))
        self.conn.commit()

    def delete_kanban_lane(self, lane_id):
        """删除甬道及其关联"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kanban_lane_items WHERE lane_id=?", (lane_id,))
        cursor.execute("DELETE FROM kanban_lanes WHERE id=?", (lane_id,))
        self.conn.commit()

    # ---- 甬道-事件关联（不变，不需要 board_id） ----

    def add_event_to_lane(self, lane_id, event_id):
        """将事件添加到甬道"""
        cursor = self.conn.cursor()
        # 先从其他甬道移除
        cursor.execute("DELETE FROM kanban_lane_items WHERE event_id=?", (event_id,))
        # 获取最大排序
        cursor.execute("SELECT MAX(sort_order) as max_order FROM kanban_lane_items WHERE lane_id=?", (lane_id,))
        row = cursor.fetchone()
        max_order = row['max_order'] if row and row['max_order'] is not None else -1
        cursor.execute(
            "INSERT INTO kanban_lane_items (lane_id, event_id, sort_order) VALUES (?, ?, ?)",
            (lane_id, event_id, max_order + 1))
        self.conn.commit()

    def move_event_to_lane(self, event_id, new_lane_id):
        """移动事件到新甬道"""
        self.add_event_to_lane(new_lane_id, event_id)

    def remove_event_from_lane(self, event_id):
        """从所有甬道移除事件"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kanban_lane_items WHERE event_id=?", (event_id,))
        self.conn.commit()

    def get_lane_events(self, lane_id):
        """获取甬道中的所有事件（按 sort_order 排序）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT e.* FROM events e
            JOIN kanban_lane_items kli ON kli.event_id = e.id
            WHERE kli.lane_id = ? AND e.status != 'archived'
            ORDER BY kli.sort_order ASC
        """, (lane_id,))
        return [dict(row) for row in cursor.fetchall()]

    # ---- 模板初始化（针对特定看板） ----

    def init_board_template(self, board_id, template_name):
        """为指定看板初始化模板（清除现有甬道，创建新甬道）"""
        cursor = self.conn.cursor()

        # 获取旧甬道ID
        cursor.execute("SELECT id FROM kanban_lanes WHERE board_id=?", (board_id,))
        old_lane_ids = [row['id'] for row in cursor.fetchall()]

        # 获取旧甬道中的事件位置
        event_lane_index = {}
        if old_lane_ids:
            cursor.execute("""
                SELECT kli.event_id, kli.lane_id
                FROM kanban_lane_items kli
                WHERE kli.lane_id IN ({})
            """.format(','.join('?' * len(old_lane_ids))), old_lane_ids)
            for row in cursor.fetchall():
                eid = row['event_id']
                lid = row['lane_id']
                if lid in old_lane_ids:
                    event_lane_index[eid] = old_lane_ids.index(lid)

        # 清空旧数据
        for lid in old_lane_ids:
            cursor.execute("DELETE FROM kanban_lane_items WHERE lane_id=?", (lid,))
        cursor.execute("DELETE FROM kanban_lanes WHERE board_id=?", (board_id,))

        # 创建新甬道
        if template_name in self.KANBAN_TEMPLATES:
            lanes = self.KANBAN_TEMPLATES[template_name]
        else:
            lanes = [("待办", "#fce4ec"), ("进行中", "#fff8e1"), ("已完成", "#e0f2f1")]

        new_lane_ids = []
        lane_count = len(lanes)
        for i, (name, color) in enumerate(lanes):
            if i == 0:
                role = 'start'
            elif i == lane_count - 1 and lane_count > 1:
                role = 'done'
            else:
                role = 'progress'
            cursor.execute(
                "INSERT INTO kanban_lanes (board_id, name, sort_order, color, role) VALUES (?, ?, ?, ?, ?)",
                (board_id, name, i, color, role))
            new_lane_ids.append(cursor.lastrowid)

        new_lane_count = len(new_lane_ids)
        old_lane_count = len(old_lane_ids)

        # 将事件映射到新甬道（按相对位置比例）
        for eid, old_idx in event_lane_index.items():
            if old_lane_count > 0 and new_lane_count > 0:
                new_idx = int(old_idx * new_lane_count / old_lane_count)
                new_idx = min(new_idx, new_lane_count - 1)
            else:
                new_idx = 0
            target_lane_id = new_lane_ids[new_idx]

            # 获取旧排序
            old_lane_id = old_lane_ids[old_idx]
            cursor.execute(
                "SELECT sort_order FROM kanban_lane_items WHERE event_id=? AND lane_id=?",
                (eid, old_lane_id))
            old_row = cursor.fetchone()
            old_sort = old_row['sort_order'] if old_row else 0

            cursor.execute(
                "INSERT INTO kanban_lane_items (lane_id, event_id, sort_order) VALUES (?, ?, ?)",
                (target_lane_id, eid, old_sort))

        self.conn.commit()

    def get_board_stats(self, board_id):
        """获取看板统计信息：甬道数、事件数、完成进度"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM kanban_lanes WHERE board_id=?", (board_id,))
        lane_count = cursor.fetchone()['cnt']

        cursor.execute("""
            SELECT COUNT(DISTINCT kli.event_id) as cnt
            FROM kanban_lane_items kli
            JOIN kanban_lanes kl ON kl.id = kli.lane_id
            JOIN events e ON e.id = kli.event_id
            WHERE kl.board_id=? AND e.status != 'archived'
        """, (board_id,))
        event_count = cursor.fetchone()['cnt']

        cursor.execute("""
            SELECT status, COUNT(*) as cnt FROM events
            WHERE board_id=? AND status != 'archived'
            GROUP BY status
        """, (board_id,))
        status_counts = {row['status']: row['cnt'] for row in cursor.fetchall()}
        total_count = sum(status_counts.values())
        completed_count = status_counts.get('completed', 0)
        in_progress_count = status_counts.get('in_progress', 0)

        return {
            "lane_count": lane_count,
            "event_count": event_count,
            "total_count": total_count,
            "completed_count": completed_count,
            "in_progress_count": in_progress_count,
        }

    def set_lane_role(self, lane_id, role):
        """设置甬道角色（start/progress/done/None），用于事件状态联动"""
        if role not in ('start', 'progress', 'done', None):
            return
        cursor = self.conn.cursor()
        cursor.execute("UPDATE kanban_lanes SET role=? WHERE id=?", (role, lane_id))
        self.conn.commit()

    # ==================== 投入统计（图表） ====================

    def get_weekly_minutes(self, weeks=8):
        """
        获取最近 N 周每周的实际投入分钟数（按计时会话的实际开始日期归属）

        Returns:
            list [(label, minutes)]，label 为该周一的 MM/DD
        """
        from datetime import timedelta

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT actual_start, COALESCE(actual_duration_seconds, 0) as secs
            FROM timer_records
            WHERE actual_start >= ?
        """, ((datetime.now() - timedelta(weeks=weeks)).strftime("%Y-%m-%d"),))

        # 以周一为每周起点
        week_minutes = {}
        for row in cursor.fetchall():
            try:
                dt = datetime.strptime(row['actual_start'], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                continue
            monday = (dt - timedelta(days=dt.weekday())).date()
            key = monday.strftime("%m/%d")
            week_minutes[key] = week_minutes.get(key, 0) + row['secs'] / 60.0

        result = []
        today = datetime.now().date()
        this_monday = today - timedelta(days=today.weekday())
        for i in range(weeks - 1, -1, -1):
            monday = this_monday - timedelta(weeks=i)
            label = monday.strftime("%m/%d")
            result.append((label, round(week_minutes.get(label, 0), 1)))
        return result

    def get_board_minutes(self):
        """
        按看板统计实际投入分钟数

        Returns:
            list [(board_name, minutes)]，按投入降序
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COALESCE(b.name, '未分配') as name,
                   SUM(tr.actual_duration_seconds) as secs
            FROM timer_records tr
            LEFT JOIN events e ON e.id = tr.event_id
            LEFT JOIN kanban_boards b ON b.id = e.board_id
            GROUP BY name
            ORDER BY secs DESC
        """)
        return [(row['name'], round((row['secs'] or 0) / 60.0, 1))
                for row in cursor.fetchall()]

    def get_today_minutes(self):
        """获取今天的实际投入分钟数（含进行中会话）"""
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(actual_duration_seconds), 0) as total
            FROM timer_records
            WHERE actual_start LIKE ? AND actual_end IS NOT NULL
        """, (today + '%',))
        total = cursor.fetchone()['total'] or 0

        cursor.execute("""
            SELECT actual_start FROM timer_records
            WHERE actual_start LIKE ? AND actual_end IS NULL
        """, (today + '%',))
        now_dt = datetime.now()
        for row in cursor.fetchall():
            try:
                start_dt = datetime.strptime(row['actual_start'], "%Y-%m-%d %H:%M:%S")
                total += max(int((now_dt - start_dt).total_seconds()), 0)
            except (ValueError, TypeError):
                pass
        return round(total / 60.0, 1)

    # ==================== 导出与备份 ====================

    def export_to_json(self, file_path):
        """
        将全部数据导出为 JSON 文件

        Returns:
            导出的事件数量，失败返回 None
        """
        tables = ["events", "timer_records", "kanban_boards", "kanban_lanes",
                  "kanban_lane_items", "card_positions", "app_settings"]
        data = {"exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "db_version": DB_VERSION}
        cursor = self.conn.cursor()
        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                data[table] = [dict(row) for row in cursor.fetchall()]
            except Exception:
                data[table] = []
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return len(data.get("events", []))

    def _backup_dir(self):
        """备份目录：%APPDATA%/DesktopStickyNotes/backups"""
        return os.path.join(os.path.dirname(CONFIG_FILE), "backups")

    def backup_now(self):
        """
        立即备份数据库（使用 SQLite backup API，WAL 安全）

        Returns:
            备份文件路径，失败返回 None
        """
        try:
            backup_dir = self._backup_dir()
            os.makedirs(backup_dir, exist_ok=True)
            dest = os.path.join(
                backup_dir,
                "sticky_notes_%s.db" % datetime.now().strftime("%Y%m%d_%H%M%S"))
            dest_conn = sqlite3.connect(dest)
            with dest_conn:
                self.conn.backup(dest_conn)
            dest_conn.close()
            self._prune_backups(backup_dir)
            return dest
        except Exception as e:
            print(f"[DB] 备份失败: {e}")
            return None

    @staticmethod
    def _prune_backups(backup_dir, keep=7):
        """只保留最近 keep 个备份"""
        try:
            files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir)
                     if f.startswith("sticky_notes_") and f.endswith(".db")]
            files.sort(key=os.path.getmtime, reverse=True)
            for path in files[keep:]:
                os.remove(path)
        except Exception:
            pass

    def _auto_backup(self):
        """启动时自动备份（可在设置中关闭）"""
        try:
            if not self.get_setting('auto_backup_enabled', True):
                return
            self.backup_now()
        except Exception:
            pass

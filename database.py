"""
🗄️ Database - اتصال وإدارة قاعدة البيانات PostgreSQL
يدعم جميع عمليات CRUD للمستخدمين، القنوات، المحتوى، والـ Queue
"""

import asyncpg
import json
import logging
from datetime import date, datetime
from config import config

logger = logging.getLogger(__name__)


class Database:
    """مدير قاعدة البيانات الرئيسي"""

    def __init__(self):
        self.pool: asyncpg.Pool = None

    # ══════════════════════════════════════════
    # الاتصال وإنشاء الجداول
    # ══════════════════════════════════════════

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            config.DATABASE_URL,
            min_size=2,
            max_size=10
        )
        await self._create_tables()
        logger.info("✅ Database connected and tables created")

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Database disconnected")

    async def _create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                -- ===== جدول المستخدمين =====
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    is_banned BOOLEAN DEFAULT FALSE,
                    daily_limit INT DEFAULT 50,
                    channel_limit INT DEFAULT 20,
                    timezone VARCHAR(50) DEFAULT 'Asia/Riyadh',
                    posts_today INT DEFAULT 0,
                    last_post_date DATE DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );

                -- ===== جدول القنوات =====
                CREATE TABLE IF NOT EXISTS channels (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
                    channel_id BIGINT NOT NULL,
                    channel_name VARCHAR(255),
                    channel_username VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    added_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, channel_id)
                );

                -- ===== جدول الـ Queue =====
                CREATE TABLE IF NOT EXISTS queue (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
                    content_type VARCHAR(50) NOT NULL,
                    content_data JSONB NOT NULL,
                    priority INT DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'pending',
                    target_channels JSONB,
                    scheduled_at TIMESTAMP,
                    published_at TIMESTAMP,
                    content_hash VARCHAR(64),
                    created_at TIMESTAMP DEFAULT NOW()
                );

                -- ===== جدول سجل النشر =====
                CREATE TABLE IF NOT EXISTS publish_log (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    queue_id INT REFERENCES queue(id) ON DELETE SET NULL,
                    channel_id BIGINT NOT NULL,
                    content_type VARCHAR(50),
                    status VARCHAR(20) DEFAULT 'success',
                    error_message TEXT,
                    published_at TIMESTAMP DEFAULT NOW()
                );

                -- ===== جدول إعدادات النشر التلقائي =====
                CREATE TABLE IF NOT EXISTS auto_publish_settings (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
                    is_enabled BOOLEAN DEFAULT FALSE,
                    posts_per_day INT DEFAULT 10,
                    publish_times JSONB DEFAULT '[]'::jsonb,
                    template TEXT,
                    updated_at TIMESTAMP DEFAULT NOW()
                );

                -- ===== الفهارس =====
                CREATE INDEX IF NOT EXISTS idx_queue_user_status
                    ON queue(user_id, status);
                CREATE INDEX IF NOT EXISTS idx_queue_scheduled
                    ON queue(scheduled_at) WHERE status = 'pending';
                CREATE INDEX IF NOT EXISTS idx_queue_hash
                    ON queue(content_hash);
                CREATE INDEX IF NOT EXISTS idx_channels_user
                    ON channels(user_id);
                CREATE INDEX IF NOT EXISTS idx_publish_log_user
                    ON publish_log(user_id, published_at);
            """)

    # ══════════════════════════════════════════
    # عمليات المستخدمين
    # ══════════════════════════════════════════

    async def get_or_create_user(self, telegram_id: int, username: str = None,
                                  first_name: str = None) -> dict:
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1", telegram_id
            )
            if user:
                await conn.execute(
                    """UPDATE users SET username = $2, first_name = $3,
                       updated_at = NOW() WHERE telegram_id = $1""",
                    telegram_id, username, first_name
                )
                return dict(user)
            else:
                user = await conn.fetchrow(
                    """INSERT INTO users (telegram_id, username, first_name,
                       daily_limit, channel_limit)
                       VALUES ($1, $2, $3, $4, $5) RETURNING *""",
                    telegram_id, username, first_name,
                    config.DEFAULT_DAILY_LIMIT, config.DEFAULT_CHANNEL_LIMIT
                )
                return dict(user)

    async def get_user(self, telegram_id: int) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1", telegram_id
            )
            return dict(row) if row else None

    async def is_user_banned(self, telegram_id: int) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchval(
                "SELECT is_banned FROM users WHERE telegram_id = $1",
                telegram_id
            )
            return row is True

    async def set_user_banned(self, telegram_id: int, banned: bool):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_banned = $2 WHERE telegram_id = $1",
                telegram_id, banned
            )

    async def get_all_users(self) -> list:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users ORDER BY created_at DESC")
            return [dict(r) for r in rows]

    async def get_user_post_count_today(self, telegram_id: int) -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT posts_today, last_post_date FROM users WHERE telegram_id = $1",
                telegram_id
            )
            if not row:
                return 0
            if row["last_post_date"] != date.today():
                await conn.execute(
                    """UPDATE users SET posts_today = 0,
                       last_post_date = CURRENT_DATE
                       WHERE telegram_id = $1""",
                    telegram_id
                )
                return 0
            return row["posts_today"]

    async def increment_post_count(self, telegram_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE users SET
                   posts_today = CASE
                       WHEN last_post_date = CURRENT_DATE THEN posts_today + 1
                       ELSE 1
                   END,
                   last_post_date = CURRENT_DATE
                   WHERE telegram_id = $1""",
                telegram_id
            )

    async def update_user_timezone(self, telegram_id: int, timezone: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET timezone = $2 WHERE telegram_id = $1",
                telegram_id, timezone
            )

    async def update_user_daily_limit(self, telegram_id: int, limit: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET daily_limit = $2 WHERE telegram_id = $1",
                telegram_id, limit
            )

    # ══════════════════════════════════════════
    # عمليات القنوات
    # ══════════════════════════════════════════

    async def add_channel(self, user_id: int, channel_id: int,
                          channel_name: str, channel_username: str = None) -> bool:
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """INSERT INTO channels (user_id, channel_id, channel_name, channel_username)
                       VALUES ($1, $2, $3, $4)
                       ON CONFLICT (user_id, channel_id) DO UPDATE
                       SET channel_name = $3, channel_username = $4, is_active = TRUE""",
                    user_id, channel_id, channel_name, channel_username
                )
                return True
            except Exception as e:
                logger.error(f"Error adding channel: {e}")
                return False

    async def remove_channel(self, user_id: int, channel_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM channels WHERE user_id = $1 AND channel_id = $2",
                user_id, channel_id
            )
            return result != "DELETE 0"

    async def get_user_channels(self, user_id: int) -> list:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM channels
                   WHERE user_id = $1 AND is_active = TRUE
                   ORDER BY added_at""",
                user_id
            )
            return [dict(r) for r in rows]

    async def get_channel(self, user_id: int, channel_id: int) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM channels WHERE user_id = $1 AND channel_id = $2",
                user_id, channel_id
            )
            return dict(row) if row else None

    # ══════════════════════════════════════════
    # عمليات الـ Queue
    # ══════════════════════════════════════════

    async def add_to_queue(self, user_id: int, content_type: str,
                           content_data: dict, priority: int = 0,
                           target_channels: list = None,
                           scheduled_at: datetime = None,
                           content_hash: str = None) -> int:
        async with self.pool.acquire() as conn:
            # منع التكرار
            if content_hash:
                existing = await conn.fetchval(
                    """SELECT id FROM queue
                       WHERE user_id = $1 AND content_hash = $2
                       AND status = 'pending'""",
                    user_id, content_hash
                )
                if existing:
                    return -1  # محتوى مكرر

            row = await conn.fetchrow(
                """INSERT INTO queue
                   (user_id, content_type, content_data, priority,
                    target_channels, scheduled_at, content_hash)
                   VALUES ($1, $2, $3::jsonb, $4, $5::jsonb, $6, $7)
                   RETURNING id""",
                user_id, content_type, json.dumps(content_data), priority,
                json.dumps(target_channels) if target_channels else None,
                scheduled_at, content_hash
            )
            return row["id"]

    async def get_pending_queue(self, user_id: int, limit: int = 20) -> list:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM queue
                   WHERE user_id = $1 AND status = 'pending'
                   ORDER BY priority DESC, created_at ASC
                   LIMIT $2""",
                user_id, limit
            )
            return [dict(r) for r in rows]

    async def get_scheduled_posts(self, before_time: datetime) -> list:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT q.*, u.timezone, u.daily_limit, u.posts_today,
                          u.last_post_date, u.is_banned
                   FROM queue q
                   JOIN users u ON q.user_id = u.telegram_id
                   WHERE q.status = 'pending'
                   AND q.scheduled_at IS NOT NULL
                   AND q.scheduled_at <= $1
                   AND u.is_banned = FALSE
                   ORDER BY q.priority DESC, q.scheduled_at ASC""",
                before_time
            )
            return [dict(r) for r in rows]

    async def get_next_in_queue(self, user_id: int, count: int = 1) -> list:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM queue
                   WHERE user_id = $1 AND status = 'pending'
                   AND (scheduled_at IS NULL OR scheduled_at <= NOW())
                   ORDER BY priority DESC, created_at ASC
                   LIMIT $2""",
                user_id, count
            )
            return [dict(r) for r in rows]

    async def mark_as_published(self, queue_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE queue SET status = 'published',
                   published_at = NOW() WHERE id = $1""",
                queue_id
            )

    async def mark_as_failed(self, queue_id: int, error: str = None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE queue SET status = 'failed' WHERE id = $1",
                queue_id
            )

    async def delete_from_queue(self, queue_id: int, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM queue WHERE id = $1 AND user_id = $2",
                queue_id, user_id
            )
            return result != "DELETE 0"

    async def clear_user_queue(self, user_id: int) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM queue WHERE user_id = $1 AND status = 'pending'",
                user_id
            )
            count = int(result.split()[-1])
            return count

    async def get_queue_count(self, user_id: int) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM queue WHERE user_id = $1 AND status = 'pending'",
                user_id
            )

    # ══════════════════════════════════════════
    # سجل النشر
    # ══════════════════════════════════════════

    async def add_publish_log(self, user_id: int, queue_id: int,
                               channel_id: int, content_type: str,
                               status: str = "success", error_message: str = None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO publish_log
                   (user_id, queue_id, channel_id, content_type, status, error_message)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                user_id, queue_id, channel_id, content_type, status, error_message
            )

    async def get_user_stats(self, user_id: int) -> dict:
        async with self.pool.acquire() as conn:
            total_published = await conn.fetchval(
                """SELECT COUNT(*) FROM publish_log
                   WHERE user_id = $1 AND status = 'success'""",
                user_id
            )
            today_published = await conn.fetchval(
                """SELECT COUNT(*) FROM publish_log
                   WHERE user_id = $1 AND status = 'success'
                   AND published_at::date = CURRENT_DATE""",
                user_id
            )
            pending = await conn.fetchval(
                "SELECT COUNT(*) FROM queue WHERE user_id = $1 AND status = 'pending'",
                user_id
            )
            channels = await conn.fetchval(
                "SELECT COUNT(*) FROM channels WHERE user_id = $1 AND is_active = TRUE",
                user_id
            )
            failed = await conn.fetchval(
                """SELECT COUNT(*) FROM publish_log
                   WHERE user_id = $1 AND status = 'failed'""",
                user_id
            )
            return {
                "total_published": total_published or 0,
                "today_published": today_published or 0,
                "pending_queue": pending or 0,
                "active_channels": channels or 0,
                "failed_posts": failed or 0
            }

    # ══════════════════════════════════════════
    # إعدادات النشر التلقائي
    # ══════════════════════════════════════════

    async def get_auto_publish_settings(self, user_id: int) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM auto_publish_settings WHERE user_id = $1",
                user_id
            )
            if row:
                return dict(row)
            # إنشاء إعدادات افتراضية
            row = await conn.fetchrow(
                """INSERT INTO auto_publish_settings (user_id)
                   VALUES ($1) RETURNING *""",
                user_id
            )
            return dict(row)

    async def update_auto_publish_settings(self, user_id: int, **kwargs):
        async with self.pool.acquire() as conn:
            settings = await self.get_auto_publish_settings(user_id)
            fields = []
            values = [user_id]
            i = 2
            for key, value in kwargs.items():
                if key in ("is_enabled", "posts_per_day", "publish_times", "template"):
                    if key == "publish_times":
                        fields.append(f"{key} = ${i}::jsonb")
                        values.append(json.dumps(value))
                    else:
                        fields.append(f"{key} = ${i}")
                        values.append(value)
                    i += 1
            if fields:
                fields.append(f"updated_at = NOW()")
                query = f"UPDATE auto_publish_settings SET {', '.join(fields)} WHERE user_id = $1"
                await conn.execute(query, *values)

    # ══════════════════════════════════════════
    # إحصائيات المالك
    # ══════════════════════════════════════════

    async def get_global_stats(self) -> dict:
        async with self.pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            active_users = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE is_banned = FALSE"
            )
            total_channels = await conn.fetchval("SELECT COUNT(*) FROM channels WHERE is_active = TRUE")
            total_published = await conn.fetchval(
                "SELECT COUNT(*) FROM publish_log WHERE status = 'success'"
            )
            total_pending = await conn.fetchval(
                "SELECT COUNT(*) FROM queue WHERE status = 'pending'"
            )
            today_published = await conn.fetchval(
                """SELECT COUNT(*) FROM publish_log
                   WHERE status = 'success'
                   AND published_at::date =
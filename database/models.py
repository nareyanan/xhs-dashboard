import sqlite3
import logging
import os

from config import DB_FILE, DATA_DIR

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """DB 테이블 초기화"""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                brand       TEXT NOT NULL,
                keyword     TEXT NOT NULL,
                type        TEXT NOT NULL,   -- 'search' | 'hashtag'
                post_count  INTEGER DEFAULT 0,
                view_count  INTEGER DEFAULT 0,
                has_error   INTEGER DEFAULT 0,
                error_msg   TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, brand, keyword, type)
            );

            CREATE TABLE IF NOT EXISTS posts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                collected_at TEXT NOT NULL,
                brand        TEXT NOT NULL,
                keyword      TEXT NOT NULL,
                post_id      TEXT,
                title        TEXT,
                likes        INTEGER DEFAULT 0,
                comments     INTEGER DEFAULT 0,
                collects     INTEGER DEFAULT 0,
                author       TEXT,
                url          TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);
            CREATE INDEX IF NOT EXISTS idx_posts_collected_at ON posts(collected_at);
            CREATE INDEX IF NOT EXISTS idx_posts_brand ON posts(brand);
        """)
        conn.commit()
        logger.info("DB 초기화 완료")
    finally:
        conn.close()

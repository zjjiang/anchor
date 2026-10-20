"""SQLite 连接与建库：数据不出墙，路径可用 ANCHOR_DB 环境变量覆盖。

规矩：
- WAL + 外键 + busy_timeout，全部幂等建库（CREATE TABLE IF NOT EXISTS）
- SCHEMA_VERSION + schema_version 表：当前不做自动迁移，版本不符时显式报错
- 业务规则不在这里（校验在 domain.py 与各 store 文件），这里只管连接与事务
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("ANCHOR_DB", "data/anchor.db"))

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS checkins (
    id          TEXT PRIMARY KEY,
    checkin_date TEXT NOT NULL,
    raw_text    TEXT NOT NULL,
    fact        TEXT,
    feeling     TEXT,
    worry       TEXT,
    speculation TEXT,
    next_action TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pressures (
    id         TEXT PRIMARY KEY,
    occurred_at TEXT NOT NULL,
    domain     TEXT NOT NULL,
    is_preset  INTEGER NOT NULL DEFAULT 1,
    note       TEXT NOT NULL,
    checkin_id TEXT REFERENCES checkins(id),
    intensity  INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patterns (
    id          TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',
    evidence    TEXT NOT NULL DEFAULT '[]',
    note        TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS weekly_reviews (
    id                 TEXT PRIMARY KEY,
    week_start         TEXT NOT NULL,
    main_sources       TEXT NOT NULL,
    recurring          TEXT NOT NULL,
    easing_vs_worsening TEXT NOT NULL,
    improved           TEXT NOT NULL,
    focus_next         TEXT NOT NULL,
    narrative          TEXT NOT NULL,
    replaced_at        TEXT,
    created_at         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pressures_time ON pressures(occurred_at);
CREATE INDEX IF NOT EXISTS idx_pressures_checkin ON pressures(checkin_id);
CREATE INDEX IF NOT EXISTS idx_checkins_date ON checkins(checkin_date);
CREATE INDEX IF NOT EXISTS idx_reviews_week ON weekly_reviews(week_start);
"""

_CST = timezone(timedelta(hours=8))


def now_utc_iso() -> str:
    """当前 UTC 时间，ISO 字符串（时间戳口径）。"""
    return datetime.now(UTC).isoformat(timespec="seconds")


def utcnow_dt() -> datetime:
    """当前 UTC datetime（窗口计算用）。"""
    return datetime.now(UTC)


def today_cst() -> str:
    """东八区日历日 YYYY-MM-DD（checkin_date / first_seen 口径）。"""
    return datetime.now(_CST).strftime("%Y-%m-%d")


def get_conn() -> sqlite3.Connection:
    """新建连接：调用方负责关闭，或配合 transaction() 使用。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def transaction():
    """事务上下文：成功提交、异常回滚并上抛。"""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def next_id(conn: sqlite3.Connection, table: str, prefix: str) -> str:
    """表内递增的人类可读 id（c1 / p1 / pt1 / w1），按数字后缀取最大 +1。"""
    row = conn.execute(
        f"SELECT COALESCE(MAX(CAST(SUBSTR(id, ?) AS INTEGER)), 0) AS n FROM {table}",
        (len(prefix) + 1,),
    ).fetchone()
    return f"{prefix}{row['n'] + 1}"


def init_db() -> None:
    """幂等建库；已有库版本高于代码时显式报错（不做自动降级/迁移）。"""
    with transaction() as conn:
        conn.executescript(_SCHEMA)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        elif row["version"] > SCHEMA_VERSION:
            raise RuntimeError(
                f"数据库版本 {row['version']} 高于代码版本 {SCHEMA_VERSION}，"
                "请升级代码后再运行（数据不出墙，禁止降级覆盖）"
            )

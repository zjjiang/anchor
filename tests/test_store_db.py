"""store.db：建库幂等、版本守卫、时间口径。"""

from __future__ import annotations

import re
from datetime import UTC

import pytest


def test_fresh_build_creates_all_tables(fresh_db):
    with fresh_db.get_conn() as conn:
        names = {
            r["name"]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {"schema_version", "checkins", "pressures", "patterns", "weekly_reviews"} <= names


def test_init_db_is_idempotent(fresh_db):
    fresh_db.init_db()
    fresh_db.init_db()  # 不抛错即幂等
    with fresh_db.get_conn() as conn:
        (row,) = conn.execute("SELECT version FROM schema_version").fetchall()
    assert row["version"] == fresh_db.SCHEMA_VERSION


def test_init_db_rejects_newer_db(fresh_db):
    with fresh_db.transaction() as conn:
        conn.execute("UPDATE schema_version SET version = ?", (fresh_db.SCHEMA_VERSION + 1,))
    with pytest.raises(RuntimeError, match="高于代码版本"):
        fresh_db.init_db()


def test_now_utc_iso_format(fresh_db):
    value = fresh_db.now_utc_iso()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", value)


def test_today_cst_is_cst_calendar_day(fresh_db):
    from datetime import datetime, timedelta

    value = fresh_db.today_cst()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
    utc_now = datetime.now(UTC)
    cst_date = (utc_now + timedelta(hours=8)).strftime("%Y-%m-%d")
    assert value == cst_date

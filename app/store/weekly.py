"""周复盘存取：同周唯一，重复保存以 replaced 标记保留旧版（不物理删除）。

情绪内容误覆盖代价高：旧版永远可回溯，但查询口径只取未替换版本。
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.store import db

_COLS = (
    "id",
    "week_start",
    "main_sources",
    "recurring",
    "easing_vs_worsening",
    "improved",
    "focus_next",
    "narrative",
    "created_at",
)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in _COLS}


def save(data: dict[str, Any]) -> str:
    """保存一周复盘；该周已有有效复盘时先将其标记 replaced。"""
    week_start = data["week_start"]
    now = db.now_utc_iso()
    with db.transaction() as conn:
        existing = conn.execute(
            "SELECT id FROM weekly_reviews WHERE week_start = ? AND replaced_at IS NULL",
            (week_start,),
        ).fetchone()
        if existing is not None:
            conn.execute(
                "UPDATE weekly_reviews SET replaced_at = ? WHERE id = ?",
                (now, existing["id"]),
            )
        wid = db.next_id(conn, "weekly_reviews", "w")
        conn.execute(
            f"INSERT INTO weekly_reviews ({', '.join(_COLS)}) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                wid,
                week_start,
                data["main_sources"],
                data["recurring"],
                data["easing_vs_worsening"],
                data["improved"],
                data["focus_next"],
                data["narrative"],
                now,
            ),
        )
    return wid


def get_by_week(week_start: str) -> dict[str, Any] | None:
    """某周的有效复盘（未替换版本），无则 None。"""
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM weekly_reviews WHERE week_start = ? AND replaced_at IS NULL",
            (week_start,),
        ).fetchone()
    return _row_to_dict(row) if row is not None else None


def list_reviews() -> list[dict[str, Any]]:
    """历史复盘列表（仅有效版本），week_start 倒序。"""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM weekly_reviews WHERE replaced_at IS NULL "
            "ORDER BY week_start DESC, id DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]

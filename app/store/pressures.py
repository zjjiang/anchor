"""压力记录存取：独立落库、check-in 关联校验、窗口聚合（分布 + 明细 + 兜底域）。

明细只到 note 为止，永不带出 check-in 原文或 digest。
"""

from __future__ import annotations

import sqlite3
from datetime import timedelta
from typing import Any

from app import domain
from app.store import db

_INSERT_COLS = ("id", "occurred_at", "domain", "is_preset", "note", "checkin_id", "intensity", "created_at")


def insert_pressure_row(
    conn: sqlite3.Connection, entry: dict[str, Any], *, checkin_id: str | None = None
) -> str:
    """在既有事务/连接内写入一条压力记录（供本模块与 checkins 原子附带共用）。"""
    if checkin_id is None:
        checkin_id = entry.get("checkin_id")
    value = domain.normalize_domain(entry.get("domain"))
    preset = domain.is_preset_domain(value)
    intensity = domain.validate_intensity(entry.get("intensity"))
    note = entry.get("note")
    if not isinstance(note, str) or not note.strip():
        raise domain.DomainError("压力条目 note 不能为空")
    if checkin_id is not None:
        exists = conn.execute(
            "SELECT 1 FROM checkins WHERE id = ?", (checkin_id,)
        ).fetchone()
        if exists is None:
            raise domain.DomainError(f"关联的 check-in 不存在：{checkin_id}")
    pid = db.next_id(conn, "pressures", "p")
    conn.execute(
        f"INSERT INTO pressures ({', '.join(_INSERT_COLS)}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            pid,
            entry.get("occurred_at") or db.now_utc_iso(),
            value,
            int(preset),
            note.strip(),
            checkin_id,
            intensity,
            db.now_utc_iso(),
        ),
    )
    return pid


def insert(entry: dict[str, Any]) -> str:
    """独立写入一条压力记录（不经 check-in）。"""
    with db.transaction() as conn:
        return insert_pressure_row(conn, entry)


def list_window(days: int = 30) -> dict[str, Any]:
    """近 N 天聚合：按领域计数分布、时间线明细、非预置领域清单。"""
    since = (db.utcnow_dt() - timedelta(days=days)).isoformat(timespec="seconds")
    with db.get_conn() as conn:
        distribution = [
            {"domain": r["domain"], "count": r["n"]}
            for r in conn.execute(
                "SELECT domain, COUNT(*) AS n FROM pressures WHERE occurred_at >= ? "
                "GROUP BY domain ORDER BY n DESC, domain",
                (since,),
            )
        ]
        timeline = [
            {
                "id": r["id"],
                "occurred_at": r["occurred_at"],
                "domain": r["domain"],
                "is_preset": bool(r["is_preset"]),
                "note": r["note"],
                "checkin_id": r["checkin_id"],
                "intensity": r["intensity"],
            }
            for r in conn.execute(
                "SELECT * FROM pressures WHERE occurred_at >= ? ORDER BY occurred_at DESC, id DESC",
                (since,),
            )
        ]
    custom = sorted({t["domain"] for t in timeline if not t["is_preset"]})
    return {"distribution": distribution, "timeline": timeline, "custom_domains": custom}

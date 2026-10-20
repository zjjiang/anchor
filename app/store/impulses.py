"""冲动决策检查点存取：记录 → 24h → 回填，executed/dropped 比例是本模块的真正产出。

规矩：
- resolve 是唯一状态迁移通道（open → executed/dropped），无内容改写、无删除
- stale 是查询时派生（open 且已过 decision_due），不落库、不靠后台任务
- 统计口径：executed_ratio = executed / (executed + dropped)，open 不进分母
"""

from __future__ import annotations

import sqlite3
from datetime import timedelta
from typing import Any

from app import domain
from app.store import db

_COLS = (
    "id",
    "occurred_at",
    "kind",
    "claim",
    "amount",
    "emotion_level",
    "note",
    "status",
    "decision_due",
    "decided_at",
    "created_at",
)


def _row_to_dict(row: sqlite3.Row, *, now: str) -> dict[str, Any]:
    record = {key: row[key] for key in _COLS}
    record["is_custom_kind"] = not domain.is_preset_impulse_kind(row["kind"])
    record["stale"] = row["status"] == "open" and row["decision_due"] < now
    return record


def insert(data: dict[str, Any]) -> str:
    """落一条 open 检查点：claim 必填，decision_due = occurred_at + 24h。"""
    claim = data.get("claim")
    if not isinstance(claim, str) or not claim.strip():
        raise domain.DomainError("claim（想做什么）不能为空")
    kind = domain.normalize_impulse_kind(data.get("kind"))
    amount = data.get("amount")
    if amount is not None and (isinstance(amount, bool) or not isinstance(amount, (int, float))):
        raise domain.DomainError("amount 必须是数字")
    emotion_level = domain.validate_intensity(data.get("emotion_level"))
    note = data.get("note")
    if note is not None and not isinstance(note, str):
        raise domain.DomainError("note 必须是字符串")

    occurred_at = data.get("occurred_at") or db.now_utc_iso()
    decision_due = (
        __import__("datetime").datetime.fromisoformat(occurred_at)
        + timedelta(hours=domain.IMPULSIVE_WINDOW_HOURS)
    ).isoformat(timespec="seconds")
    with db.transaction() as conn:
        iid = db.next_id(conn, "impulses", "i")
        conn.execute(
            "INSERT INTO impulses (id, occurred_at, kind, is_custom_kind, claim, amount, "
            "emotion_level, note, status, decision_due, decided_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, NULL, ?)",
            (
                iid,
                occurred_at,
                kind,
                int(domain.is_preset_impulse_kind(kind)),
                claim.strip(),
                amount,
                emotion_level,
                note,
                decision_due,
                db.now_utc_iso(),
            ),
        )
    return iid


def resolve(impulse_id: str, outcome: str, *, note: str | None = None) -> None:
    """回填结果：open → executed/dropped，记录 decided_at；非 open 或不存在拒绝。"""
    domain.validate_outcome(outcome)
    if note is not None and not isinstance(note, str):
        raise domain.DomainError("note 必须是字符串")
    with db.transaction() as conn:
        row = conn.execute("SELECT status FROM impulses WHERE id = ?", (impulse_id,)).fetchone()
        if row is None:
            raise KeyError(impulse_id)
        if row["status"] != "open":
            raise domain.DomainError("该冲动已回填过，不能重复回填")
        conn.execute(
            "UPDATE impulses SET status = ?, decided_at = ?, "
            "note = COALESCE(?, note) WHERE id = ?",
            (outcome, db.now_utc_iso(), note, impulse_id),
        )


def get(impulse_id: str) -> dict[str, Any]:
    """单条详情。"""
    now = db.now_utc_iso()
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM impulses WHERE id = ?", (impulse_id,)).fetchone()
    if row is None:
        raise KeyError(impulse_id)
    return _row_to_dict(row, now=now)


def list_window(days: int = 30) -> dict[str, Any]:
    """近 N 天清单（倒序）+ 统计；stale 查询时派生，open 不进比例分母。"""
    since = (db.utcnow_dt() - timedelta(days=days)).isoformat(timespec="seconds")
    now = db.now_utc_iso()
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM impulses WHERE occurred_at >= ? ORDER BY occurred_at DESC, id DESC",
            (since,),
        ).fetchall()
    items = [_row_to_dict(r, now=now) for r in rows]
    counts = {"executed": 0, "dropped": 0, "open": 0}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    decided = counts["executed"] + counts["dropped"]
    stats = {
        "total": len(items),
        "executed": counts["executed"],
        "dropped": counts["dropped"],
        "open": counts["open"],
        "executed_ratio": counts["executed"] / decided if decided else None,
    }
    return {"items": items, "stats": stats}

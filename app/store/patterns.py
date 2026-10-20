"""模式记录存取：重复压力/行为模式的人工修养式沉淀。

规矩：
- first_seen / last_seen 由系统维护（东八区日历日），不接受外部赋值
- evidence 是 check-in id 列表，写入前逐一校验存在性
- 状态三态 active / watched / resolved，无删除通道
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app import domain
from app.store import db

_COLS = ("id", "description", "status", "note", "first_seen", "last_seen", "created_at")


def _row_to_dict(row: sqlite3.Row, *, with_evidence: bool) -> dict[str, Any]:
    record = {key: row[key] for key in _COLS}
    evidence = json.loads(row["evidence"])
    if with_evidence:
        record["evidence"] = evidence
    else:
        record["evidence_count"] = len(evidence)
    return record


def _get(conn: sqlite3.Connection, pattern_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM patterns WHERE id = ?", (pattern_id,)).fetchone()
    if row is None:
        raise KeyError(f"模式不存在：{pattern_id}")
    return row


def _validate_evidence(conn: sqlite3.Connection, evidence: list[str]) -> list[str]:
    """evidence 逐一校验 check-in 存在性，任一非法整体拒绝。"""
    for cid in evidence:
        exists = conn.execute("SELECT 1 FROM checkins WHERE id = ?", (cid,)).fetchone()
        if exists is None:
            raise domain.DomainError(f"证据 check-in 不存在：{cid}")
    return list(evidence)


def insert(data: dict[str, Any]) -> str:
    """新建模式：description 必填，evidence 可选，状态默认 active。"""
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        raise domain.DomainError("模式描述不能为空")
    status = domain.validate_status(data.get("status") or "active")
    note = data.get("note")
    if note is not None and not isinstance(note, str):
        raise domain.DomainError("note 必须是字符串")
    evidence = data.get("evidence") or []
    if not isinstance(evidence, list) or not all(isinstance(c, str) for c in evidence):
        raise domain.DomainError("evidence 必须是 check-in id 列表")
    today = db.today_cst()
    with db.transaction() as conn:
        _validate_evidence(conn, evidence)
        pid = db.next_id(conn, "patterns", "pt")
        conn.execute(
            "INSERT INTO patterns (id, description, status, evidence, note, first_seen, last_seen, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                pid,
                description.strip(),
                status,
                json.dumps(evidence),
                note,
                today,
                today,
                db.now_utc_iso(),
            ),
        )
    return pid


def update_status(pattern_id: str, status: str) -> None:
    """状态流转（合法三态之一），并刷新 last_seen。"""
    domain.validate_status(status)
    with db.transaction() as conn:
        _get(conn, pattern_id)
        conn.execute(
            "UPDATE patterns SET status = ?, last_seen = ? WHERE id = ?",
            (status, db.today_cst(), pattern_id),
        )


def update_note(pattern_id: str, note: str) -> None:
    """补充观察说明，并刷新 last_seen。"""
    if not isinstance(note, str) or not note.strip():
        raise domain.DomainError("note 不能为空")
    with db.transaction() as conn:
        _get(conn, pattern_id)
        conn.execute(
            "UPDATE patterns SET note = ?, last_seen = ? WHERE id = ?",
            (note.strip(), db.today_cst(), pattern_id),
        )


def get(pattern_id: str) -> dict[str, Any]:
    """单条详情（含 evidence 明细）。"""
    with db.get_conn() as conn:
        return _row_to_dict(_get(conn, pattern_id), with_evidence=True)


def list_all() -> list[dict[str, Any]]:
    """全量列表（evidence 只给数量），last_seen 倒序。"""
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM patterns ORDER BY last_seen DESC, id DESC").fetchall()
    return [_row_to_dict(r, with_evidence=False) for r in rows]


def list_by_status(status: str) -> list[dict[str, Any]]:
    """按状态过滤的列表。"""
    domain.validate_status(status)
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM patterns WHERE status = ? ORDER BY last_seen DESC, id DESC",
            (status,),
        ).fetchall()
    return [_row_to_dict(r, with_evidence=False) for r in rows]

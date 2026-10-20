"""check-in 存取：落库（含附带压力原子写入）、详情、摘要列表。

规矩：raw_text 一经写入永不改删（无 UPDATE/DELETE 通道）；
附带 pressures 与 check-in 同事务，任一非法整体回滚。
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.store import db
from app.store.pressures import insert_pressure_row

_CHECKIN_COLS = (
    "id",
    "checkin_date",
    "raw_text",
    "fact",
    "feeling",
    "worry",
    "speculation",
    "next_action",
    "created_at",
)


def insert(data: dict[str, Any]) -> str:
    """写入一条 check-in；附带 pressures 原子落库并回填 checkin_id。"""
    with db.transaction() as conn:
        cid = db.next_id(conn, "checkins", "c")
        conn.execute(
            f"INSERT INTO checkins ({', '.join(_CHECKIN_COLS)}) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                cid,
                data["checkin_date"],
                data["raw_text"],
                data.get("fact"),
                data.get("feeling"),
                data.get("worry"),
                data.get("speculation"),
                data.get("next_action"),
                db.now_utc_iso(),
            ),
        )
        for entry in data.get("pressures", []):
            insert_pressure_row(conn, entry, checkin_id=cid)
    return cid


def _row_to_dict(row: sqlite3.Row, *, with_raw: bool) -> dict[str, Any]:
    record = {key: row[key] for key in _CHECKIN_COLS if key != "raw_text" or with_raw}
    return record


def get(checkin_id: str) -> dict[str, Any]:
    """单条详情（含 raw_text，仅 MCP 详情用），附带该条关联的压力领域。"""
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM checkins WHERE id = ?", (checkin_id,)).fetchone()
        if row is None:
            raise KeyError(f"check-in 不存在：{checkin_id}")
        domains = [
            r["domain"]
            for r in conn.execute(
                "SELECT domain FROM pressures WHERE checkin_id = ? ORDER BY occurred_at",
                (checkin_id,),
            )
        ]
    record = _row_to_dict(row, with_raw=True)
    record["pressure_domains"] = domains
    return record


def list_range(start_date: str, end_date: str) -> list[dict[str, Any]]:
    """日期窗口摘要（不含 raw_text），按日期倒序，附压力领域。"""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM checkins WHERE checkin_date >= ? AND checkin_date <= ? "
            "ORDER BY checkin_date DESC, id DESC",
            (start_date, end_date),
        ).fetchall()
        links: dict[str, list[str]] = {}
        for r in conn.execute(
            "SELECT checkin_id, domain FROM pressures WHERE checkin_id IS NOT NULL "
            "ORDER BY occurred_at"
        ):
            links.setdefault(r["checkin_id"], []).append(r["domain"])
    result = []
    for row in rows:
        record = _row_to_dict(row, with_raw=False)
        record["pressure_domains"] = links.get(row["id"], [])
        result.append(record)
    return result

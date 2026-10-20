"""check-in 模块：payload 校验与摘要（纯函数，零 IO）。

梳理框架即工具 schema：龙虾陪聊后按五槽位组织参数才能落库；
槽位可留空（不逼填），但 raw_text 必须有。
"""

from __future__ import annotations

from typing import Any

from app import domain
from app.store import db

SUMMARY_FIELDS = (
    "id",
    "checkin_date",
    *domain.DIGEST_SLOTS,
    "created_at",
)


def validate_checkin_date(value: Any) -> str:
    """日历日 YYYY-MM-DD 校验。"""
    if not isinstance(value, str) or len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise domain.DomainError("日期格式必须是 YYYY-MM-DD")
    try:
        from datetime import date

        date.fromisoformat(value)
    except ValueError as exc:
        raise domain.DomainError(f"日期不合法：{value}") from exc
    return value


def validate_pressure_entry(entry: Any) -> dict[str, Any]:
    """单条附带压力归类校验（不落库，只归一）。"""
    if not isinstance(entry, dict):
        raise domain.DomainError("压力条目必须是对象")
    note = entry.get("note")
    if not isinstance(note, str) or not note.strip():
        raise domain.DomainError("压力条目 note 不能为空")
    value = domain.normalize_domain(entry.get("domain"))
    normalized: dict[str, Any] = {
        "domain": value,
        "is_preset": domain.is_preset_domain(value),
        "note": note.strip(),
        "intensity": domain.validate_intensity(entry.get("intensity")),
        "checkin_id": None,
    }
    if isinstance(entry.get("occurred_at"), str) and entry["occurred_at"].strip():
        normalized["occurred_at"] = entry["occurred_at"].strip()
    return normalized


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """log_checkin 入参校验与归一：raw_text 必填，五槽位可选，附带压力条目。"""
    if not isinstance(payload, dict):
        raise domain.DomainError("入参必须是对象")
    raw_text = payload.get("raw_text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise domain.DomainError("raw_text（原话）不能为空")

    checkin_date = payload.get("checkin_date")
    data: dict[str, Any] = {
        "raw_text": raw_text.strip(),
        "checkin_date": (
            validate_checkin_date(checkin_date)
            if checkin_date is not None
            else db.today_cst()
        ),
    }
    for slot in domain.DIGEST_SLOTS:
        data[slot] = domain.validate_digest_slot(slot, payload.get(slot))

    pressures = payload.get("pressures") or []
    if not isinstance(pressures, list):
        raise domain.DomainError("pressures 必须是列表")
    data["pressures"] = [validate_pressure_entry(entry) for entry in pressures]
    return data


def summarize(row: dict[str, Any]) -> dict[str, Any]:
    """check-in 摘要：不含 raw_text（看板与列表用）。"""
    summary = {key: row.get(key) for key in SUMMARY_FIELDS}
    summary["pressure_domains"] = row.get("pressure_domains") or []
    return summary


def detail(row: dict[str, Any]) -> dict[str, Any]:
    """check-in 详情：含 raw_text，仅 MCP 单条详情返回。"""
    return {key: row.get(key) for key in (*SUMMARY_FIELDS, "raw_text")}

"""weekly 模块：周口径、数据包聚合、复盘入参校验（纯函数，零 IO）。

周复盘五问：主要压力来源 / 重复出现的问题 / 缓解 vs 恶化 / 本周改善 / 下周最值得关注的一件事。
数据包不含 raw_text——周复盘永远不需要原文。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app import domain
from app.modules.checkin import validate_checkin_date

REVIEW_QUESTIONS = (
    "main_sources",
    "recurring",
    "easing_vs_worsening",
    "improved",
    "focus_next",
)

_CST = timezone(timedelta(hours=8))


def week_start_of(value: str | None) -> str:
    """东八区周起始日（周一）：None 取当前周；显式日期归到所在周的周一。"""
    if value is None:
        today = datetime.now(_CST).date()
        monday = today - timedelta(days=today.weekday())
        return monday.isoformat()
    parsed = date.fromisoformat(validate_checkin_date(value))
    return (parsed - timedelta(days=parsed.weekday())).isoformat()


def build_week_data(
    week_start: str,
    checkins: list[dict[str, Any]],
    pressures: list[dict[str, Any]],
    patterns: list[dict[str, Any]],
) -> dict[str, Any]:
    """聚合一周数据包：check-in 摘要（倒序）、压力分布、逐日计数、活跃模式。

    入参由 store 层按同窗口取出；这里只做过滤、聚合与字段裁剪。
    """
    start = date.fromisoformat(week_start)
    end = start + timedelta(days=6)

    week_checkins = sorted(
        (c for c in checkins if start <= date.fromisoformat(c["checkin_date"]) <= end),
        key=lambda c: (c["checkin_date"], c["id"]),
        reverse=True,
    )
    checkin_summaries = [
        {key: c.get(key) for key in ("id", "checkin_date", "fact", "feeling", "worry",
                                     "speculation", "next_action", "created_at")}
        for c in week_checkins
    ]

    daily_counts: dict[str, int] = {}
    distribution: dict[str, int] = {}
    for p in pressures:
        occurred = p["occurred_at"][:10]
        occurred_date = date.fromisoformat(occurred)
        if not (start <= occurred_date <= end):
            continue
        daily_counts[occurred] = daily_counts.get(occurred, 0) + 1
        distribution[p["domain"]] = distribution.get(p["domain"], 0) + 1

    return {
        "week_start": week_start,
        "checkins": checkin_summaries,
        "pressure_distribution": sorted(
            ({"domain": d, "count": n} for d, n in distribution.items()),
            key=lambda item: (-item["count"], item["domain"]),
        ),
        "daily_counts": dict(sorted(daily_counts.items())),
        "active_patterns": [
            {"description": p.get("description"), "evidence_count": p.get("evidence_count", 0)}
            for p in patterns
        ],
    }


def validate_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """save_weekly_review 入参校验：week_start 合法 + 五问与 narrative 必填。"""
    if not isinstance(payload, dict):
        raise domain.DomainError("入参必须是对象")
    data: dict[str, Any] = {
        "week_start": week_start_of(payload.get("week_start")),
    }
    for field in (*REVIEW_QUESTIONS, "narrative"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise domain.DomainError(f"{field} 不能为空")
        data[field] = value.strip()
    return data

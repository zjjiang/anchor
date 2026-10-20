"""shared_status 模块：唯一跨系统出口的抽象状态构建（纯函数，零 IO）。

隐私红线（契约测试守门）：返回字段白名单化——枚举、计数、日期、规则模板句，
永不包含 check-in 原文、digest、压力 note、模式 description 等任何自由文本。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app import domain

_CST = timezone(timedelta(hours=8))

_NOTE_TEMPLATES = {
    "low": "近期状态平稳。",
    "mid": "近期压力有所上升，主要在{domains}，建议留意负荷。",
    "high": "近期压力偏高，主要在{domains}，建议本周降低额外承诺、优先恢复精力。",
}


def build_shared_status(
    *,
    days: int,
    distribution: list[dict[str, Any]],
    intensities: list[int | None],
    checkin_dates: list[str],
) -> dict[str, Any]:
    """构建白名单化的抽象状态。入参由 store 层按窗口取出，这里只做推导与拼装。"""
    count = sum(item["count"] for item in distribution)
    rated = [v for v in intensities if v is not None]
    high_ratio = (
        sum(1 for v in rated if v >= 4) / len(rated) if rated else 0.0
    )
    level = domain.derive_stress_level(count, high_ratio)

    top_domains = sorted(distribution, key=lambda item: (-item["count"], item["domain"]))
    domain_labels = [
        domain.PRESSURE_DOMAIN_LABELS.get(item["domain"], item["domain"])
        for item in top_domains[:2]
    ]
    domains_text = "、".join(domain_labels) if domain_labels else "整体状态"

    if level == "low":
        note = _NOTE_TEMPLATES["low"]
    else:
        note = _NOTE_TEMPLATES[level].format(domains=domains_text)

    return {
        "period": {"days": days},
        "overall_stress_level": level,
        "top_domains": [{"domain": item["domain"], "count": item["count"]} for item in top_domains],
        "checkin_streak": _consecutive_days(checkin_dates),
        "note": note,
    }


def _consecutive_days(checkin_dates: list[str]) -> int:
    """截至今天（东八区）的连续 check-in 天数。"""
    days = {date.fromisoformat(d) for d in checkin_dates if isinstance(d, str) and len(d) == 10}
    streak = 0
    current = datetime.now(_CST).date()
    while current in days:
        streak += 1
        current -= timedelta(days=1)
    return streak

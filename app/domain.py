"""领域常量与校验规则：store / MCP / API 三层共用的唯一出处。

规矩：
- 校验纯函数，零 IO，失败一律抛 DomainError（中文消息）
- 压力领域六域 + free-text 兜底：未知值原样保留并标记非预置，永不硬套
- STRESS_THRESHOLDS 集中定义 shared_status 的三档推导阈值，调参不改 schema
"""

from __future__ import annotations

from typing import Any

DIGEST_SLOTS = ("fact", "feeling", "worry", "speculation", "next_action")

# 六个预置压力领域 → 中文标签
PRESSURE_DOMAIN_LABELS: dict[str, str] = {
    "work": "工作/职业未来",
    "family": "夫妻/家庭关系",
    "relations": "其他关系",
    "money": "金钱",
    "energy": "精力状态",
    "self": "自我评价",
}
PRESSURE_DOMAINS = frozenset(PRESSURE_DOMAIN_LABELS)

PATTERN_STATUSES = frozenset({"active", "watched", "resolved"})

DIGEST_SLOT_MAX_LEN = 2000

# shared_status 压力等级推导阈值（Phase 2 按真实数据调参，不涉 schema）
STRESS_THRESHOLDS: dict[str, float] = {
    "count_low": 3,  # 窗口内条数 ≤ 此值 → low
    "count_high": 10,  # 窗口内条数 > 此值 → high
    "high_intensity_ratio": 0.5,  # intensity≥4 占比超过此值 → high
}

# shared_status 返回字段白名单（隐私红线：多一个自由文本字段都不行；
# impulses 永不进入此白名单——抽象状态保持"状态不事件"）
SHARED_STATUS_FIELDS = frozenset(
    {"period", "overall_stress_level", "top_domains", "checkin_streak", "note"}
)

# 冲动决策类型：四预置 + other 兜底（未知值原样保留，同压力领域模式）
IMPULSE_KIND_LABELS: dict[str, str] = {
    "spending": "大额消费",
    "transfer": "转账",
    "conflict": "激烈争吵",
    "resignation": "辞职",
}
IMPULSE_KINDS = frozenset(IMPULSE_KIND_LABELS) | {"other"}

# 冲动回填结果（状态迁移通道：resolve_impulse 是唯一出口）
IMPULSE_OUTCOMES = {"executed": "executed", "dropped": "dropped"}

IMPULSIVE_WINDOW_HOURS = 24

# 冲动检查单模板（固定句式，可带插值；机器可验证"四要素给过"）
IMPULSE_CHECKLIST_TEMPLATES: dict[str, str] = {
    "facts": "先把 {claim} 拆成事实：哪些是已经发生的，哪些是你预计的？",
    "worst_case": "最坏后果：如果做了，最坏会怎样？这个结果一周后还能挽回吗？",
    "future_self": "24 小时视角：睡一觉之后，你还会想这么做吗？先放到现在与 {due} 之间。",
}


class DomainError(ValueError):
    """领域规则违反，消息面向用户（中文）。"""


def normalize_domain(raw: Any) -> str:
    """领域值规范化：预置六域大小写不敏感归一；未知值兜底保留原文。"""
    if not isinstance(raw, str) or not raw.strip():
        raise DomainError("压力领域不能为空")
    value = raw.strip().lower()
    if value in PRESSURE_DOMAINS:
        return value
    if len(value) > 50:
        raise DomainError("压力领域名称过长（最多 50 字符）")
    return value


def is_preset_domain(value: str) -> bool:
    return value in PRESSURE_DOMAINS


def validate_digest_slot(slot: str, value: Any) -> str | None:
    """digest 槽位校验：字符串（≤2000 字符）或 None。"""
    if value is None:
        return None
    if not isinstance(value, str):
        raise DomainError(f"digest 槽位 {slot} 必须是字符串")
    if len(value) > DIGEST_SLOT_MAX_LEN:
        raise DomainError(f"digest 槽位 {slot} 过长（最多 {DIGEST_SLOT_MAX_LEN} 字符）")
    return value


def validate_intensity(value: Any) -> int | None:
    """intensity：1-5 整数或 None。可选项，不要求用户每次打分。"""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise DomainError("intensity 必须是 1-5 的整数")
    if not 1 <= value <= 5:
        raise DomainError("intensity 必须在 1-5 之间")
    return value


def validate_status(value: Any) -> str:
    """模式状态：active / watched / resolved 三态。"""
    if value not in PATTERN_STATUSES:
        raise DomainError(f"模式状态必须是 {'/'.join(sorted(PATTERN_STATUSES))} 之一")
    return value


def normalize_impulse_kind(raw: Any) -> str:
    """冲动类型规范化：预置枚举大小写不敏感归一；未知值兜底保留原文。"""
    if not isinstance(raw, str) or not raw.strip():
        raise DomainError("冲动类型不能为空")
    value = raw.strip().lower()
    if value in IMPULSE_KINDS:
        return value
    if len(value) > 50:
        raise DomainError("冲动类型名称过长（最多 50 字符）")
    return value


def is_preset_impulse_kind(value: str) -> bool:
    return value in IMPULSE_KIND_LABELS


def validate_outcome(value: Any) -> str:
    """冲动回填结果：executed / dropped。"""
    if value not in IMPULSE_OUTCOMES:
        raise DomainError("回填结果必须是 executed（执行了）或 dropped（放弃了）")
    return value


def build_checklist(claim: str, due: str) -> dict[str, str]:
    """检查单：固定模板句 + claim/due 插值，四要素机器可验证。"""
    return {key: text.format(claim=claim, due=due) for key, text in IMPULSE_CHECKLIST_TEMPLATES.items()}


def derive_stress_level(count: int, high_intensity_ratio: float) -> str:
    """压力三档推导：条数阈值 + 高强度占比，规则见 STRESS_THRESHOLDS。"""
    if count <= 0:
        return "low"
    if high_intensity_ratio > STRESS_THRESHOLDS["high_intensity_ratio"]:
        return "high"
    if count > STRESS_THRESHOLDS["count_high"]:
        return "high"
    if count <= STRESS_THRESHOLDS["count_low"]:
        return "low"
    return "mid"

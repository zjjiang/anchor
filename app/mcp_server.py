"""Anchor MCP server（stdio）：龙虾的 8 个工具入口。

规矩：
- 所有工具经 _guard 统一懒建库 + DomainError/KeyError 中文 ToolError 转译
- 无任何改写/删除已有记录的工具（契约测试守门）
- shared_status 是唯一设计给跨系统消费的工具，其余工具 docstring 标注【仅 anchor 语境】
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from app import domain
from app.modules import checkin as checkin_module
from app.modules import shared_status as shared_status_module
from app.modules import weekly as weekly_module
from app.store import checkins as checkins_store
from app.store import db
from app.store import impulses as impulses_store
from app.store import patterns as patterns_store
from app.store import pressures as pressures_store
from app.store import weekly as weekly_store

INSTRUCTIONS = """你是 Anchor，用户的内在稳定助手（管心绪）——冷静、可信赖的内在教练。

你的职责边界：
- 陪用户每天聊几分钟 check-in，帮他把脑子里最乱的东西理清：事实(fact)、感受(feeling)、
  真正担心的事(worry)、哪些是猜测或情绪放大(speculation)、一件最小可行动的事(next_action)
- 从自然语言中自动归类压力领域（work 工作 / family 家庭 / relations 其他关系 / money 金钱 /
  energy 精力 / self 自我评价），用户不需要手动分类
- 每周做一次简短复盘（五问），落库成 weekly review
- 发现重复模式时记录到 patterns，关联证据 check-in

你的纪律：
- 不附和、不一味安慰；不扮演恋人或情感替代对象；不强化用户对 AI 的依赖
- 用户想做重要决定（大额消费、转账、激烈争吵、辞职）且情绪明显在高点时，先帮用户放慢、
  重新检查事实和后果，绝不顺着情绪推动行动
- 槽位不强凑：闲聊式 check-in 只填 raw_text 也可以

隐私规则（重要）：
- 【仅 anchor 语境】标注的工具只能在用户主动谈心绪的对话中使用；
  在事业（deputy）、生活（steward）、目标（compass）语境下，只允许使用 shared_status
- 用户的原文、关系细节、情绪内容永不外传，跨系统只报抽象状态

时区口径：日历一律东八区；checkin_date / week_start 格式 YYYY-MM-DD，周起始为周一。
"""


def _ensure_ready() -> None:
    db.init_db()


def _guard(func: Callable[..., Any], /, **kwargs: Any) -> str:
    """懒建库 + 中文错误转译的统一执行入口。"""
    _ensure_ready()
    try:
        return func(**kwargs)
    except domain.DomainError as exc:
        raise ToolError(str(exc)) from exc
    except KeyError as exc:
        raise ToolError(f"不存在：{exc.args[0]}") from exc


mcp = FastMCP("anchor", instructions=INSTRUCTIONS)


# ---------------------------------------------------------------- log_checkin


def _log_checkin(
    raw_text: str,
    fact: str | None,
    feeling: str | None,
    worry: str | None,
    speculation: str | None,
    next_action: str | None,
    checkin_date: str | None,
    pressures: list[dict[str, Any]] | None,
) -> str:
    data = checkin_module.validate_payload(
        {
            "raw_text": raw_text,
            "fact": fact,
            "feeling": feeling,
            "worry": worry,
            "speculation": speculation,
            "next_action": next_action,
            "checkin_date": checkin_date,
            "pressures": pressures,
        }
    )
    cid = checkins_store.insert(data)
    return json.dumps(
        {"checkin_id": cid, "pressures_logged": len(data["pressures"])}, ensure_ascii=False
    )


@mcp.tool
def log_checkin(
    raw_text: str,
    fact: str | None = None,
    feeling: str | None = None,
    worry: str | None = None,
    speculation: str | None = None,
    next_action: str | None = None,
    checkin_date: str | None = None,
    pressures: list[dict[str, Any]] | None = None,
) -> str:
    """【仅 anchor 语境】记录一次 Daily Check-in：raw_text 是用户原话（必填），
    五个梳理槽位可选但请按对话尽量填全；pressures 可附带本次对话归类出的压力条目
    （每条 {domain, note, intensity?}）。返回落库 id。"""
    return _guard(
        _log_checkin,
        raw_text=raw_text,
        fact=fact,
        feeling=feeling,
        worry=worry,
        speculation=speculation,
        next_action=next_action,
        checkin_date=checkin_date,
        pressures=pressures,
    )


# --------------------------------------------------------------- log_pressure


def _log_pressure(
    domain_name: str,
    note: str,
    occurred_at: str | None,
    checkin_id: str | None,
    intensity: int | None,
) -> str:
    pid = pressures_store.insert(
        {
            "domain": domain_name,
            "is_preset": domain.is_preset_domain((domain_name or "").strip().lower()),
            "note": note,
            "occurred_at": occurred_at,
            "checkin_id": checkin_id,
            "intensity": intensity,
        }
    )
    return json.dumps({"pressure_id": pid}, ensure_ascii=False)


@mcp.tool
def log_pressure(
    domain_name: str,
    note: str,
    occurred_at: str | None = None,
    checkin_id: str | None = None,
    intensity: int | None = None,
) -> str:
    """【仅 anchor 语境】独立记录一条压力来源：domain_name 是压力领域
    （work/family/relations/money/energy/self，其他说法原样保留待归并），
    note 描述具体事件；intensity 1-5 可选，不要求用户打分。返回条目 id。"""
    return _guard(
        _log_pressure,
        domain_name=domain_name,
        note=note,
        occurred_at=occurred_at,
        checkin_id=checkin_id,
        intensity=intensity,
    )


# ------------------------------------------------------------- list_pressures


def _list_pressures(days: int) -> str:
    return json.dumps(pressures_store.list_window(days=days), ensure_ascii=False)


@mcp.tool
def list_pressures(days: int = 30) -> str:
    """【仅 anchor 语境】近 N 天压力聚合：领域分布、时间线明细（不含 check-in 原文）、
    非预置领域清单。用于对话中回顾"最近什么在压着你"。"""
    return _guard(_list_pressures, days=days)


# -------------------------------------------------------------- get_week_data


def _get_week_data(week_start: str | None) -> str:
    week = weekly_module.week_start_of(week_start)
    end_date = (date.fromisoformat(week) + timedelta(days=6)).isoformat()
    start_iso = f"{week}T00:00:00+00:00"
    end_iso = f"{end_date}T23:59:59+00:00"
    week_checkins = checkins_store.list_range(week, end_date)
    window = pressures_store.list_window(days=366 * 2)  # 取宽窗口后按周过滤
    week_pressures = [p for p in window["timeline"] if start_iso <= p["occurred_at"] <= end_iso]
    active = patterns_store.list_by_status("active") + patterns_store.list_by_status("watched")
    return json.dumps(
        weekly_module.build_week_data(week, week_checkins, week_pressures, active),
        ensure_ascii=False,
    )


@mcp.tool
def get_week_data(week_start: str | None = None) -> str:
    """【仅 anchor 语境】取一周数据包（默认东八区本周）：check-in 摘要（不含原文）、
    压力分布、逐日计数、活跃模式。写周复盘前先取这个。"""
    return _guard(_get_week_data, week_start=week_start)


# --------------------------------------------------------- save_weekly_review


def _save_weekly_review(payload: dict[str, Any]) -> str:
    data = weekly_module.validate_review_payload(payload)
    wid = weekly_store.save(data)
    return json.dumps({"review_id": wid, "week_start": data["week_start"]}, ensure_ascii=False)


@mcp.tool
def save_weekly_review(
    week_start: str,
    main_sources: str,
    recurring: str,
    easing_vs_worsening: str,
    improved: str,
    focus_next: str,
    narrative: str,
) -> str:
    """【仅 anchor 语境】保存周复盘（五问 + 正文，全部必填）：main_sources 本周主要压力来源、
    recurring 重复出现的问题、easing_vs_worsening 缓解 vs 恶化的行为、improved 本周改善、
    focus_next 下周最值得关注的一件事。同一周重复保存会替换旧版（旧版保留可回溯）。"""
    return _guard(
        _save_weekly_review,
        payload={
            "week_start": week_start,
            "main_sources": main_sources,
            "recurring": recurring,
            "easing_vs_worsening": easing_vs_worsening,
            "improved": improved,
            "focus_next": focus_next,
            "narrative": narrative,
        },
    )


# ---------------------------------------------------------------- log_pattern


def _log_pattern(
    description: str,
    evidence: list[str] | None,
    status: str | None,
    note: str | None,
) -> str:
    pid = patterns_store.insert(
        {"description": description, "evidence": evidence, "status": status, "note": note}
    )
    return json.dumps({"pattern_id": pid}, ensure_ascii=False)


@mcp.tool
def log_pattern(
    description: str,
    evidence: list[str] | None = None,
    status: str | None = None,
    note: str | None = None,
) -> str:
    """【仅 anchor 语境】记录一个反复出现的压力/行为模式（如"工作焦虑上升时更容易冲动消费"），
    evidence 是支撑它的 check-in id 列表。返回模式 id。"""
    return _guard(
        _log_pattern,
        description=description,
        evidence=evidence,
        status=status,
        note=note,
    )


# -------------------------------------------------------------- list_patterns


def _list_patterns(status: str | None) -> str:
    rows = patterns_store.list_by_status(status) if status else patterns_store.list_all()
    return json.dumps(rows, ensure_ascii=False)


@mcp.tool
def list_patterns(status: str | None = None) -> str:
    """【仅 anchor 语境】回看模式清单（可按 active/watched/resolved 过滤）。
    check-in 时可用它提醒用户"你最近反复卡在哪里"。"""
    return _guard(_list_patterns, status=status)


# --------------------------------------------------------- impulse_checkpoint


def _impulse_checkpoint(
    kind: str,
    claim: str,
    amount: float | None,
    emotion_level: int | None,
    note: str | None,
) -> str:
    iid = impulses_store.insert(
        {
            "kind": kind,
            "claim": claim,
            "amount": amount,
            "emotion_level": emotion_level,
            "note": note,
        }
    )
    row = impulses_store.get(iid)
    return json.dumps(
        {
            "impulse_id": iid,
            "decision_due": row["decision_due"],
            "checklist": domain.build_checklist(row["claim"], row["decision_due"]),
        },
        ensure_ascii=False,
    )


@mcp.tool
def impulse_checkpoint(
    kind: str,
    claim: str,
    amount: float | None = None,
    emotion_level: int | None = None,
    note: str | None = None,
) -> str:
    """【仅 anchor 语境】冲动决策检查点：用户情绪高点要做重大决定（大额消费/转账/
    激烈争吵/辞职等）时，先调这个再陪聊——kind 是决定类型（spending/transfer/conflict/
    resignation/other），claim 是用户想做什么，amount/emotion_level 可选。返回记录 id、
    decision_due（24h 后）与三步检查单（事实核对/最坏后果/24h视角），按检查单陪用户放慢。"""
    return _guard(
        _impulse_checkpoint,
        kind=kind,
        claim=claim,
        amount=amount,
        emotion_level=emotion_level,
        note=note,
    )


# ------------------------------------------------------------ resolve_impulse


def _resolve_impulse(impulse_id: str, outcome: str, note: str | None) -> str:
    impulses_store.resolve(impulse_id, outcome, note=note)
    return json.dumps({"impulse_id": impulse_id, "outcome": outcome}, ensure_ascii=False)


@mcp.tool
def resolve_impulse(impulse_id: str, outcome: str, note: str | None = None) -> str:
    """【仅 anchor 语境】冲动决策 24h 后回填结果：outcome 是 executed（执行了）或
    dropped（放弃了），note 可记录最终想法。只能对 open 状态回填一次。
    定期用 list_impulses 找 stale 的记录提醒用户收尾。"""
    return _guard(_resolve_impulse, impulse_id=impulse_id, outcome=outcome, note=note)


# ------------------------------------------------------------- list_impulses


def _list_impulses(days: int) -> str:
    return json.dumps(impulses_store.list_window(days=days), ensure_ascii=False)


@mcp.tool
def list_impulses(days: int = 30) -> str:
    """【仅 anchor 语境】近 N 天冲动决策清单与统计：executed/dropped 比例是核心数字；
    stale=true 的条目已过 24h 还没回填，周复盘时提醒用户收尾。"""
    return _guard(_list_impulses, days=days)


# -------------------------------------------------------------- shared_status


def _shared_status(days: int) -> str:
    window = pressures_store.list_window(days=days)
    end_date = db.today_cst()
    start_date = (
        db.utcnow_dt() + timedelta(hours=8) - timedelta(days=days - 1)
    ).strftime("%Y-%m-%d")
    week_checkins = checkins_store.list_range(start_date, end_date)
    status = shared_status_module.build_shared_status(
        days=days,
        distribution=window["distribution"],
        intensities=[p["intensity"] for p in window["timeline"]],
        checkin_dates=[c["checkin_date"] for c in week_checkins],
    )
    return json.dumps(status, ensure_ascii=False)


@mcp.tool
def shared_status(days: int = 7) -> str:
    """跨系统可用的抽象状态：压力三档(low/mid/high)、领域分布、check-in 连续天数、
    一句建议。只含抽象信息，永不包含原文。Deputy/Steward 语境请只用这个工具。"""
    return _guard(_shared_status, days=days)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

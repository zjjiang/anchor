"""MCP stdio 全链路冒烟：子进程拉起 server，走真实 stdio 往返。

用法：uv run python scripts/smoke_stdio.py
MCP 工具面任何改动后必跑。默认落在临时库，不碰 data/anchor.db。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError

CHECKS = 0


def ok(label: str, condition: bool) -> None:
    global CHECKS
    if not condition:
        raise SystemExit(f"✗ 冒烟失败：{label}")
    CHECKS += 1
    print(f"  ✓ {label}")


async def main() -> None:
    tmp_db = Path(tempfile.mkdtemp()) / "smoke.db"
    env = {**os.environ, "ANCHOR_DB": str(tmp_db)}
    transport = StdioTransport("uv", ["run", "python", "-m", "app.mcp_server"], env=env, cwd=str(Path(__file__).resolve().parents[1]))
    async with Client(transport) as client:
        tools = {t.name for t in await client.list_tools()}
        ok(
            "工具清单 = 8 个且无改写类",
            tools == {
                "log_checkin",
                "log_pressure",
                "list_pressures",
                "get_week_data",
                "save_weekly_review",
                "log_pattern",
                "list_patterns",
                "shared_status",
            },
        )

        raw = await client.call_tool(
            "log_checkin",
            {
                "raw_text": "冒烟：今天有点累",
                "fact": "开了全天会",
                "feeling": "疲惫",
                "pressures": [{"domain": "work", "note": "会议连轴"}],
            },
        )
        cid = json.loads(raw.content[0].text)["checkin_id"]
        ok(f"log_checkin 落库 {cid}", cid == "c1")

        raw = await client.call_tool(
            "log_pressure", {"domain_name": "energy", "note": "没睡好", "intensity": 4}
        )
        pid = json.loads(raw.content[0].text)["pressure_id"]
        ok(f"log_pressure 独立落库 {pid}", pid.startswith("p"))

        raw = await client.call_tool("list_pressures", {"days": 30})
        data = json.loads(raw.content[0].text)
        ok("list_pressures 分布含 work/energy", {d["domain"] for d in data["distribution"]} == {"work", "energy"})
        ok("明细不含 check-in 原文", "冒烟：今天有点累" not in raw.content[0].text)

        raw = await client.call_tool("get_week_data", {})
        week = json.loads(raw.content[0].text)
        ok("get_week_data 取到本周", week["week_start"] <= __import__("datetime").date.today().isoformat())

        raw = await client.call_tool(
            "log_pattern",
            {"description": "开会多→精力差", "evidence": [cid]},
        )
        ok("log_pattern 带证据", json.loads(raw.content[0].text)["pattern_id"] == "pt1")

        raw = await client.call_tool("list_patterns", {})
        ok("list_patterns 回看", json.loads(raw.content[0].text)[0]["evidence_count"] == 1)

        raw = await client.call_tool(
            "save_weekly_review",
            {
                "week_start": week["week_start"],
                "main_sources": "会议过多",
                "recurring": "睡不够",
                "easing_vs_worsening": "午休缓解",
                "improved": "砍了一个会",
                "focus_next": "保住睡眠",
                "narrative": "冒烟复盘正文",
            },
        )
        ok("save_weekly_review 落库", json.loads(raw.content[0].text)["review_id"] == "w1")

        raw = await client.call_tool("shared_status", {"days": 7})
        status = json.loads(raw.content[0].text)
        ok(
            "shared_status 只含白名单字段",
            set(status) == {"period", "overall_stress_level", "top_domains", "checkin_streak", "note"},
        )
        ok("隐私：原文不出现在抽象状态", "冒烟：今天有点累" not in raw.content[0].text)

        try:
            await client.call_tool("log_checkin", {"raw_text": "   "})
            raise SystemExit("✗ 冒烟失败：空 raw_text 未被拒绝")
        except ToolError as exc:
            ok("中文错误转译（ToolError）", "原话" in str(exc))

    print(f"\nstdio 冒烟全部通过（{CHECKS} 项）")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

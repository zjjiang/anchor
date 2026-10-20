"""MCP 契约测试（守门测试，不许删）：

① 隐私红线：shared_status 序列化返回中不出现库内已知原文/note/description
② 无改写通道：工具清单中不存在任何修改/删除已有记录的工具
③ 8 个工具的成功路径与中文错误路径（fastmcp.Client 内存直调）
"""

from __future__ import annotations

import json

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError as CallToolError

from app.mcp_server import mcp
from app.modules import checkin as checkin_module
from app.store import checkins as checkins_store
from app.store import impulses as impulses_store
from app.store import patterns as patterns_store
from app.store import pressures as pressures_store
from app.store import weekly as weekly_store

SECRET_RAW = "这是一句绝不能外传的私密原话"
SECRET_NOTE = "压力备注：和老板吵架的细节"
SECRET_DESCRIPTION = "模式描述：焦虑时刷购物网站的细节"
SECRET_CLAIM = "冲动备注：深夜想买两万的相机"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def client():
    async with Client(mcp) as c:
        yield c


async def _call(client, name: str, **args) -> dict:
    result = await client.call_tool(name, args)
    return json.loads(result.content[0].text)


@pytest.fixture()
def seeded_db(fresh_db):
    """埋入已知原文/note/描述/冲动 claim，供泄露断言使用。"""
    cid = checkins_store.insert(
        checkin_module.validate_payload(
            {"raw_text": SECRET_RAW, "fact": "事实X"}
        )
    )
    pressures_store.insert(
        {"domain": "work", "is_preset": True, "note": SECRET_NOTE, "intensity": 5}
    )
    patterns_store.insert({"description": SECRET_DESCRIPTION, "evidence": [cid]})
    impulses_store.insert({"kind": "spending", "claim": SECRET_CLAIM, "amount": 12800})
    weekly_store.save(
        {
            "week_start": "2026-10-19",
            "main_sources": "s",
            "recurring": "r",
            "easing_vs_worsening": "e",
            "improved": "i",
            "focus_next": "f",
            "narrative": "正文n",
        }
    )
    return cid


class TestPrivacyGate:
    async def test_shared_status_leaks_nothing(self, client, seeded_db):
        data = await _call(client, "shared_status", days=30)
        serialized = json.dumps(data, ensure_ascii=False)
        for secret in (SECRET_RAW, SECRET_NOTE, SECRET_DESCRIPTION, SECRET_CLAIM,
                       "事实X", "正文n"):
            assert secret not in serialized
        # impulses 永不进入抽象状态：字段白名单不变，统计类字段也不出现
        assert set(data) == {"period", "overall_stress_level", "top_domains",
                             "checkin_streak", "note"}
        assert "executed" not in serialized and "stale" not in serialized

    async def test_no_mutation_tools_exist(self):
        """工具清单中不存在任何改写/删除已有记录的工具（隐私与永久性红线）。

        resolve_impulse 是唯一例外形态：状态迁移（open→executed/dropped），
        不改任何既有内容字段，与 patterns 的状态流转同模式。
        """
        async with Client(mcp) as c:
            tools = await c.list_tools()
        forbidden = ("update", "edit", "modify", "delete", "remove", "replace", "rewrite")
        mutable_targets = ("checkin", "pressure", "pattern", "review", "impulse")
        for tool in tools:
            name = tool.name.lower()
            if any(target in name for target in mutable_targets):
                assert not any(word in name for word in forbidden), f"发现改写类工具：{tool.name}"
        allowed = {
            "log_checkin", "log_pressure", "list_pressures", "get_week_data",
            "save_weekly_review", "log_pattern", "list_patterns", "shared_status",
            "impulse_checkpoint", "resolve_impulse", "list_impulses",
        }
        assert {t.name for t in tools} == allowed

    async def test_raw_text_never_in_list_tools(self, client, seeded_db):
        pressures = await _call(client, "list_pressures", days=30)
        assert SECRET_RAW not in json.dumps(pressures, ensure_ascii=False)
        week = await _call(client, "get_week_data")
        assert SECRET_RAW not in json.dumps(week, ensure_ascii=False)


class TestToolHappyPaths:
    async def test_log_and_read_checkin(self, client, fresh_db):
        result = await _call(
            client,
            "log_checkin",
            raw_text="今天有点烦",
            fact="方案被打回",
            feeling="烦躁",
            pressures=[{"domain": "work", "note": "返工"}],
        )
        assert result["checkin_id"] == "c1"
        assert result["pressures_logged"] == 1

    async def test_log_pressure_and_list(self, client, fresh_db):
        result = await _call(client, "log_pressure", domain_name="family", note="吵架")
        assert result["pressure_id"] == "p1"
        data = await _call(client, "list_pressures", days=30)
        assert data["distribution"] == [{"domain": "family", "count": 1}]

    async def test_week_flow(self, client, fresh_db):
        await _call(client, "log_checkin", raw_text="x",
                    pressures=[{"domain": "money", "note": "账单"}])
        data = await _call(client, "get_week_data")
        assert data["week_start"] == data["week_start"]
        saved = await _call(
            client,
            "save_weekly_review",
            week_start=data["week_start"],
            main_sources="钱",
            recurring="月光",
            easing_vs_worsening="记账缓解",
            improved="开始记账",
            focus_next="做预算",
            narrative="正文",
        )
        assert saved["review_id"] == "w1"

    async def test_pattern_flow(self, client, fresh_db):
        cid = (await _call(client, "log_checkin", raw_text="x"))["checkin_id"]
        pid = (await _call(client, "log_pattern", description="模式", evidence=[cid]))["pattern_id"]
        rows = json.loads((await client.call_tool("list_patterns", {})).content[0].text)
        assert rows[0]["id"] == pid
        assert rows[0]["evidence_count"] == 1

    async def test_shared_status_empty_window(self, client, fresh_db):
        data = await _call(client, "shared_status", days=7)
        assert data["overall_stress_level"] == "low"


class TestChineseErrors:
    async def test_empty_raw_text(self, client, fresh_db):
        with pytest.raises(CallToolError, match="原话"):
            await client.call_tool("log_checkin", {"raw_text": "  "})

    async def test_bad_intensity(self, client, fresh_db):
        with pytest.raises(CallToolError, match="intensity"):
            await client.call_tool(
                "log_pressure", {"domain_name": "work", "note": "x", "intensity": 9}
            )

    async def test_bad_evidence(self, client, fresh_db):
        with pytest.raises(CallToolError, match="c404"):
            await client.call_tool(
                "log_pattern", {"description": "x", "evidence": ["c404"]}
            )

    async def test_missing_review_field(self, client, fresh_db):
        with pytest.raises(CallToolError, match="narrative"):
            await client.call_tool(
                "save_weekly_review",
                {
                    "week_start": "2026-10-19",
                    "main_sources": "s",
                    "recurring": "r",
                    "easing_vs_worsening": "e",
                    "improved": "i",
                    "focus_next": "f",
                    "narrative": " ",
                },
            )


class TestImpulseGuardTools:
    async def test_checkpoint_full_flow(self, client, fresh_db):
        result = await _call(
            client,
            "impulse_checkpoint",
            kind="Spending",
            claim="深夜想买相机",
            amount=20000,
            emotion_level=4,
        )
        assert result["impulse_id"] == "i1"
        # 检查单四要素：三提示 + decision_due，均为模板句
        assert set(result["checklist"]) == {"facts", "worst_case", "future_self"}
        assert "深夜想买相机" in result["checklist"]["facts"]
        from datetime import UTC, datetime, timedelta

        due = datetime.fromisoformat(result["decision_due"])
        assert datetime.now(UTC) + timedelta(hours=23) < due <= datetime.now(UTC) + timedelta(hours=25)

        stats = (await _call(client, "list_impulses", days=30))["stats"]
        assert stats == {"total": 1, "executed": 0, "dropped": 0, "open": 1,
                         "executed_ratio": None}

        resolved = await _call(client, "resolve_impulse", impulse_id="i1",
                               outcome="dropped", note="睡醒后不想要了")
        assert resolved["outcome"] == "dropped"
        stats = (await _call(client, "list_impulses", days=30))["stats"]
        assert stats["executed_ratio"] == 0.0

    async def test_checkpoint_missing_claim(self, client, fresh_db):
        with pytest.raises(CallToolError, match="claim"):
            await client.call_tool("impulse_checkpoint", {"kind": "spending", "claim": " "})

    async def test_double_resolve_rejected(self, client, fresh_db):
        await _call(client, "impulse_checkpoint", kind="other", claim="x")
        await _call(client, "resolve_impulse", impulse_id="i1", outcome="executed")
        with pytest.raises(CallToolError, match="已回填"):
            await client.call_tool(
                "resolve_impulse", {"impulse_id": "i1", "outcome": "dropped"}
            )

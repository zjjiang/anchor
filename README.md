# Anchor

**Personal OS 第四个同构后端，管心绪。** deputy 管事业、steward 管生活、compass 管方向、
anchor 管心绪。

Anchor 是内在稳定助手：每天用自然语言 check-in 几分钟，把脑子里最乱的东西理成
事实 / 感受 / 担心 / 猜测 / 最小行动；长期沉淀压力来源与重复模式，每周出一次简短复盘。
它不是心理咨询产品，不是陪伴型 AI——是一个长期、冷静、可信赖的内在教练。

## 架构

纯逻辑后端，与 deputy/steward/compass 完全同构：**不调 LLM、不配 API key、不烧 token**，
"听懂和梳理"在龙虾（OpenClaw）侧，本仓库提供结构化落库与查询工具。

```
龙虾（OpenClaw）—— 脑子在这里
   ├── MCP stdio → deputy    事业（8899）
   ├── MCP stdio → steward   生活（8901）
   ├── MCP stdio → compass   方向（8902）
   └── MCP stdio → anchor    心绪（看板 8903）← 这里
```

- Python 3.12+ / FastAPI + FastMCP(stdio) / SQLite（`data/anchor.db`，无 ORM）/ uv
- 数据不出墙：db gitignore、仅 localhost、无鉴权
- 隐私红线（契约测试守门）：`shared_status` 是唯一跨系统出口，只出抽象状态
  （压力三档 / 领域分布 / 建议负荷），永不返回原文；无任何改写/删除已有记录的工具

## 跑起来

```bash
uv sync                                    # 装依赖
uv run pytest -q                           # 测试（134 个）
uv run python scripts/smoke_stdio.py       # MCP stdio 全链路冒烟
uv run uvicorn app.api:app --port 8903     # 只读看板（可选）
uv run python -m app.mcp_server            # MCP server（龙虾接入，见 docs/lobster-setup.md）
```

龙虾接入与 Anchor 分身人设：`docs/lobster-setup.md` / `docs/anchor-guide.md`。

## 红线

1. `data/anchor.db` 含最私密的情绪原文，**敏感级别高于 deputy/steward**——不入库（git）、
   不出本机、不进云端明文
2. `shared_status` 只出抽象状态，契约测试（`tests/test_mcp_contract.py`）不许删
3. 无改写/删除已有记录的工具，check-in 原文一经落库永久保留
4. 第一阶段不做、第二阶段已含 Impulse Guard（检查点/回填/统计）；仍不做：自动模式检测、
   跨系统实际接线、情绪评分仪表盘

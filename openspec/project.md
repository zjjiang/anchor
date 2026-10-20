# Anchor 项目约定

## 定位

**Anchor = Personal OS 的内在稳定助手（管心绪）。** deputy 管事业、steward 管生活、compass 管方向、anchor 管心绪。

它不是心理咨询产品，也不是陪伴型 AI。核心目标：帮助用户在高压力、焦虑、关系冲突、冲动决策状态下持续梳理情绪、恢复判断力，并识别长期反复出现的压力与行为模式。产品形态是"长期、冷静、可信赖的内在教练"。

## 已定架构（2026-10-20，与 deputy/steward/compass 完全同构）

- 纯逻辑后端：**不调 LLM、不配 API key、不烧 token**，"听懂/梳理"全在龙虾（OpenClaw）侧；
  本仓库只提供结构化落库与查询工具（MCP stdio），梳理框架由工具参数 schema 承接
- 技术栈：Python 3.12+ / FastAPI + FastMCP(stdio) + SQLite（`data/anchor.db`，无 ORM），uv 管理
- 端口：只读 Web 看板 **8903**（deputy=8899、steward=8901、compass=8902）
- 总线是龙虾，四个子系统互不直连；数据不出墙（db gitignore，仅 localhost，无鉴权）
- 时区口径：时间戳 UTC ISO 字符串；日历口径（checkin_date / week_start / first_seen）一律东八区，周起始为周一

## 三条铁律（强制，全家族统一）

1. **OpenSpec 先行**：非平凡改动先 `/opsx:propose`，用户审阅通过前不动手写代码
2. **TDD**：Red → Green → Refactor，`uv run pytest -q` 全绿才算完
3. **PR 合入**：绝不直推 main；一个 change = 一个分支 = 一个 PR；**任何 git push 前先找用户确认**

## 契约红线（有守门测试，不许删）

1. **`shared_status` 是唯一跨系统出口**：只返回抽象状态（压力等级/领域分布/建议负荷），
   永不返回 check-in 原文、digest、压力 note、模式 description——契约测试断言返回序列化中
   不含库内已知原文
2. **无改写通道**：MCP 不提供任何修改/删除已有 check-in、pressure、pattern、review 的工具——
   契约测试守门
3. **业务规则只在 store 层强制**，MCP 工具层只做编排与 ToolError 转译
4. **数据不出墙**：`data/anchor.db` 含最私密的对话原文，敏感级别高于 deputy/steward，
   gitignore + 仅 localhost

## 命令

```bash
uv sync                                        # 装依赖
uv run pytest -q                               # 全量测试
uv run ruff check .                            # lint
uv run python scripts/smoke_stdio.py           # MCP stdio 全链路冒烟（MCP/门禁改动后必跑）
uv run uvicorn app.api:app --port 8903         # 只读看板
uv run python -m app.mcp_server                # MCP stdio server（龙虾接入）
```

## 范围纪律

第一阶段（add-anchor-core）主链路四件 + 模式记录 + shared_status + 只读看板，已完成。
第二阶段进行中：Impulse Guard 已落地（add-impulse-guard：检查点/回填/统计，impulses
不进 shared_status 白名单）。

**不做**：自动模式检测、shared_status 与 deputy/steward 实际接线、冲动 24h 自动推送
（龙虾 cron 职责）、金额阈值/预算联动、情绪评分体系、mood 仪表盘、测试题/表单、
提议门禁（日记型数据直写）、用户认证。扩展前先回本节确认。

## 成功标准

1. 我愿不愿意每天花几分钟跟它说几句（输入轻：自然语言，无表单）
2. 它是不是真的越来越懂我反复卡在哪（pressures/patterns 沉淀）
3. 周复盘有没有真正改变我的行为（easing_vs_worsening / focus_next 落到行动）

# Proposal: add-anchor-core

## Why

Personal OS 已有 deputy（事业）、steward（生活）、compass（方向）三个同构后端，唯独缺一个管"心绪"的子系统。高压力、焦虑、关系冲突、冲动决策发生时，没有一个地方持续记录和梳理；时间久了，反复出现的压力模式（如"工作焦虑上升 → 冲动消费"）完全依赖人脑记忆，无法被系统性识别。

Anchor（内在稳定助手）补上这个位置。第一阶段只跑通主链路：**Daily Check-in → 对话整理落库 → 压力来源记录 → Weekly Reflection**。不做心理产品，不做情绪仪表盘，不做陪伴型 AI。

## What Changes

- **新建 anchor 仓库骨架**：完全同构 compass/steward —— uv + Python 3.12+ / fastapi / fastmcp(stdio) / SQLite（`data/anchor.db`，无 ORM，`ANCHOR_DB` 环境变量覆盖）/ 只读 Web 看板（127.0.0.1:8903）
- **Daily Check-in**：新增 `checkins` 表（raw_text 原话永久保留 + 五槽位 digest JSON：fact / feeling / worry / speculation / next_action）。梳理发生在龙虾侧对话中，`log_checkin` 的工具参数本身就是梳理框架——用 schema 强制梳理发生
- **压力来源记录**：新增 `pressures` 表，domain 枚举 work / family / relations / money / energy / self（+ free-text 兜底），龙虾从自然语言自动归类，用户无需手动分类
- **模式记录**：新增 `patterns` 表（description / status / evidence），第一阶段由龙虾在对话中人工修养式维护，不做自动检测
- **Weekly Reflection**：新增 `weekly_reviews` 表；`get_week_data` 输出聚合数据包（压力分布 / 重复话题 / check-in 摘要），龙虾按人设写复盘后 `save_weekly_review` 落库
- **隐私边界**：`shared_status()` 是唯一跨系统出口，只返回抽象状态（压力等级 / 领域分布 / 建议负荷），永不返回原文；用 MCP 契约测试机器化验证这条红线（断言返回中不存在 raw 文本字段）
- **不做门禁**：与 compass 不同，Anchor 全部写入直落。日记型主观数据可追加可修正，加提议门禁只会给每天几分钟的 check-in 添摩擦
- **龙虾侧配套文档**：`docs/anchor-guide.md`（内在教练人设：不附和、不扮演恋人、放慢决策；check-in / weekly SOP；隐私规则）+ `docs/lobster-setup.md`（stdio 接入指南）
- **Phase 1 明确不做**：Impulse Guard、自动模式检测、跨系统 `shared_status` 实际接线（工具先就位）、情绪评分仪表盘、任何测试题/表单

## Capabilities

### New Capabilities

- `daily-checkin`：每日 check-in 的记录与五槽位梳理落库（`log_checkin`、checkins 存取、digest 结构校验）
- `pressure-tracking`：压力来源记录与领域归类（`log_pressure`、`list_pressures`、domain 枚举与 free-text 兜底、可选 intensity）
- `pattern-notes`：重复行为/压力模式的人工修养式记录（`log_pattern`、`list_patterns`、evidence 关联 check-in）
- `weekly-reflection`：周复盘数据包与复盘落库（`get_week_data`、`save_weekly_review`）
- `privacy-boundary`：跨系统抽象状态导出与隐私红线（`shared_status` 仅抽象输出，契约测试守门）

### Modified Capabilities

（无 —— 新仓库，无既有规格）

## Impact

- **新仓库全量**：`app/{domain,api,mcp_server}.py`、`app/store/`（db + 4 个域文件）、`app/modules/`（纯函数）、`app/web/index.html`、`tests/`、`scripts/smoke_stdio.py`、`docs/`、`openspec/project.md`
- **依赖**：与家族一致的四件套 fastapi / fastmcp / uvicorn + pytest/ruff dev 组；无新增依赖
- **对现有子系统零影响**：互不直连，总线是龙虾；`shared_status` 的实际消费方（deputy/steward）留到 Phase 2
- **端口**：8903（避开了 8899 / 8901 / 8902，deputy=8899 被 Docker 占用过的 8787 也避开）

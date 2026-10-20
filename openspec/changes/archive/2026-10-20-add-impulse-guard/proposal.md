# Proposal: add-impulse-guard

## Why

原始需求中"冲动决策防护"（第 5 条）是唯一还没落地的能力：目前只有 `docs/anchor-guide.md` 里的"先放 24 小时"人设约定，纯靠龙虾自觉，没有数据沉淀。放慢决策本身有价值，但更有价值的是**回填**——记录过的冲动，多少次是真需要的？这个比例既是给用户看的最强 mirror，也是后续自动模式检测的核心素材。

同时第一阶段已验证主链路可用，用户对五槽位、隐私契约的模式已建立认知，此时加同类结构的表和工具成本最低。

## What Changes

- **新增 `impulses` 表**：kind 五枚举（`spending` 大额消费 / `transfer` 转账 / `conflict` 激烈争吵 / `resignation` 辞职 / `other` 兜底）、`claim` 必填（用户想做什么）、`amount` 可选、`emotion_level` 可选（1-5，仅用户自己表达强度时填）、`status`（`open` / `executed` / `dropped`）、`decision_due`（创建 +24h，UTC）
- **新增 3 个 MCP 工具**：
  - `impulse_checkpoint`：落检查点，返回结构化检查单（事实核对提示 / 最坏后果 / 24h 视角 / decision_due）——检查单由规则模板生成，人话但非 LLM 自由文本
  - `resolve_impulse`：24h 后回填 outcome（`executed` / `dropped` + 可选 note），状态迁移而非内容改写（与 patterns `update_status` 同模式）
  - `list_impulses`：窗口清单 + 统计（executed/dropped 比例），`open` 且超 24h 的标记 `stale: true`
- **契约测试扩容**：allowed 工具集 8 → 11；forbidden 改写词名单覆盖 impulse 目标（impulse 不允许 update/delete 内容类工具，只有 resolve 状态迁移）
- **隐私边界不变**：impulses **不进** `shared_status` 白名单——抽象状态保持"状态不事件"，冲动决策的细节（想买什么/想吵什么）留在 anchor 内
- **不做**：自动 24h 推送（龙虾 cron 职责，anchor 只提供 stale 标记）、金额审批/预算联动、冲动内容进任何跨系统出口

## Capabilities

### New Capabilities

- `impulse-guard`：冲动决策检查点记录、24h 后回填、清单与统计（3 个工具 + impulses 存取 + stale 标记 + 检查单模板）

### Modified Capabilities

（无 —— 现有 5 个能力的规格均不变；契约测试的 allowed 集扩容属于 `impulse-guard` 自身的守门要求，写入其 spec 场景）

## Impact

- **代码**：`app/domain.py`（IMPULSE_KINDS/IMPULSE_OUTCOMES/常量）、`app/store/impulses.py`（新）、`app/mcp_server.py`（+3 工具）、`tests/`（module/store/contract 各一）、`scripts/smoke_stdio.py`（+3 步）、`docs/anchor-guide.md`（Impulse SOP 从"人设约定"升级为"工具流程"）
- **schema**：新表 `impulses`（幂等建库，SCHEMA_VERSION 不变——家族惯例是 CREATE IF NOT EXISTS 追加，无迁移步骤）
- **对现有能力零影响**：shared_status 白名单不动；既有 8 工具签名不变

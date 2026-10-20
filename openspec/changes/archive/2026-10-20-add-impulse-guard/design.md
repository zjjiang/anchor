# Design

## Context

第一阶段主链路已上线（见 `archive/2026-10-20-add-anchor-core/`），家族模式已验证：纯函数 module + 薄 store + 显式薄签名 MCP 工具 + 契约守门测试。本 change 完全沿用该模式加第三个写入域（impulses），无新外部依赖、无跨仓库改动。

需求动机与边界见 proposal.md；本文件只记技术取舍。

## Goals / Non-Goals

**Goals:**

- 冲动决策"记录 → 24h → 回填"全链路可落库、可统计
- 检查单输出可机器验证（模板句，无自由文本）
- 契约守门测试随工具面扩容仍完整覆盖隐私与永久性红线

**Non-Goals:**

- 自动 24h 提醒推送（龙虾 cron 职责；anchor 只提供 stale 标记查询）
- 金额阈值判断 / 预算联动 / 任何"该不该买"的计算
- impulses 进 shared_status 或任何跨系统出口
- 冲动记录的编辑与删除

## Decisions

### D1. SCHEMA_VERSION 1 → 2

新增表即 schema 变更，按 steward 的 goals 表先例 bump 版本号。旧库跑新代码：`init_db` 幂等 `CREATE IF NOT EXISTS` 直接补表，版本表写入 2；新代码禁跑旧库的逻辑（版本守卫）不需要放开——只升不降，方向安全。

### D2. resolve_impulse 是状态迁移，不是"改写工具"——但守门测试仍要扩名单

patterns 已有 `update_status` 先例：状态迁移类操作不违反"原文不可改"红线。但契约测试的 forbidden 名单目前按工具名匹配（update/edit/delete…× 目标域），resolve 不在违禁词里、天然通过；本 change 仍显式把 impulse 加入 mutable_targets 断言与 allowed 集，让"impulse 只有 resolve 一条状态迁移通道"成为被测试锁死的事实，防止未来有人加 `update_impulse` 溜进来。

### D3. 检查单 = 服务端规则模板，不是让龙虾自己发挥

检查单若由龙虾自由生成，就无法机器验证"每次检查点都给了完整四要素"。决定：`impulse_checkpoint` 返回值中的检查单三提示 + decision_due 由 Python 模板句生成（可带 claim/kind 插值，但句式固定）。龙虾的对话发挥空间在"怎么念"而不在"给不给"。

### D4. stale 是查询时派生，不是定时任务

open 且 now > decision_due 即 stale，读取时计算，不落库、不靠后台 job。anchor 保持纯后端无定时器，提醒节奏完全归龙虾 cron。

### D5. executed 占比 = executed / (executed + dropped)，open 不进分母

统计口径在 store 层一次算好返回，避免每个消费方自己算错。分母排除 open——"还没决定的"不稀释比例。

### D6. emotion_level 复用 intensity 校验（1-5 可选），语义独立

不复用 `pressures.intensity` 字段名，避免跨表语义混淆（一个是压力强度、一个是冲动时刻情绪强度）；校验规则同一函数。

## Risks / Trade-offs

- [龙虾不走 checkpoint 直接陪聊决策] → 人设文档升级为硬流程（anchor-guide Impulse SOP：检测到重大决定词先 checkpoint 再对话）+ 数据侧 list_impulses 的 stale 记录在周复盘里可见，漏走流程会被看见
- [resolve 回填率低（记了不收尾），统计失去意义] → stale 标记 + 周复盘 SOP 中加"清一下上周没回填的冲动"一步；不自动化，保持轻
- [检查单模板句随时间显得机械] → 模板集中在一个常量 dict，改文案不动逻辑；龙虾可在对话里用自己的话展开，模板只保证"给过"

## Migration Plan

`uv sync` → `uv run pytest -q` → `scripts/smoke_stdio.py`（+3 步）→ 重启龙虾 MCP 子进程即自动建新表。回滚 = `git revert` + 删 `data/anchor.db` 中 impulses 表（或整库，属开发期数据）。

## Open Questions

（无。）

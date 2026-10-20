# Design

## Context

anchor 是全新仓库，Personal OS 第四个同构后端。家族既有约定（见 proposal.md - Why）：纯逻辑后端、脑子在龙虾（OpenClaw）侧、互不直连、数据不出墙。代码骨架完全照 compass/steward 抄：`app/{domain,api,mcp_server}.py` + `app/store/` + `app/web/index.html`，uv + Python 3.12+，fastapi / fastmcp(stdio) / SQLite 单文件无 ORM，幂等建库 + SCHEMA_VERSION，无迁移工具。

本 change 的特殊约束有二：① Anchor 的核心产出是对话中的"梳理"，但子系统不配 AI——梳理必须由工具 schema 承接；② Anchor 是全家族最私密子系统，而四个子系统共享同一个龙虾脑子，隐私边界无法靠进程隔离实现。

## Goals / Non-Goals

**Goals:**

- 主链路四件（check-in / 压力记录 / 模式记录 / 周复盘）落库与查询全部可用
- 隐私红线机器可测：`pytest` 全绿即证明 `shared_status` 无泄露、无改写通道
- 龙虾拿到仓库即可接入：INSTRUCTIONS 章程 + docs SOP 完备

**Non-Goals:**

- Impulse Guard、自动模式检测、`shared_status` 与 deputy/steward 的实际接线（Phase 2）
- 情绪评分体系、mood 仪表盘、任何统计图表形式的"形式感"（产品边界，长期不做）
- 提议门禁（proposals）——见 Decisions D4
- 用户认证、非 localhost 访问

## Decisions

### D1. 梳理发生在龙虾侧，靠工具 schema 强制 —— 而非 Anchor 内置 LLM

`log_checkin` 的五个 digest 槽位（fact / feeling / worry / speculation / next_action）就是梳理框架：龙虾陪聊完后必须按槽位组织参数才能落库。备选方案是 Anchor 内置 LLM 做自动提取——否决，理由：打破全家族"子系统不烧 token、不配 key"的铁律；梳理质量本就应在对话中由人机共同完成，事后跑模型提取既贵又丢失语境。代价是梳理质量依赖龙虾侧模型遵循度，缓解手段是 INSTRUCTIONS 中给出正反例 + 槽位允许留空（不逼填）。

### D2. 隐私边界 = 工具面收窄（软）+ 抽象导出（唯一出口）+ 契约测试（硬）

同一只龙虾理论上可在事业语境调 anchor 明细工具，进程级硬隔离不存在。三层缓解：

- **软**：`docs/anchor-guide.md` 人设规则写明"非 anchor 语境不调 anchor 明细工具"；`shared_status` 以外的工具 docstring 标注 `【仅 anchor 语境】`
- **结构**：`shared_status` 是唯一设计给跨系统消费的工具，返回字段白名单式定义（period / overall_stress_level / top_domains / checkin_streak / note），note 由规则模板生成而非 LLM 自由文本
- **硬**：`tests/test_mcp_contract.py` 两条守门断言：① 库中埋已知原文后断言 `shared_status` 序列化返回不含该原文；② 工具清单中不存在任何改写/删除类工具。与 deputy 的"MCP 不暴露直写工具"守门测试同模式

备选方案是给 MCP server 加调用方身份区分——stdio 模式下无调用方概念，不可行；Phase 2 若做独立消费方再考虑。

### D3. 事件明细用宽表而非 steward 的单表事件源

steward 的 `events` 单表适合多领域异构事件；anchor 的四类记录（check-in / pressure / pattern / review）字段差异大、查询口径不同（周聚合、领域分布、状态机），单表会让每个查询都是 payload JSON 解析。决定：四张独立表 + 各自 store 文件，与 compass 的多表风格对齐。raw_text 只存 `checkins.raw_text` 一处。

### D4. 不做提议门禁

compass 的门禁服务于"快照定格"式不可逆变更；anchor 全部写入是日记型追加（check-in 永久但无真源覆盖问题，周复盘走 replaced 版本替换）。每天几分钟的 check-in 若夹一次审批会直接杀死主链路使用意愿。写通道纪律改由"无改写工具"守门测试承担（D2）。

### D5. 周复盘同周唯一，replaced 标记而非删除

同周重复保存时旧记录打 `replaced_at` 标记保留（不物理删除）——情绪内容误覆盖的代价高，保留可回溯；查询口径只取未替换版本。

### D6. 压力领域枚举放 domain.py，free-text 兜底保留原文

预置六域 + 未知值原样落库并标记非预置，是为了不逼用户/龙虾硬套分类（"通用兜底，永不被 schema 卡死"，steward 惯例）；归并到预置域是 Phase 2 的事。

### D7. 时区口径

时间戳一律 UTC ISO 字符串；日历口径（checkin_date、week_start、first_seen/last_seen）一律东八区，与 deputy 的 run_date 口径一致。周起始为周一。

## Risks / Trade-offs

- [龙虾不按五槽位梳理，digest 长期大面积留空] → 槽位可选不逼填 + INSTRUCTIONS 正反例；`list_pressures`/`get_week_data` 不依赖 digest 也能出活，主链路不因 digest 空而断
- [shared_status 的阈值规则（stress_level 三档）初期不准] → 阈值集中在 domain.py 常量，允许后续按真实数据调参，不涉及 schema 变更
- [自由文本 domain 兜底长期堆积碎片值] → 非预置域在 list_pressures 中单独列出，Phase 2 做归并；不阻塞主链路
- [raw_text 永久保留与"数据不出墙"叠加，DB 文件本身高度敏感] → 沿用家族既有约定：`data/` gitignore、仅 localhost、备份遵循用户本地习惯；本仓库文档中明示此文件敏感级别高于 deputy/steward
- [契约测试只防工具面泄露，防不了龙虾跨语境"复述"原文] → 属人设层软约束，docs 中写明；技术侧无法根治共享脑子的问题，已在 D2 说明取舍

## Migration Plan

全新仓库，无迁移。建库即用：`uv sync` → `uv run pytest -q` → `uv run python scripts/smoke_stdio.py` → 龙虾按 docs/lobster-setup.md 挂载。回滚 = 删 `data/anchor.db`。

## Open Questions

（无 —— 阈值具体数值在实现期以常量落定，属实现细节不改变规格。）

# impulse-guard Specification

## Purpose
用户在情绪高点要做重大决定（大额消费 / 转账 / 激烈争吵 / 辞职等）时，强制一个"先记录、放 24 小时、再回填结果"的检查点：放慢决策本身，同时沉淀 executed vs dropped 的比例数据，供回看与后续模式检测。

## Requirements

### Requirement: 冲动检查点记录
系统 SHALL 提供 `impulse_checkpoint` 工具，接受 `kind`（必填，`spending` / `transfer` / `conflict` / `resignation` / `other`）、`claim`（必填，用户想做什么）、`amount`（可选，涉及金额）、`emotion_level`（可选，1-5，仅用户自己表达强度时填）、`note`（可选补充），写入 status 为 `open` 的记录，`decision_due` 为创建时间 +24 小时；返回记录 id 与结构化检查单。

#### Scenario: 完整检查点落库
- **WHEN** 龙虾调用 `impulse_checkpoint`，kind=spending，claim 描述想买的物件，amount=12800
- **THEN** 系统存入一条 open 状态记录，decision_due 为当前 UTC 时间 +24h，返回新 id

#### Scenario: 缺少 claim 被拒绝
- **WHEN** `impulse_checkpoint` 调用缺失 claim 或 claim 为空白
- **THEN** 系统拒绝写入并返回中文错误信息，不产生任何记录

#### Scenario: 未知 kind 走兜底
- **WHEN** kind 传入 "investment" 等非预置值
- **THEN** 系统原样保留并标记非预置，正常落库不报错

### Requirement: 检查单规则模板生成
`impulse_checkpoint` 的返回 SHALL 包含由规则模板生成的结构化检查单：事实核对提示、最坏后果、24 小时视角、decision_due 时间戳；模板为固定句式，MUST NOT 包含 LLM 生成的自由文本字段。

#### Scenario: 检查单四要素齐全
- **WHEN** 任一合法 `impulse_checkpoint` 调用成功
- **THEN** 返回包含事实核对、最坏后果、24h 视角三个提示项与 decision_due，均为模板句

### Requirement: 冲动结果回填
系统 SHALL 提供 `resolve_impulse` 工具，对 `open` 状态的记录回填 outcome（`executed` 执行了 / `dropped` 放弃了）与可选 note，并将 status 置为对应值、记录 decided_at；对不存在或不处于 open 状态的记录 SHALL 拒绝。回填只改状态与结论字段，不涉及既有内容改写。

#### Scenario: 正常回填
- **WHEN** 对一条 open 记录调用 `resolve_impulse`，outcome=dropped，note 说明放弃原因
- **THEN** 该记录 status 变为 dropped，decided_at 为当前时间，note 落库

#### Scenario: 重复回填被拒绝
- **WHEN** 对已 resolved 的记录再次调用 `resolve_impulse`
- **THEN** 系统拒绝并返回中文错误信息

#### Scenario: 不存在的记录被拒绝
- **WHEN** resolve 的 id 在库中不存在
- **THEN** 系统拒绝并返回中文错误信息

### Requirement: 冲动清单与统计
系统 SHALL 提供 `list_impulses` 工具，按天数窗口（默认 30 天）返回：清单（occurred_at、kind、claim、amount、emotion_level、status、stale、decision_due、decided_at）与统计（总数、executed 数、dropped 数、open 数、executed 占已决比例）；`open` 且已过 decision_due 的条目 `stale` 为 true。

#### Scenario: 统计与 stale 标记
- **WHEN** 库中有 2 条 executed、1 条 dropped、1 条 open 且已过 24h 的记录后调用 `list_impulses`
- **THEN** 统计为 total=4 / executed=2 / dropped=1 / open=1，已决中 executed 占比 2/3，超时 open 条目 stale=true

#### Scenario: 空窗口
- **WHEN** 窗口内无任何记录
- **THEN** 返回空清单与全零统计，不报错

### Requirement: 契约与隐私边界
impulses 相关工具 MUST 标注【仅 anchor 语境】；`shared_status` 的返回字段白名单 MUST 保持不变（impulses 不进入抽象状态导出）；MCP 契约测试的 allowed 工具集 SHALL 扩为 11 个，且改写词守门名单 SHALL 覆盖 impulse 目标（不存在 update/delete impulse 内容类工具，resolve 为唯一状态迁移通道）。

#### Scenario: shared_status 白名单不变
- **WHEN** 库中存在冲动记录后调用 `shared_status` 并检查返回
- **THEN** 字段仍为白名单五项，不含任何 impulse 内容或统计

#### Scenario: 契约测试守门扩容
- **WHEN** 运行 MCP 契约测试
- **THEN** allowed 集为 11 个工具（原 8 + impulse_checkpoint / resolve_impulse / list_impulses），且无任何 update/delete impulse 内容类工具

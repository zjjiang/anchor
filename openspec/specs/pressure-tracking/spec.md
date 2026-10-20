# pressure-tracking Specification

## Purpose
长期记录压力主要来自哪些领域（工作 / 家庭 / 其他关系 / 金钱 / 精力 / 自我评价），由龙虾在对话中从自然语言自动归类，用户无需手动分类；为周复盘与模式识别提供分布数据。

## Requirements

### Requirement: 记录压力条目
系统 SHALL 提供 `log_pressure` 工具，接受 `domain`（必填）、`note`（必填）、`occurred_at`（可选，默认当前 UTC 时间）、`checkin_id`（可选，关联某次 check-in）、`intensity`（可选，1-5 整数），写入后返回条目 id。

#### Scenario: 独立记录一条压力
- **WHEN** 龙虾调用 `log_pressure`，domain=work，note 描述具体事件
- **THEN** 系统存入一条压力记录并返回 id，checkin_id 与 intensity 为空

#### Scenario: 关联 check-in 记录
- **WHEN** `log_pressure` 携带已存在的 checkin_id
- **THEN** 该条记录的 checkin_id 正确落库

#### Scenario: 关联不存在的 check-in 被拒绝
- **WHEN** `log_pressure` 携带的 checkin_id 在库中不存在
- **THEN** 系统拒绝写入并返回中文错误信息

### Requirement: 压力领域枚举与兜底
domain SHALL 接受六个预置领域：`work`（工作/职业未来）、`family`（夫妻/家庭关系）、`relations`（其他关系）、`money`（金钱）、`energy`（精力状态）、`self`（自我评价），以及 free-text 兜底值；预置枚举之外的单个词按兜底处理时 MUST 保留原文以便后续归并。

#### Scenario: 预置领域直接接受
- **WHEN** domain 传入六个预置值之一（大小写不敏感）
- **THEN** 系统规范化为小写预置值后落库

#### Scenario: 未知领域走兜底
- **WHEN** domain 传入非预置值（如 "health"）
- **THEN** 系统接受并原样保留该值，标记为非预置领域，不报错

#### Scenario: 空领域被拒绝
- **WHEN** domain 为空或空白
- **THEN** 系统拒绝写入并返回中文错误信息

### Requirement: intensity 可选且有界
intensity 为可选项；提供时 SHALL 为 1-5 的整数，缺失时存 NULL。系统 SHALL NOT 要求用户每次打分。

#### Scenario: 合法强度落库
- **WHEN** intensity 传入 3
- **THEN** 记录的 intensity 为 3

#### Scenario: 越界强度被拒绝
- **WHEN** intensity 传入 0 或 6 或非整数
- **THEN** 系统拒绝写入并返回中文错误信息

### Requirement: 聚合查询
系统 SHALL 提供 `list_pressures` 工具，按天数窗口（默认 30 天）返回：按领域分组的计数分布、时间线明细（occurred_at、domain、note，不含任何 check-in 原文）、非预置领域的清单。

#### Scenario: 按领域聚合
- **WHEN** 近 30 天内有 5 条 work、2 条 family 记录后调用 `list_pressures`
- **THEN** 返回的分布中 work=5、family=2，明细按时间倒序

#### Scenario: 窗口内无数据
- **WHEN** 查询窗口内没有任何记录
- **THEN** 返回空分布与空明细，不报错

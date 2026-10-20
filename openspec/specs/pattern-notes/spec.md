# pattern-notes Specification

## Purpose
把对话中发现的重复压力/行为模式（如"工作焦虑上升时更容易冲动消费"）沉淀为可回顾的记录，关联证据 check-in；第一阶段由龙虾人工修养式维护，不做自动检测。

## Requirements

### Requirement: 记录模式
系统 SHALL 提供 `log_pattern` 工具，接受 `description`（必填，模式描述）、`evidence`（可选，check-in id 列表）、`status`（可选，默认 `active`）、`note`（可选补充说明），写入后返回模式 id。

#### Scenario: 带证据创建模式
- **WHEN** 龙虾调用 `log_pattern`，description 描述一个重复模式，evidence 携带 2 个已存在的 check-in id
- **THEN** 系统存入该模式，状态为 active，evidence 完整落库

#### Scenario: evidence 含不存在的 check-in 被拒绝
- **WHEN** evidence 中任一 id 在库中不存在
- **THEN** 系统拒绝写入并指出非法 id，不产生任何记录

### Requirement: 模式状态机
模式 status SHALL 限定为 `active`（观察中）、`watched`（已留意）、`resolved`（已化解）三种；系统 SHALL 提供更新模式状态的途径（更新工具），其他非法值被拒绝。

#### Scenario: 状态流转合法
- **WHEN** 将某模式从 active 更新为 resolved
- **THEN** 更新成功，状态变为 resolved

#### Scenario: 非法状态被拒绝
- **WHEN** 状态传入 "deleted" 等三个合法值之外的值
- **THEN** 系统拒绝并返回中文错误信息

### Requirement: 模式列表查询
系统 SHALL 提供 `list_patterns` 工具，返回全部模式（id、description、status、evidence 数量、note、first_seen/last_seen），默认按 last_seen 倒序；支持按 status 过滤。

#### Scenario: 全量回看
- **WHEN** 库中有 3 条不同状态的模式后调用 `list_patterns`
- **THEN** 返回 3 条，按 last_seen 倒序，每条含 evidence 数量

#### Scenario: 按状态过滤
- **WHEN** 以 status=active 调用 `list_patterns`
- **THEN** 仅返回 active 状态的模式

### Requirement: first_seen / last_seen 自动维护
系统 SHALL 在创建模式时写入 first_seen 与 last_seen（东八区日历日），并在模式被更新时刷新 last_seen；这两个字段由系统维护，MUST NOT 接受外部直接赋值。

#### Scenario: 创建即有时间戳
- **WHEN** 创建一条新模式
- **THEN** first_seen 与 last_seen 均为当天日历日

#### Scenario: 更新刷新 last_seen
- **WHEN** 次日更新某模式的 note
- **THEN** 该模式 last_seen 变为次日，first_seen 不变

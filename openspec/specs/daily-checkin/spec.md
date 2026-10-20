# daily-checkin Specification

## Purpose
让用户每天用自然语言说几句话就能完成 check-in：原文永久保留，同时把"事实 / 感受 / 担心 / 猜测放大 / 最小行动"五槽位梳理结果结构化落库，作为后续压力追踪与周复盘的原料。

## Requirements

### Requirement: 记录 check-in
系统 SHALL 提供 `log_checkin` 工具，接受 `raw_text`（必填，用户原话）、`checkin_date`（可选，默认东八区当天）、五个可选 digest 槽位（`fact` / `feeling` / `worry` / `speculation` / `next_action`），以及可选的 `pressures` 附带列表，写入后返回 check-in id。

#### Scenario: 完整五槽位落库
- **WHEN** 龙虾调用 `log_checkin`，raw_text 与五个槽位均非空
- **THEN** 系统存入一条 check-in 记录，raw_text 与五槽位原样保留，返回新 id

#### Scenario: 仅原话落库
- **WHEN** 龙虾只提供 raw_text（如闲聊式 check-in 无明确行动项）
- **THEN** 系统正常落库，digest 各槽位为空，不报错

#### Scenario: 缺少原话被拒绝
- **WHEN** `log_checkin` 调用缺失 raw_text 或 raw_text 为空白
- **THEN** 系统拒绝写入并返回中文错误信息，不产生任何记录

### Requirement: digest 槽位类型校验
系统 SHALL 校验五个 digest 槽位均为字符串类型且长度不超过 2000 字符，校验失败时拒绝整条写入。

#### Scenario: 槽位类型非法
- **WHEN** 任一 digest 槽位传入非字符串（如数字、嵌套对象）
- **THEN** 系统拒绝写入并指出非法槽位名

### Requirement: check-in 不可修改原文
check-in 落库后，系统 SHALL NOT 提供任何修改或删除 raw_text 的工具或接口；记录一经写入即为永久。

#### Scenario: 无改写通道
- **WHEN** 检查 MCP 工具面与 Web API
- **THEN** 不存在任何能变更已有 check-in 原文或 digest 的操作

### Requirement: 附带压力归类
`log_checkin` SHALL 支持在同一次调用中附带 0..n 条压力归类（domain + note），原子性地与 check-in 一并落库并自动关联 check-in id；任一压力条目非法时整次调用失败。

#### Scenario: 对话中一次完成梳理与归类
- **WHEN** 龙虾调用 `log_checkin` 时附带两条压力条目（如 work、family）
- **THEN** 一条 check-in 与两条 pressures 记录同时存在，且两条 pressures 的 checkin_id 均指向该 check-in

#### Scenario: 附带条目非法整体回滚
- **WHEN** 附带的压力条目中有一条 domain 非法
- **THEN** 本次调用失败，check-in 与 pressures 均不写入

### Requirement: 只读回看
系统 SHALL 提供按日期范围查询 check-in 摘要（id、日期、digest、关联压力领域）的只读途径（MCP 工具与 Web API 各一），摘要中 raw_text 仅在 MCP 单条详情中返回。

#### Scenario: 列表查询不泄露原文到看板
- **WHEN** 调用 check-in 列表类接口
- **THEN** 返回项包含 digest 与日期，不包含 raw_text 字段

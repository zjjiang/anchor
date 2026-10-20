# Spec Delta

## Purpose

Anchor 是 Personal OS 中最私密的子系统。本能力定义唯一跨系统出口 `shared_status`：只允许导出抽象后的状态（压力等级、领域分布、建议负荷），永不导出原文、关系细节与情绪内容；红线由 MCP 契约测试机器化验证。

## ADDED Requirements

### Requirement: 抽象状态导出
系统 SHALL 提供 `shared_status` 工具，接受可选天数窗口（默认 7 天），返回且仅返回以下抽象字段：`period`（窗口）、`overall_stress_level`（low / mid / high 三档，由窗口内压力条目数与 intensity 分布推导）、`top_domains`（按计数倒序的领域列表，每项含 domain 与 count）、`checkin_streak`（近窗口内有 check-in 的天数）、`note`（一句建议性摘要，由规则模板生成）。

#### Scenario: 正常导出
- **WHEN** 近 7 天有多条压力记录后调用 `shared_status`
- **THEN** 返回包含且仅包含上述五个抽象字段，其中 overall_stress_level 与 top_domains 与数据一致

#### Scenario: 空窗口导出
- **WHEN** 窗口内无任何记录
- **THEN** overall_stress_level 为 low，top_domains 为空，note 为中性摘要，不报错

### Requirement: 导出内容不含私密原文
`shared_status` 的返回 MUST NOT 包含任何 check-in 原文、digest 槽位内容、压力条目 note、模式 description 或自由文本字段；此约束为隐私红线。

#### Scenario: 返回中无原文类字段
- **WHEN** 调用 `shared_status` 并检查返回的每一个字段
- **THEN** 所有字段均为枚举值、计数、日期或规则模板生成的固定句式，不存在用户原话

### Requirement: 压力等级推导规则
overall_stress_level SHALL 由窗口内数据规则推导：无记录或计数 ≤ 阈值下界为 low；超过阈值上界，或高强度（intensity ≥ 4）条目占比过半，为 high；其间为 mid。阈值 SHALL 在领域常量中集中定义。

#### Scenario: 高强度条目推高等级
- **WHEN** 窗口内仅 2 条记录但均为 intensity 5
- **THEN** overall_stress_level 为 high

#### Scenario: 少量常规记录为中低档
- **WHEN** 窗口内 2 条 intensity 2 的记录
- **THEN** overall_stress_level 为 low 或 mid（依阈值），绝不为 high

### Requirement: 契约测试守门
系统 MUST 以 MCP 契约测试机器化验证隐私红线：断言 `shared_status` 真实返回的序列化结果中不出现任何库内 raw_text、digest 槽位、note、description 的值；该测试与"MCP 不提供改写 check-in 工具"的断言同为守门测试，MUST NOT 被删除。

#### Scenario: 泄露即测试失败
- **WHEN** 库中存在已知原文（如 "这是一句私密原话"）后运行契约测试
- **THEN** 断言 `shared_status` 的序列化返回中不包含该原文，若包含则测试失败

#### Scenario: 无改写工具守门
- **WHEN** 运行 MCP 契约测试检查工具清单
- **THEN** 不存在任何名称或 docstring 表明可修改/删除已有 check-in、pressure、pattern、review 的工具

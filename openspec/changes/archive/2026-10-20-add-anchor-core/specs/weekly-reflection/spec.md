# Spec Delta

## Purpose

每周一次简短复盘：系统聚合本周数据（压力分布、重复话题、check-in 摘要、模式变化），龙虾按人设回答五个固定问题后落库，形成可回看的周度档案。

## ADDED Requirements

### Requirement: 周数据包
系统 SHALL 提供 `get_week_data` 工具，接受可选的周起始日（默认东八区当前周的周一），返回该周数据包：check-in 列表（日期 + digest，不含 raw_text）、按领域分组的压力分布、逐日压力计数、本周活跃模式及其 evidence 数。

#### Scenario: 默认取当前周
- **WHEN** 不带参数调用 `get_week_data`
- **THEN** 返回东八区本周一至今的数据包

#### Scenario: 指定历史周
- **WHEN** 传入上一次 check-in 所在周的周起始日
- **THEN** 返回该自然周（7 天窗口）的数据

#### Scenario: 空周
- **WHEN** 指定周内没有任何 check-in 与压力记录
- **THEN** 返回空数据包，明确标记本周无记录，不报错

### Requirement: 保存周复盘
系统 SHALL 提供 `save_weekly_review` 工具，接受 `week_start`（必填，与数据包同口径的周起始日）、五个固定问题的回答（`main_sources` 主要压力来源、`recurring` 重复出现的问题、`easing_vs_worsening` 缓解 vs 恶化的行为、`improved` 本周改善、`focus_next` 下周最值得关注的一件事，均必填）、`narrative`（必填，复盘正文）。

#### Scenario: 完整复盘落库
- **WHEN** 龙虾填写全部必填项后调用 `save_weekly_review`
- **THEN** 系统存入一条周复盘并返回 id，created_at 为当前时间

#### Scenario: 缺失必填问题被拒绝
- **WHEN** 任一固定问题或 narrative 缺失或空白
- **THEN** 系统拒绝写入并指出缺失项

### Requirement: 同周唯一复盘
同一 week_start SHALL 至多存在一条复盘；对已有复盘的周再次保存时，系统 MUST 以新版本整体替换并在原记录上保留 replaced 标记与时间，而非追加平行记录。

#### Scenario: 重复保存走替换
- **WHEN** 对已有复盘的周再次调用 `save_weekly_review`
- **THEN** 旧复盘标记为 replaced 并记录替换时间，该周有效复盘仍只有一条

#### Scenario: 查询只看有效复盘
- **WHEN** 查询某周复盘时该周曾发生过替换
- **THEN** 仅返回替换后的最新版本

### Requirement: 复盘只读回看
系统 SHALL 提供按周查询历史复盘列表的只读途径（MCP 工具与 Web API 各一），返回 week_start、五个问题回答、narrative、created_at。

#### Scenario: 历史复盘列表
- **WHEN** 库中有 3 周复盘后调用列表接口
- **THEN** 返回 3 条，按 week_start 倒序

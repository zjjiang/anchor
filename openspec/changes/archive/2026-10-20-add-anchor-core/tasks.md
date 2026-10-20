# Tasks

## 1. 仓库脚手架

- [x] 1.1 建 `pyproject.toml`（Python >=3.12，deps：fastapi/fastmcp>=2.0/uvicorn；dev：pytest/ruff line-length=100）、`.gitignore`（data/、*.db、.venv、__pycache__）、空 `app/__init__.py`；`uv sync` 成功，`uv run python -c "import fastmcp"` 通过
- [x] 1.2 建 `openspec/project.md`（定位一句话、四子系统集成图、三条铁律、命令、范围纪律、成功标准），照 compass/steward 模板；内容与 README 定位一致
- [x] 1.3 建 `app/store/db.py`：`ANCHOR_DB` 环境变量覆盖、WAL+外键+busy_timeout、`SCHEMA_VERSION` + schema_version 表、四张表幂等建库（checkins/pressures/patterns/weekly_reviews）、`transaction()` 上下文管理器；`tests/test_store_db.py` 验证 fresh 建库与版本表写入

## 2. 领域常量与校验（privacy-boundary / pressure-tracking 的规则基座）

- [x] 2.1 建 `app/domain.py`：`PRESSURE_DOMAINS` 六域常量+中文标签、`normalize_domain()`（大小写规范化/兜底标记）、`validate_digest_slot()`（字符串、≤2000）、`validate_intensity()`（1-5 int 或 None）、`PATTERN_STATUSES` 三态、`STRESS_THRESHOLDS` 常量、`DomainError`；纯函数单元测试 `tests/test_domain.py` 全绿（TDD：先写测试）

## 3. Daily Check-in（daily-checkin spec）

- [x] 3.1 TDD `app/modules/checkin.py` 纯函数：`validate_payload()`（raw_text 必填非空白、五槽位校验、附带 pressures 校验）、`summarize()`；`tests/test_checkin_module.py` Red→Green
- [x] 3.2 TDD `app/store/checkins.py`：`insert()`（含附带 pressures 原子写入，事务内失败整体回滚）、`get()`、`list_range()`（摘要不含 raw_text）；`tests/test_store_checkins.py` 覆盖含/无 digest、原子回滚、checkin_id 外键拒绝不存在引用（pressures 侧）
- [x] 3.3 TDD `app/store/pressures.py`：`insert()`（domain 规范化、intensity 校验、checkin_id 存在性检查）、`list_window()`（分布聚合+明细+非预置域清单）；`tests/test_store_pressures.py` 覆盖预置/兜底/空窗三场景

## 4. 模式记录（pattern-notes spec）

- [x] 4.1 TDD `app/store/patterns.py`：`insert()`（evidence 存在性校验、first_seen/last_seen 自动东八区日历日、拒绝外部赋值）、`update_status()`/`update_note()`（刷新 last_seen、非法状态拒绝）、`list_all()`/`list_by_status()`；`tests/test_store_patterns.py` 覆盖状态机与时间戳自动维护

## 5. Weekly Reflection（weekly-reflection spec）

- [x] 5.1 TDD `app/modules/weekly.py` 纯函数：`week_start_of()`（东八区周一）、`build_week_data()`（从 checkins/pressures/patterns 聚合数据包，不含 raw_text）、`validate_review_payload()`（五问+narrative 必填）；`tests/test_weekly_module.py` 覆盖默认周/指定周/空周
- [x] 5.2 TDD `app/store/weekly.py`：`save()`（同周唯一，replaced_at 标记旧版）、`get_by_week()`（仅返回有效版）、`list_reviews()`（倒序）；`tests/test_store_weekly.py` 覆盖重复保存替换与查询口径

## 6. 抽象导出（privacy-boundary spec）

- [x] 6.1 TDD `app/modules/shared_status.py` 纯函数：`derive_stress_level()`（阈值规则：计数阈值+intensity≥4 占比）、`build_shared_status()`（五字段白名单，note 规则模板生成）；`tests/test_shared_status_module.py` 覆盖空窗/high 推导/中低档三场景
- [x] 6.2 TDD `app/store` 层支撑查询（如需独立计数查询，挂在既有 store 文件）；确认 `shared_status` 链路无任何 raw 字段取出（代码走查 + 测试断言）

## 7. MCP 工具面

- [x] 7.1 建 `app/mcp_server.py`：FastMCP + 中文 `INSTRUCTIONS`（内在教练章程精简版：五槽位用法、domain 归类规则、【仅 anchor 语境】标注约定）；注册 8 个工具 `log_checkin`/`log_pressure`/`list_pressures`/`get_week_data`/`save_weekly_review`/`log_pattern`/`list_patterns`/`shared_status`，全部 `ensure_ready()` + `DomainError→ToolError` 中文转译；`scripts/smoke_stdio.py` 子进程全链路冒烟跑通
- [x] 7.2 TDD `tests/test_mcp_contract.py` 守门测试：① 库埋已知原文后 `shared_status` 序列化返回不含该原文及任何 note/description 值；② 工具清单无改写/删除类工具；③ `fastmcp.Client` 内存调用 8 个工具成功路径与中文错误路径

## 8. 只读 Web 看板（端口 8903）

- [x] 8.1 建 `app/api.py`：只读 GET 端点（check-in 列表/压力分布/模式列表/周复盘列表）+ lifespan `ensure_ready()` + `DomainError→400`、`KeyError→404`；`tests/test_web_routes.py` 用 TestClient 验证响应不含 raw_text
- [x] 8.2 建 `app/web/index.html`：单文件原生 HTML/CSS/JS（同 compass 风格，暗色适配），四区块：近期 check-in（digest 卡片，无原文）、压力领域分布、模式列表、周复盘归档；`uv run uvicorn app.api:app --port 8903` 手工过一遍

## 9. 龙虾侧文档与收尾

- [x] 9.1 写 `docs/anchor-guide.md`：内在教练人设（冷静、不附和、不扮演恋人、放慢决策、不强化依赖）、check-in SOP（含五槽位正反例）、weekly SOP（cron 周日触发流程）、隐私规则（非 anchor 语境不调明细工具，只用 shared_status）
- [x] 9.2 写 `docs/lobster-setup.md`：stdio JSON 配置（绝对 cwd + `uv run python -m app.mcp_server`）、ANCHOR_DB 说明、data/anchor.db 敏感级别提示（高于 deputy/steward）；写 `README.md`：定位一句话（deputy 管事业、steward 管生活、compass 管方向、anchor 管心绪）、四条启动命令、红线
- [x] 9.3 全量验证：`uv run pytest -q` 全绿 + `uv run ruff check .` 干净 + `scripts/smoke_stdio.py` 通过 + `openspec validate add-anchor-core` 通过

## Workflow follow-up

- 实现走分支 `feat/add-anchor-core`，PR 合入（push 前找用户确认）
- 合入后 `/opsx:archive` 归档本 change，specs 落入 `openspec/specs/`
- Phase 2 候选（不排期）：Impulse Guard、自动模式检测、shared_status 与 deputy/steward 接线、自由文本 domain 归并

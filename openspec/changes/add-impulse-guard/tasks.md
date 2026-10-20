# Tasks

## 1. 领域常量与 schema

- [x] 1.1 TDD `app/domain.py` 追加：`IMPULSE_KINDS` 五枚举（spending/transfer/conflict/resignation/other + 中文标签）、`normalize_impulse_kind()`（大小写归一 + 未知兜底原样保留）、`IMPULSE_OUTCOMES`（executed/dropped）、`IMPULSE_CHECKLIST_TEMPLATES`（三提示模板句常量）、`IMPULSIVE_WINDOW_HOURS=24`；`tests/test_domain.py` 补对应用例跑绿
- [x] 1.2 `app/store/db.py`：`_SCHEMA` 追加 `impulses` 表（id/occurred_at/kind/is_custom_kind/claim/amount/emotion_level/note/status/decision_due/decided_at/created_at + idx）、`SCHEMA_VERSION` 1→2；`tests/test_store_db.py` 验证新表创建与版本 2

## 2. impulses store（impulse-guard spec 核心）

- [x] 2.1 TDD `tests/test_store_impulses.py` + `app/store/impulses.py`：`insert()`（claim 必填、amount 可选数值、emotion_level 复用 intensity 校验、decision_due=+24h）、`resolve()`（open→executed/dropped、decided_at、非 open/不存在拒绝）、`list_window()`（清单+统计 total/executed/dropped/open/ratio、stale 派生）；Red→Green 后全量回归

## 3. MCP 工具面（3 个新工具 + 契约扩容）

- [x] 3.1 `app/mcp_server.py`：薄签名 + impl 模式加 `impulse_checkpoint`（返回 id+检查单模板 JSON）/`resolve_impulse`/`list_impulses`，全部【仅 anchor 语境】docstring
- [x] 3.2 TDD `tests/test_mcp_contract.py` 扩容：allowed 集 8→11、mutable_targets 加 "impulse"、新工具成功路径与中文错误路径、`shared_status` 白名单在库含 impulse 记录时不变的泄露断言；`tests/test_shared_status_module.py` 补"impulses 不入白名单"用例
- [x] 3.3 `scripts/smoke_stdio.py` 追加：checkpoint 落库 → 检查单四要素断言 → resolve 回填 → list 统计断言；全链路跑通

## 4. 文档与收尾

- [x] 4.1 `docs/anchor-guide.md`：Impulse 纪律从"人设约定"升级为工具流程 SOP（触发词 → 先 checkpoint 再对话 → 24h 后 resolve → 周复盘清 stale）；`docs/lobster-setup.md` 工具清单 8→11
- [x] 4.2 全量验证：`uv run pytest -q` 全绿 + `uv run ruff check .` 干净 + `uv run python scripts/smoke_stdio.py` 通过 + `openspec validate add-impulse-guard` 通过

## Workflow follow-up

- 走 `feat/add-impulse-guard` 分支，PR 合入（push 前找用户确认）
- 合入后 `/opsx:archive` 归档，主 specs 新增 impulse-guard

# 龙虾接入指南（Anchor × OpenClaw）

Anchor 是 MCP stdio server，与 deputy/steward/compass 同构：龙虾拉起子进程，无需端口、
无需鉴权、数据不出本机。

## 1. 前置

```bash
cd ~/Projects/anchor
uv sync            # 装依赖
uv run pytest -q   # 应全绿
```

## 2. 龙虾 MCP 配置

在 OpenClaw 的 MCP 配置中加入（绝对 cwd，与 steward/deputy 条目并列）：

```json
{
  "mcpServers": {
    "anchor": {
      "command": "uv",
      "args": ["run", "python", "-m", "app.mcp_server"],
      "cwd": "/Users/jiangzhijian/Projects/anchor"
    }
  }
}
```

重启龙虾后确认工具清单出现 8 个：`log_checkin` / `log_pressure` / `list_pressures` /
`get_week_data` / `save_weekly_review` / `log_pattern` / `list_patterns` / `shared_status`。

> MCP 面任何改动后必跑：`uv run python scripts/smoke_stdio.py`

## 3. 人设配置

按 `docs/anchor-guide.md` 配置 Anchor 分身（人设 + check-in/weekly SOP + 隐私规则）。
核心三条：内在教练不附和、五槽位用人话梳理、非 anchor 语境只碰 `shared_status`。

## 4. Cron 建议

- 晚间 check-in 提醒：每天一次（用户未主动聊时轻提醒，不催）
- 周复盘：周日晚间，流程见 anchor-guide Weekly SOP

## 5. 数据与敏感级别

- 数据库：`data/anchor.db`（首次写自动创建），可用环境变量 `ANCHOR_DB` 覆盖路径
- **敏感级别高于 deputy/steward**：库内含情绪原文与家庭/关系细节。不要备份到云端明文目录、
  不要把库文件发给任何工具或人
- 端口 8903 只读看板（可选）：`uv run uvicorn app.api:app --port 8903`

## 6. 冒烟自检

```bash
uv run python scripts/smoke_stdio.py   # 12 项 stdio 全链路
uv run pytest -q                       # 108 个测试
```

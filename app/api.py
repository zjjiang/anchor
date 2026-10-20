"""Anchor 只读看板 API（127.0.0.1:8903）：给人类回看，不给写通道。

规矩：所有端点只读；响应永不包含 check-in 原文（shared_status 同款口径）；
DomainError→400、KeyError→404；lifespan 懒建库。
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from app import domain
from app.modules import checkin as checkin_module
from app.modules import shared_status as shared_status_module
from app.store import checkins as checkins_store
from app.store import db
from app.store import patterns as patterns_store
from app.store import pressures as pressures_store
from app.store import weekly as weekly_store

_WEB_DIR = Path(__file__).parent / "web"


_WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(title="anchor", docs_url=None, redoc_url=None)


@app.exception_handler(domain.DomainError)
async def _domain_error(_: Request, exc: domain.DomainError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(KeyError)
async def _key_error(_: Request, exc: KeyError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": f"不存在：{exc.args[0]}"})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_WEB_DIR / "index.html")


@app.get("/api/checkins")
def api_checkins(days: int = 30) -> list[dict[str, Any]]:
    """近 N 天 check-in 摘要（digest + 压力领域，无原文）。"""
    end = db.today_cst()
    start = (db.utcnow_dt() + timedelta(hours=8) - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    rows = checkins_store.list_range(start, end)
    return [checkin_module.summarize(r) for r in rows]


@app.get("/api/pressures")
def api_pressures(days: int = 30) -> dict[str, Any]:
    return pressures_store.list_window(days=days)


@app.get("/api/patterns")
def api_patterns(status: str | None = None) -> list[dict[str, Any]]:
    if status:
        return patterns_store.list_by_status(status)
    return patterns_store.list_all()


@app.get("/api/reviews")
def api_reviews() -> list[dict[str, Any]]:
    return weekly_store.list_reviews()


@app.get("/api/summary")
def api_summary(days: int = 7) -> dict[str, Any]:
    """看板顶栏的抽象状态（与 shared_status 同口径，只读）。"""
    window = pressures_store.list_window(days=days)
    end = db.today_cst()
    start = (db.utcnow_dt() + timedelta(hours=8) - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    rows = checkins_store.list_range(start, end)
    return shared_status_module.build_shared_status(
        days=days,
        distribution=window["distribution"],
        intensities=[p["intensity"] for p in window["timeline"]],
        checkin_dates=[c["checkin_date"] for c in rows],
    )

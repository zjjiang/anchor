"""测试隔离：每个测试用独立临时库，monkeypatch ANCHOR_DB 环境变量。"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """把 DB 指向临时路径并重新加载 store.db，测试间零共享。"""
    db_file = tmp_path / "test_anchor.db"
    monkeypatch.setenv("ANCHOR_DB", str(db_file))
    from app.store import db

    importlib.reload(db)
    db.init_db()
    yield db

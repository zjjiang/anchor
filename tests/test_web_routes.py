"""Web API：只读端点，响应永不包含 raw_text（隐私红线在 API 层同样成立）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.modules import checkin as checkin_module
from app.store import checkins as checkins_store
from app.store import patterns as patterns_store
from app.store import pressures as pressures_store
from app.store import weekly as weekly_store


@pytest.fixture()
def client(fresh_db):
    with TestClient(app) as c:
        yield c


def _seed():
    cid = checkins_store.insert(
        checkin_module.validate_payload({"raw_text": "看板不该显示的原话", "fact": "事实F"})
    )
    pressures_store.insert(
        {"domain": "work", "is_preset": True, "note": "返工", "checkin_id": cid, "intensity": 3}
    )
    patterns_store.insert({"description": "模式D", "evidence": [cid]})
    weekly_store.save(
        {
            "week_start": "2026-10-19",
            "main_sources": "s",
            "recurring": "r",
            "easing_vs_worsening": "e",
            "improved": "i",
            "focus_next": "f",
            "narrative": "正文",
        }
    )


class TestReadOnlyEndpoints:
    def test_api_checkins_no_raw_text(self, client):
        _seed()
        resp = client.get("/api/checkins?days=30")
        assert resp.status_code == 200
        rows = resp.json()
        assert rows and all("raw_text" not in r for r in rows)
        assert rows[0]["fact"] == "事实F"

    def test_api_pressures(self, client):
        _seed()
        data = client.get("/api/pressures?days=30").json()
        assert data["distribution"] == [{"domain": "work", "count": 1}]
        assert "看板不该显示的原话" not in str(data)

    def test_api_patterns(self, client):
        _seed()
        rows = client.get("/api/patterns").json()
        assert rows[0]["description"] == "模式D"
        assert rows[0]["evidence_count"] == 1

    def test_api_reviews(self, client):
        _seed()
        rows = client.get("/api/reviews").json()
        assert rows[0]["week_start"] == "2026-10-19"
        assert rows[0]["narrative"] == "正文"

    def test_api_summary(self, client):
        _seed()
        data = client.get("/api/summary").json()
        assert set(data) == {"period", "overall_stress_level", "top_domains",
                             "checkin_streak", "note"}
        assert "看板不该显示的原话" not in str(data)

    def test_index_served(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Anchor" in resp.text

    def test_no_write_endpoints(self, client):
        """看板只读：写请求一律被拒（405 未实现 / 404 无路由）。"""
        assert client.post("/api/checkins", json={}).status_code == 405
        assert client.delete("/api/patterns/pt1").status_code in (404, 405)

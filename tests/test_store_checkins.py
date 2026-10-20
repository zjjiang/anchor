"""store.checkins：落库、原子附带写入、摘要查询（不含原文）。"""

from __future__ import annotations

import pytest

from app import domain
from app.modules import checkin
from app.store import checkins as checkins_store


def _payload(**overrides):
    base = {"raw_text": "今天有点烦", "fact": "方案被打回"}
    base.update(overrides)
    return checkin.validate_payload(base)


class TestInsert:
    def test_insert_returns_id_and_stores_digest(self, fresh_db):
        data = _payload(next_action="明天约老板")
        cid = checkins_store.insert(data)
        assert cid == "c1"
        row = checkins_store.get(cid)
        assert row["raw_text"] == "今天有点烦"
        assert row["fact"] == "方案被打回"
        assert row["next_action"] == "明天约老板"
        assert row["checkin_date"] == data["checkin_date"]

    def test_ids_increment(self, fresh_db):
        first = checkins_store.insert(_payload())
        second = checkins_store.insert(_payload())
        assert (first, second) == ("c1", "c2")

    def test_atomic_pressures(self, fresh_db):
        data = _payload(
            pressures=[
                {"domain": "work", "note": "返工"},
                {"domain": "SELF", "note": "自我怀疑", "intensity": 4},
            ]
        )
        cid = checkins_store.insert(data)
        from app.store import pressures as pressures_store

        window = pressures_store.list_window(days=7)
        assert window["distribution"] == [
            {"domain": "self", "count": 1},
            {"domain": "work", "count": 1},
        ]
        rows = checkins_store.list_range("2000-01-01", "2999-12-31")
        assert rows[0]["pressure_domains"] == ["work", "self"]
        detail = checkins_store.get(cid)
        assert detail["id"] == cid

    def test_atomic_rollback_on_bad_pressure(self, fresh_db):
        # 绕过模块校验，直接构造带非法附带条目的 data 模拟事务中途失败
        data = _payload()
        data["pressures"] = [
            {"domain": "work", "is_preset": True, "note": "ok", "intensity": None},
            {"domain": "", "is_preset": False, "note": "bad", "intensity": None},
        ]
        with pytest.raises(domain.DomainError):
            checkins_store.insert(data)
        assert checkins_store.list_range("2000-01-01", "2999-12-31") == []
        from app.store import pressures as pressures_store

        assert pressures_store.list_window(days=7)["timeline"] == []


class TestListRange:
    def test_summary_has_no_raw_text(self, fresh_db):
        checkins_store.insert(_payload(raw_text="私密原话"))
        rows = checkins_store.list_range("2000-01-01", "2999-12-31")
        assert len(rows) == 1
        assert "raw_text" not in rows[0]
        assert rows[0]["fact"] == "方案被打回"

    def test_date_window_filters(self, fresh_db):
        data = _payload()
        data["checkin_date"] = "2026-01-15"
        checkins_store.insert(data)
        data2 = _payload()
        data2["checkin_date"] = "2026-02-15"
        checkins_store.insert(data2)
        rows = checkins_store.list_range("2026-02-01", "2026-02-28")
        assert len(rows) == 1 and rows[0]["checkin_date"] == "2026-02-15"

    def test_list_ordered_by_date_desc(self, fresh_db):
        for day in ("2026-01-15", "2026-03-01", "2026-02-10"):
            data = _payload()
            data["checkin_date"] = day
            checkins_store.insert(data)
        rows = checkins_store.list_range("2000-01-01", "2999-12-31")
        assert [r["checkin_date"] for r in rows] == ["2026-03-01", "2026-02-10", "2026-01-15"]

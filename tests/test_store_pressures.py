"""store.pressures：独立落库、checkin 关联校验、窗口聚合。"""

from __future__ import annotations

import pytest

from app import domain
from app.store import checkins as checkins_store
from app.store import pressures as pressures_store


class TestInsert:
    def test_insert_independent_entry(self, fresh_db):
        pid = pressures_store.insert(
            {"domain": "money", "is_preset": True, "note": "房租压力", "intensity": None}
        )
        assert pid == "p1"
        window = pressures_store.list_window(days=30)
        assert window["distribution"] == [{"domain": "money", "count": 1}]

    def test_unknown_domain_marked_custom(self, fresh_db):
        pressures_store.insert(
            {"domain": "health", "is_preset": False, "note": "体检", "intensity": None}
        )
        window = pressures_store.list_window(days=30)
        assert window["distribution"] == [{"domain": "health", "count": 1}]
        assert window["custom_domains"] == ["health"]

    def test_checkin_reference_validated(self, fresh_db):
        with pytest.raises(domain.DomainError, match="check-in"):
            pressures_store.insert(
                {
                    "domain": "work",
                    "is_preset": True,
                    "note": "x",
                    "intensity": None,
                    "checkin_id": "c404",
                }
            )

    def test_link_to_existing_checkin(self, fresh_db):
        data = {"raw_text": "x"}
        from app.modules import checkin

        cid = checkins_store.insert(checkin.validate_payload(data))
        pressures_store.insert(
            {
                "domain": "family",
                "is_preset": True,
                "note": "吵架",
                "intensity": None,
                "checkin_id": cid,
            }
        )
        timeline = pressures_store.list_window(days=30)["timeline"]
        assert timeline[0]["checkin_id"] == cid

    def test_intensity_validated(self, fresh_db):
        with pytest.raises(domain.DomainError):
            pressures_store.insert(
                {"domain": "work", "is_preset": True, "note": "x", "intensity": 9}
            )

    def test_occurred_at_default_now(self, fresh_db):
        pressures_store.insert(
            {"domain": "work", "is_preset": True, "note": "x", "intensity": None}
        )
        timeline = pressures_store.list_window(days=30)["timeline"]
        assert "T" in timeline[0]["occurred_at"]


class TestListWindow:
    def test_distribution_ordered_by_count_desc(self, fresh_db):
        for note, dom in [("a", "work"), ("b", "work"), ("c", "work"),
                          ("d", "family"), ("e", "family"), ("f", "self")]:
            pressures_store.insert(
                {"domain": dom, "is_preset": dom != "self", "note": note, "intensity": None}
            )
        window = pressures_store.list_window(days=30)
        assert window["distribution"] == [
            {"domain": "work", "count": 3},
            {"domain": "family", "count": 2},
            {"domain": "self", "count": 1},
        ]

    def test_timeline_excludes_digest_and_raw(self, fresh_db):
        from app.modules import checkin

        cid = checkins_store.insert(checkin.validate_payload({"raw_text": "私密原话", "fact": "f"}))
        pressures_store.insert(
            {
                "domain": "work",
                "is_preset": True,
                "note": "压力事件",
                "intensity": 2,
                "checkin_id": cid,
            }
        )
        (item,) = pressures_store.list_window(days=30)["timeline"]
        assert item["note"] == "压力事件"
        assert "raw_text" not in item and "fact" not in item

    def test_empty_window(self, fresh_db):
        window = pressures_store.list_window(days=30)
        assert window == {"distribution": [], "timeline": [], "custom_domains": []}

    def test_window_filters_old_entries(self, fresh_db):
        pressures_store.insert(
            {
                "domain": "work",
                "is_preset": True,
                "note": "旧的",
                "intensity": None,
                "occurred_at": "2020-01-01T00:00:00+00:00",
            }
        )
        pressures_store.insert(
            {"domain": "work", "is_preset": True, "note": "新的", "intensity": None}
        )
        window = pressures_store.list_window(days=30)
        assert [t["note"] for t in window["timeline"]] == ["新的"]

    def test_timeline_newest_first(self, fresh_db):
        for occurred_at in ("2026-10-01T00:00:00+00:00", "2026-10-05T00:00:00+00:00"):
            pressures_store.insert(
                {
                    "domain": "work",
                    "is_preset": True,
                    "note": occurred_at[:10],
                    "intensity": None,
                    "occurred_at": occurred_at,
                }
            )
        notes = [t["note"] for t in pressures_store.list_window(days=30)["timeline"]]
        assert notes == ["2026-10-05", "2026-10-01"]

"""store.impulses：检查点落库、resolve 状态迁移、清单统计与 stale 派生。"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app import domain
from app.store import impulses as impulses_store


class TestInsert:
    def test_insert_open_with_due(self, fresh_db):
        iid = impulses_store.insert(
            {"kind": "spending", "claim": "买 12800 的笔记本", "amount": 12800}
        )
        assert iid == "i1"
        row = impulses_store.get(iid)
        assert row["status"] == "open"
        assert row["kind"] == "spending"
        assert row["amount"] == 12800
        # decision_due = occurred_at + 24h
        occurred = __import__("datetime").datetime.fromisoformat(row["occurred_at"])
        due = __import__("datetime").datetime.fromisoformat(row["decision_due"])
        assert due - occurred == timedelta(hours=domain.IMPULSIVE_WINDOW_HOURS)

    def test_claim_required(self, fresh_db):
        for bad in [{"kind": "spending"}, {"kind": "spending", "claim": "  "}, {"kind": "spending", "claim": None}]:
            with pytest.raises(domain.DomainError, match="claim"):
                impulses_store.insert(bad)

    def test_kind_required_and_fallback(self, fresh_db):
        assert impulses_store.insert({"kind": "conflict", "claim": "吵架"}) is not None
        iid = impulses_store.insert({"kind": "Investment", "claim": "投一笔钱"})
        assert impulses_store.get(iid)["kind"] == "investment"
        assert impulses_store.get(iid)["is_custom_kind"] is True

    def test_missing_kind_rejected(self, fresh_db):
        with pytest.raises(domain.DomainError, match="类型"):
            impulses_store.insert({"claim": "x"})

    def test_emotion_level_uses_intensity_rule(self, fresh_db):
        with pytest.raises(domain.DomainError):
            impulses_store.insert({"kind": "spending", "claim": "x", "emotion_level": 6})
        iid = impulses_store.insert({"kind": "spending", "claim": "x", "emotion_level": 5})
        assert impulses_store.get(iid)["emotion_level"] == 5

    def test_amount_must_be_number(self, fresh_db):
        with pytest.raises(domain.DomainError, match="amount"):
            impulses_store.insert({"kind": "spending", "claim": "x", "amount": "很多"})

    def test_ids_increment(self, fresh_db):
        first = impulses_store.insert({"kind": "other", "claim": "a"})
        second = impulses_store.insert({"kind": "other", "claim": "b"})
        assert (first, second) == ("i1", "i2")


class TestResolve:
    def test_resolve_dropped(self, fresh_db):
        iid = impulses_store.insert({"kind": "spending", "claim": "x"})
        impulses_store.resolve(iid, "dropped", note="睡一觉后不想要了")
        row = impulses_store.get(iid)
        assert row["status"] == "dropped"
        assert row["decided_at"] is not None
        assert row["note"] == "睡一觉后不想要了"

    def test_resolve_executed(self, fresh_db):
        iid = impulses_store.insert({"kind": "resignation", "claim": "提辞职"})
        impulses_store.resolve(iid, "executed")
        assert impulses_store.get(iid)["status"] == "executed"

    def test_double_resolve_rejected(self, fresh_db):
        iid = impulses_store.insert({"kind": "other", "claim": "x"})
        impulses_store.resolve(iid, "dropped")
        with pytest.raises(domain.DomainError, match="已回填"):
            impulses_store.resolve(iid, "executed")

    def test_missing_rejected(self, fresh_db):
        with pytest.raises(KeyError):
            impulses_store.resolve("i404", "dropped")

    def test_bad_outcome_rejected(self, fresh_db):
        iid = impulses_store.insert({"kind": "other", "claim": "x"})
        with pytest.raises(domain.DomainError):
            impulses_store.resolve(iid, "maybe")


class TestListWindow:
    def _seed(self):
        i1 = impulses_store.insert({"kind": "spending", "claim": "a"})
        i2 = impulses_store.insert({"kind": "transfer", "claim": "b"})
        i3 = impulses_store.insert({"kind": "conflict", "claim": "c"})
        i4 = impulses_store.insert({"kind": "other", "claim": "d"})
        impulses_store.resolve(i1, "executed")
        impulses_store.resolve(i2, "executed")
        impulses_store.resolve(i3, "dropped")
        return i4  # 保持 open

    def test_stats_exclude_open_from_ratio(self, fresh_db):
        self._seed()
        data = impulses_store.list_window(days=30)
        assert data["stats"] == {
            "total": 4,
            "executed": 2,
            "dropped": 1,
            "open": 1,
            "executed_ratio": 2 / 3,
        }

    def test_stale_marked_but_not_in_open_decay(self, fresh_db, monkeypatch):
        i_open = self._seed()
        # 把 i_open 的 decision_due 推到过去，模拟超时未回填
        with fresh_db.transaction() as conn:
            conn.execute(
                "UPDATE impulses SET decision_due = '2020-01-01T00:00:00+00:00' WHERE id = ?",
                (i_open,),
            )
        (item,) = [x for x in impulses_store.list_window(days=30)["items"] if x["id"] == i_open]
        assert item["stale"] is True
        assert item["status"] == "open"

    def test_empty_window(self, fresh_db):
        data = impulses_store.list_window(days=30)
        assert data["items"] == []
        assert data["stats"] == {
            "total": 0,
            "executed": 0,
            "dropped": 0,
            "open": 0,
            "executed_ratio": None,
        }

    def test_window_filters_and_newest_first(self, fresh_db):
        impulses_store.insert(
            {
                "kind": "spending",
                "claim": "旧的",
                "occurred_at": "2020-01-01T00:00:00+00:00",
            }
        )
        impulses_store.insert({"kind": "spending", "claim": "新的"})
        data = impulses_store.list_window(days=30)
        assert [i["claim"] for i in data["items"]] == ["新的"]

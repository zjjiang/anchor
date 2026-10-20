"""store.patterns：模式记录、evidence 校验、状态机、时间戳自动维护。"""

from __future__ import annotations

import pytest

from app import domain
from app.modules import checkin as checkin_module
from app.store import checkins as checkins_store
from app.store import patterns as patterns_store


def _make_checkin() -> str:
    return checkins_store.insert(checkin_module.validate_payload({"raw_text": "x"}))


class TestInsert:
    def test_insert_defaults(self, fresh_db):
        pid = patterns_store.insert({"description": "工作焦虑上升时容易冲动消费"})
        assert pid == "pt1"
        row = patterns_store.get(pid)
        assert row["status"] == "active"
        assert row["evidence"] == []
        assert row["first_seen"] == row["last_seen"] == row["first_seen"]

    def test_insert_with_evidence(self, fresh_db):
        c1, c2 = _make_checkin(), _make_checkin()
        pid = patterns_store.insert({"description": "低精力日易起冲突", "evidence": [c1, c2]})
        row = patterns_store.get(pid)
        assert row["evidence"] == [c1, c2]

    def test_evidence_must_exist(self, fresh_db):
        with pytest.raises(domain.DomainError, match="c404"):
            patterns_store.insert({"description": "x", "evidence": ["c404"]})

    def test_description_required(self, fresh_db):
        for bad in [{}, {"description": "  "}, {"description": None}]:
            with pytest.raises(domain.DomainError, match="描述"):
                patterns_store.insert(bad)

    def test_timestamps_not_assignable(self, fresh_db):
        """first_seen/last_seen 由系统维护，外部赋值被忽略。"""
        pid = patterns_store.insert(
            {"description": "x", "first_seen": "1999-01-01", "last_seen": "1999-01-01"}
        )
        row = patterns_store.get(pid)
        assert row["first_seen"] != "1999-01-01"


class TestUpdateStatus:
    def test_legal_transition(self, fresh_db):
        pid = patterns_store.insert({"description": "x"})
        patterns_store.update_status(pid, "resolved")
        assert patterns_store.get(pid)["status"] == "resolved"

    def test_illegal_status_rejected(self, fresh_db):
        pid = patterns_store.insert({"description": "x"})
        with pytest.raises(domain.DomainError):
            patterns_store.update_status(pid, "deleted")

    def test_missing_pattern_keyerror(self, fresh_db):
        with pytest.raises(KeyError):
            patterns_store.update_status("pt404", "active")


class TestUpdateNote:
    def test_note_updated_and_last_seen_refreshed(self, fresh_db, monkeypatch):
        pid = patterns_store.insert({"description": "x", "note": "初版"})
        # 模拟次日
        real = patterns_store.db.today_cst
        monkeypatch.setattr(patterns_store.db, "today_cst", lambda: "2026-10-21")
        try:
            patterns_store.update_note(pid, "补充观察")
        finally:
            monkeypatch.setattr(patterns_store.db, "today_cst", real)
        row = patterns_store.get(pid)
        assert row["note"] == "补充观察"
        assert row["last_seen"] == "2026-10-21"
        assert row["first_seen"] != "2026-10-21"


class TestList:
    def test_list_all_newest_first(self, fresh_db, monkeypatch):
        patterns_store.insert({"description": "旧模式"})
        monkeypatch.setattr(patterns_store.db, "today_cst", lambda: "2026-10-21")
        patterns_store.insert({"description": "新模式"})
        rows = patterns_store.list_all()
        assert [r["description"] for r in rows] == ["新模式", "旧模式"]
        assert "evidence" not in rows[0]  # 列表只给 evidence 数量
        assert rows[0]["evidence_count"] == 0

    def test_filter_by_status(self, fresh_db):
        p1 = patterns_store.insert({"description": "a"})
        patterns_store.insert({"description": "b"})
        patterns_store.update_status(p1, "resolved")
        rows = patterns_store.list_by_status("resolved")
        assert [r["description"] for r in rows] == ["a"]
        assert patterns_store.list_by_status("watched") == []

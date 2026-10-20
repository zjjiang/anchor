"""modules.checkin：payload 校验与摘要纯函数。"""

from __future__ import annotations

import pytest

from app import domain
from app.modules import checkin


class TestValidatePayload:
    def test_full_payload_normalized(self):
        payload = {
            "raw_text": " 今天有点烦，方案又被打回了 ",
            "fact": "方案第三次被打回",
            "feeling": "烦躁、有点羞愧",
            "worry": "怕老板觉得我能力不行",
            "speculation": "'能力不行'是我的猜测",
            "next_action": "明天上午约老板15分钟对齐方向",
            "pressures": [
                {"domain": "Work", "note": "方案返工"},
                {"domain": "self", "note": "自我怀疑", "intensity": 4},
            ],
        }
        data = checkin.validate_payload(payload)
        assert data["raw_text"] == "今天有点烦，方案又被打回了"
        assert data["checkin_date"] == data["checkin_date"]  # 由实现填默认日
        assert len(data["pressures"]) == 2
        assert data["pressures"][0]["domain"] == "work"
        assert data["pressures"][0]["is_preset"] is True
        assert data["pressures"][0]["intensity"] is None
        assert data["pressures"][1]["intensity"] == 4

    def test_minimal_payload_only_raw_text(self):
        data = checkin.validate_payload({"raw_text": "就是想记录一下"})
        assert data["raw_text"] == "就是想记录一下"
        assert all(data[slot] is None for slot in domain.DIGEST_SLOTS)
        assert data["pressures"] == []

    def test_missing_raw_text_rejected(self):
        for payload in [{}, {"raw_text": "   "}, {"raw_text": None}]:
            with pytest.raises(domain.DomainError, match="原话"):
                checkin.validate_payload(payload)

    def test_digest_slot_type_rejected(self):
        with pytest.raises(domain.DomainError, match="feeling"):
            checkin.validate_payload({"raw_text": "x", "feeling": 3})

    def test_explicit_checkin_date_kept(self):
        data = checkin.validate_payload({"raw_text": "x", "checkin_date": "2026-10-19"})
        assert data["checkin_date"] == "2026-10-19"

    def test_bad_checkin_date_rejected(self):
        with pytest.raises(domain.DomainError, match="日期"):
            checkin.validate_payload({"raw_text": "x", "checkin_date": "19/10/2026"})

    def test_pressure_entry_missing_note_rejected(self):
        with pytest.raises(domain.DomainError, match="note"):
            checkin.validate_payload(
                {"raw_text": "x", "pressures": [{"domain": "work"}]}
            )

    def test_pressure_bad_entry_rolls_back_whole_call(self):
        with pytest.raises(domain.DomainError):
            checkin.validate_payload(
                {
                    "raw_text": "x",
                    "pressures": [
                        {"domain": "work", "note": "ok"},
                        {"domain": "", "note": "bad"},
                    ],
                }
            )


class TestSummarize:
    def test_summary_omits_raw_text(self):
        row = {
            "id": "c1",
            "checkin_date": "2026-10-20",
            "raw_text": "私密原话",
            "fact": "f",
            "feeling": None,
            "worry": None,
            "speculation": None,
            "next_action": "a",
            "created_at": "2026-10-20T01:00:00+00:00",
            "pressure_domains": ["work", "family"],
        }
        summary = checkin.summarize(row)
        assert "raw_text" not in summary
        assert summary["id"] == "c1"
        assert summary["pressure_domains"] == ["work", "family"]

    def test_detail_keeps_raw_text(self):
        row = {"id": "c1", "raw_text": "私密原话", "fact": None, "feeling": None,
               "worry": None, "speculation": None, "next_action": None,
               "checkin_date": "2026-10-20", "created_at": "t"}
        detail = checkin.detail(row)
        assert detail["raw_text"] == "私密原话"

"""modules.weekly：周口径与数据包聚合、复盘入参校验（纯函数）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import domain
from app.modules import weekly


def _cst_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


class TestWeekStartOf:
    def test_default_is_current_week_monday(self):
        today = _cst_now().date()
        monday = today - timedelta(days=today.weekday())
        assert weekly.week_start_of(None) == monday.isoformat()

    def test_explicit_date_normalized(self):
        assert weekly.week_start_of("2026-10-21") == "2026-10-19"  # 周三 → 周一
        assert weekly.week_start_of("2026-10-19") == "2026-10-19"  # 周一即本身

    def test_sunday_belongs_to_same_week(self):
        assert weekly.week_start_of("2026-10-25") == "2026-10-19"  # 周日

    def test_bad_date_rejected(self):
        with pytest.raises(domain.DomainError, match="日期"):
            weekly.week_start_of("2026/10/19")


class TestBuildWeekData:
    def _checkins(self):
        return [
            {
                "id": "c2",
                "checkin_date": "2026-10-20",
                "fact": "方案被打回",
                "feeling": "烦躁",
                "worry": "怕评价差",
                "speculation": None,
                "next_action": "约老板",
                "created_at": "t2",
            },
            {
                "id": "c1",
                "checkin_date": "2026-10-19",
                "fact": None,
                "feeling": "累",
                "worry": None,
                "speculation": None,
                "next_action": None,
                "created_at": "t1",
            },
        ]

    def _pressures(self):
        return [
            {"domain": "work", "note": "返工", "occurred_at": "2026-10-20T01:00:00+00:00"},
            {"domain": "work", "note": "加班", "occurred_at": "2026-10-19T01:00:00+00:00"},
            {"domain": "family", "note": "吵架", "occurred_at": "2026-10-20T02:00:00+00:00"},
        ]

    def test_package_aggregates(self):
        data = weekly.build_week_data(
            "2026-10-19",
            self._checkins(),
            self._pressures(),
            [{"description": "焦虑→消费", "evidence_count": 2}],
        )
        assert data["week_start"] == "2026-10-19"
        assert [c["id"] for c in data["checkins"]] == ["c2", "c1"]  # 日期倒序
        assert data["pressure_distribution"] == [
            {"domain": "work", "count": 2},
            {"domain": "family", "count": 1},
        ]
        assert data["daily_counts"] == {"2026-10-19": 1, "2026-10-20": 2}
        assert data["active_patterns"] == [
            {"description": "焦虑→消费", "evidence_count": 2}
        ]

    def test_no_raw_text_in_checkins(self):
        rows = [dict(r, raw_text="私密原话") for r in self._checkins()]
        data = weekly.build_week_data("2026-10-19", rows, [], [])
        assert all("raw_text" not in c for c in data["checkins"])

    def test_out_of_week_checkins_filtered(self):
        rows = self._checkins() + [
            {"id": "c9", "checkin_date": "2026-10-10", "created_at": "t9",
             "fact": None, "feeling": None, "worry": None, "speculation": None,
             "next_action": None}
        ]
        data = weekly.build_week_data("2026-10-19", rows, self._pressures(), [])
        assert [c["id"] for c in data["checkins"]] == ["c2", "c1"]

    def test_empty_week(self):
        data = weekly.build_week_data("2026-10-19", [], [], [])
        assert data["checkins"] == []
        assert data["pressure_distribution"] == []
        assert data["daily_counts"] == {}
        assert data["active_patterns"] == []


class TestValidateReviewPayload:
    def _valid(self):
        return {
            "week_start": "2026-10-19",
            "main_sources": "工作返工",
            "recurring": "自我怀疑反复出现",
            "easing_vs_worsening": "散步缓解；熬夜恶化",
            "improved": "主动约了老板",
            "focus_next": "睡够7点",
            "narrative": "本周整体偏紧但可控。",
        }

    def test_valid_payload(self):
        data = weekly.validate_review_payload(self._valid())
        assert data["week_start"] == "2026-10-19"
        assert set(data) == {
            "week_start",
            "main_sources",
            "recurring",
            "easing_vs_worsening",
            "improved",
            "focus_next",
            "narrative",
        }

    def test_missing_field_rejected(self):
        for field in ("main_sources", "recurring", "easing_vs_worsening", "improved",
                      "focus_next", "narrative"):
            payload = self._valid()
            payload[field] = "  "
            with pytest.raises(domain.DomainError, match=field):
                weekly.validate_review_payload(payload)

    def test_bad_week_rejected(self):
        payload = self._valid()
        payload["week_start"] = "tomorrow"
        with pytest.raises(domain.DomainError):
            weekly.validate_review_payload(payload)

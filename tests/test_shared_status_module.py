"""modules.shared_status：抽象状态白名单构建与三档推导（纯函数）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import domain
from app.modules import shared_status


class TestBuildSharedStatus:
    def test_fields_are_exact_whitelist(self):
        status = shared_status.build_shared_status(
            days=7,
            distribution=[{"domain": "work", "count": 3}],
            intensities=[4, 2],
            checkin_dates=["2026-10-19", "2026-10-20"],
        )
        assert set(status) == set(domain.SHARED_STATUS_FIELDS)
        assert status["period"] == {"days": 7}
        assert status["overall_stress_level"] in ("low", "mid", "high")
        assert status["top_domains"] == [{"domain": "work", "count": 3}]
        assert status["checkin_streak"] == 2
        assert isinstance(status["note"], str)

    def test_high_intensity_ratio_drives_high(self):
        status = shared_status.build_shared_status(
            days=7, distribution=[{"domain": "work", "count": 2}],
            intensities=[5, 5], checkin_dates=[],
        )
        assert status["overall_stress_level"] == "high"
        assert "高" in status["note"]

    def test_low_window(self):
        status = shared_status.build_shared_status(
            days=7,
            distribution=[{"domain": "money", "count": 1}],
            intensities=[2],
            checkin_dates=["2026-10-20"],
        )
        assert status["overall_stress_level"] == "low"

    def test_empty_window_is_neutral(self):
        status = shared_status.build_shared_status(
            days=7, distribution=[], intensities=[], checkin_dates=[]
        )
        assert status["overall_stress_level"] == "low"
        assert status["top_domains"] == []
        assert status["checkin_streak"] == 0

    def test_no_free_text_from_data(self):
        """返回中任何字段都不含库内原文：领域是枚举，note 是模板句。"""
        status = shared_status.build_shared_status(
            days=7,
            distribution=[{"domain": "work", "count": 2}, {"domain": "family", "count": 1}],
            intensities=[3, 3],
            checkin_dates=["2026-10-20"],
        )
        serialized = str(status)
        assert "私密" not in serialized
        for forbidden in ("raw", "note_value", "description"):
            assert forbidden not in status

    def test_streak_counts_consecutive_days_ending_today(self):
        today = datetime.now(timezone(timedelta(hours=8))).date()
        dates = [
            (today - timedelta(days=offset)).isoformat() for offset in (0, 1, 2, 5)
        ]
        status = shared_status.build_shared_status(
            days=7, distribution=[], intensities=[], checkin_dates=dates
        )
        assert status["checkin_streak"] == 3

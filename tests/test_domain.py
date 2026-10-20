"""domain：领域常量与校验纯函数（零 IO）。"""

from __future__ import annotations

import pytest

from app import domain


class TestNormalizeDomain:
    def test_preset_domains_case_insensitive(self):
        for raw in ["work", "WORK", "Family", " family "]:
            normalized = domain.normalize_domain(raw)
            assert normalized == raw.strip().lower()
            assert normalized in domain.PRESSURE_DOMAINS

    def test_preset_labels_cover_six_domains(self):
        assert len(domain.PRESSURE_DOMAINS) == 6
        assert set(domain.PRESSURE_DOMAINS) == {
            "work",
            "family",
            "relations",
            "money",
            "energy",
            "self",
        }
        assert all(domain.PRESSURE_DOMAIN_LABELS[d] for d in domain.PRESSURE_DOMAINS)

    def test_unknown_domain_falls_back_with_original_text(self):
        normalized = domain.normalize_domain("Health")
        assert normalized == "health"
        assert not domain.is_preset_domain(normalized)

    def test_empty_domain_rejected(self):
        for bad in ["", "   ", None]:
            with pytest.raises(domain.DomainError):
                domain.normalize_domain(bad)


class TestValidateDigestSlot:
    def test_accepts_string_and_none(self):
        assert domain.validate_digest_slot("fact", "方案被打回") == "方案被打回"
        assert domain.validate_digest_slot("fact", None) is None

    def test_rejects_non_string(self):
        with pytest.raises(domain.DomainError, match="fact"):
            domain.validate_digest_slot("fact", 123)

    def test_rejects_over_length(self):
        with pytest.raises(domain.DomainError, match="fact"):
            domain.validate_digest_slot("fact", "x" * 2001)


class TestValidateIntensity:
    @pytest.mark.parametrize("value", [1, 2, 3, 4, 5])
    def test_accepts_bounded_int(self, value):
        assert domain.validate_intensity(value) == value

    def test_accepts_none(self):
        assert domain.validate_intensity(None) is None

    @pytest.mark.parametrize("value", [0, 6, -1, 2.5, "3"])
    def test_rejects_out_of_bounds_or_non_int(self, value):
        with pytest.raises(domain.DomainError):
            domain.validate_intensity(value)


class TestPatternStatus:
    def test_statuses(self):
        assert domain.PATTERN_STATUSES == {"active", "watched", "resolved"}

    def test_validate_status(self):
        assert domain.validate_status("active") == "active"
        with pytest.raises(domain.DomainError):
            domain.validate_status("deleted")


class TestStressThresholds:
    def test_thresholds_are_concentrated(self):
        assert set(domain.STRESS_THRESHOLDS) == {"count_low", "count_high", "high_intensity_ratio"}
        assert 0 < domain.STRESS_THRESHOLDS["count_low"] < domain.STRESS_THRESHOLDS["count_high"]
        assert 0 < domain.STRESS_THRESHOLDS["high_intensity_ratio"] <= 1

    def test_derive_stress_level(self):
        t = domain.STRESS_THRESHOLDS
        # 空窗 / 少量低强度 → low
        assert domain.derive_stress_level(0, 0.0) == "low"
        assert domain.derive_stress_level(t["count_low"], 0.0) == "low"
        # 高强度占比过半 → high（即使条数少）
        assert domain.derive_stress_level(2, 1.0) == "high"
        # 条数超上界 → high
        assert domain.derive_stress_level(t["count_high"] + 1, 0.0) == "high"
        # 其间 → mid
        mid_count = (t["count_low"] + t["count_high"]) // 2
        assert domain.derive_stress_level(mid_count, 0.2) == "mid"

    def test_shared_status_fields_whitelist(self):
        assert set(domain.SHARED_STATUS_FIELDS) == {
            "period",
            "overall_stress_level",
            "top_domains",
            "checkin_streak",
            "note",
        }

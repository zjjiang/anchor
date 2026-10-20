"""store.weekly：复盘落库、同周唯一（replaced 版本替换）、查询口径。"""

from __future__ import annotations

from app.modules import weekly
from app.store import weekly as weekly_store


def _payload(week="2026-10-19", focus="睡够"):
    return weekly.validate_review_payload(
        {
            "week_start": week,
            "main_sources": "工作返工",
            "recurring": "自我怀疑",
            "easing_vs_worsening": "散步缓解；熬夜恶化",
            "improved": "约了老板",
            "focus_next": focus,
            "narrative": "本周复盘正文。",
        }
    )


class TestSave:
    def test_first_save(self, fresh_db):
        wid = weekly_store.save(_payload())
        assert wid == "w1"

    def test_resave_replaces_keeps_old_row(self, fresh_db):
        weekly_store.save(_payload(focus="v1"))
        wid2 = weekly_store.save(_payload(focus="v2"))
        assert wid2 == "w2"
        with fresh_db.get_conn() as conn:
            rows = conn.execute(
                "SELECT focus_next, replaced_at FROM weekly_reviews ORDER BY id"
            ).fetchall()
        assert len(rows) == 2
        assert rows[0]["focus_next"] == "v1"
        assert rows[0]["replaced_at"] is not None  # 旧版保留可回溯，不物理删除
        assert rows[1]["replaced_at"] is None


class TestQuery:
    def test_get_by_week_returns_effective_only(self, fresh_db):
        weekly_store.save(_payload(focus="v1"))
        weekly_store.save(_payload(focus="v2"))
        review = weekly_store.get_by_week("2026-10-19")
        assert review["focus_next"] == "v2"
        assert "replaced_at" not in review

    def test_get_by_week_empty(self, fresh_db):
        assert weekly_store.get_by_week("2026-01-05") is None

    def test_list_reviews_newest_first(self, fresh_db):
        weekly_store.save(_payload("2026-10-05"))
        weekly_store.save(_payload("2026-10-12"))
        rows = weekly_store.list_reviews()
        assert [r["week_start"] for r in rows] == ["2026-10-12", "2026-10-05"]
        assert all("replaced_at" not in r for r in rows)
        assert rows[0]["narrative"] == "本周复盘正文。"

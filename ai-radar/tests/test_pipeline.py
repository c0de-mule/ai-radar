"""End-to-end pipeline tests with all external calls mocked."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pipeline.config import Settings
from pipeline.models import (
    Category,
    DailyBriefing,
    Source,
)


class TestPipelineIntegration:
    """Integration tests for the full pipeline flow."""

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self, tmp_path, sample_raw_items):
        """Test the complete pipeline from fetch to output."""
        from pipeline.output.json_writer import write_briefing
        from pipeline.processing.dedup import deduplicate
        from pipeline.processing.relevance import score_relevance

        # 1. Deduplicate
        deduped = deduplicate(sample_raw_items)
        assert len(deduped) == len(sample_raw_items)  # No dups in sample

        # 2. Score relevance
        for item in deduped:
            score_relevance(item)
        deduped.sort(key=lambda x: x.relevance_score, reverse=True)
        assert deduped[0].relevance_score > 0

        # 3. Mock AI summarization (just use extractive fallback)
        from pipeline.processing.ai_summarizer import (
            _apply_ai_result,
            _extractive_fallback,
        )

        briefing_items = []
        for item in deduped:
            fallback = _extractive_fallback(item)
            bi = _apply_ai_result(item, fallback)
            briefing_items.append(bi)

        assert len(briefing_items) == len(deduped)

        # 4. Assemble briefing
        from pipeline.models import BriefingStats

        stats = BriefingStats(
            total_items=len(briefing_items),
            sources={
                s.value: sum(1 for i in briefing_items if i.source == s)
                for s in Source
            },
            categories={
                c.value: sum(1 for i in briefing_items if i.category == c)
                for c in Category
            },
        )

        briefing = DailyBriefing(
            date="2025-02-10",
            generated_at=datetime.now(tz=UTC),
            headline=briefing_items[0].title,
            stats=stats,
            items=briefing_items,
        )

        # 5. Write output
        data_dir = tmp_path / "data"
        output = write_briefing(briefing, data_dir)
        assert output.exists()
        assert (data_dir / "latest.json").exists()
        assert (data_dir / "index.json").exists()

    def test_settings_defaults(self):
        """Settings should have sensible defaults when env vars are empty."""
        settings = Settings()
        assert not settings.has_gemini
        assert not settings.has_claude
        assert not settings.has_email
        assert settings.email_recipients == []

    def test_settings_with_keys(self, monkeypatch):
        """Settings should detect available services from env vars."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-2")
        monkeypatch.setenv("EMAIL_RECIPIENTS", "a@b.com, c@d.com")
        settings = Settings()
        assert settings.has_gemini
        assert settings.has_claude
        assert settings.email_recipients == ["a@b.com", "c@d.com"]

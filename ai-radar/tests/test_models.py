"""Tests for data models."""

import pytest
from pydantic import ValidationError

from pipeline.models import (
    BriefingItem,
    Category,
    DailyBriefing,
    RawItem,
    Source,
)


class TestRawItem:
    """Tests for the RawItem model."""

    def test_create_minimal(self):
        item = RawItem(
            id="test-1", title="Test", url="https://example.com",
            source=Source.HACKERNEWS,
        )
        assert item.id == "test-1"
        assert item.content == ""
        assert item.relevance_score == 0.0
        assert item.score is None

    def test_create_full(self, sample_raw_items):
        item = sample_raw_items[0]
        assert item.source == Source.HACKERNEWS
        assert item.score == 850
        assert "OpenAI" in item.title

    def test_relevance_score_mutable(self):
        item = RawItem(id="t", title="t", url="http://x.com", source=Source.RSS)
        item.relevance_score = 7.5
        assert item.relevance_score == 7.5


class TestBriefingItem:
    """Tests for the BriefingItem model."""

    def test_create(self, sample_briefing_items):
        item = sample_briefing_items[0]
        assert item.category == Category.MODELS
        assert item.relevance_score == 9.2
        assert len(item.tags) == 3

    def test_relevance_score_bounds(self):
        with pytest.raises(ValidationError):
            BriefingItem(
                id="t", title="t", url="http://x.com", source=Source.RSS,
                category=Category.TOOLS, summary="s", relevance_score=11.0,
            )

    def test_relevance_score_negative(self):
        with pytest.raises(ValidationError):
            BriefingItem(
                id="t", title="t", url="http://x.com", source=Source.RSS,
                category=Category.TOOLS, summary="s", relevance_score=-1.0,
            )


class TestDailyBriefing:
    """Tests for the DailyBriefing model."""

    def test_create(self, sample_briefing):
        assert sample_briefing.date == "2025-02-10"
        assert len(sample_briefing.items) == 3
        assert sample_briefing.stats.total_items == 3

    def test_items_by_category(self, sample_briefing):
        grouped = sample_briefing.items_by_category()
        assert Category.MODELS in grouped
        assert Category.RESEARCH in grouped
        assert Category.TUTORIALS in grouped
        assert Category.TOOLS not in grouped  # No tools in sample
        assert len(grouped[Category.MODELS]) == 1

    def test_serialization_roundtrip(self, sample_briefing):
        json_str = sample_briefing.model_dump_json()
        restored = DailyBriefing.model_validate_json(json_str)
        assert restored.date == sample_briefing.date
        assert len(restored.items) == len(sample_briefing.items)
        assert restored.headline == sample_briefing.headline


class TestEnums:
    """Tests for Source and Category enums."""

    def test_source_values(self):
        assert Source.HACKERNEWS.value == "hackernews"
        assert Source.ARXIV.value == "arxiv"
        assert Source.RSS.value == "rss"

    def test_category_values(self):
        assert Category.MODELS.value == "models"
        assert Category.TOOLS.value == "tools"
        assert Category.RESEARCH.value == "research"
        assert Category.INDUSTRY.value == "industry"
        assert Category.TUTORIALS.value == "tutorials"

    def test_all_categories_have_meta(self):
        from pipeline.models import CATEGORY_META
        for cat in Category:
            assert cat in CATEGORY_META
            assert "label" in CATEGORY_META[cat]
            assert "emoji" in CATEGORY_META[cat]

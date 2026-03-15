"""Tests for the processing pipeline — dedup, relevance, AI summarizer."""

from datetime import UTC, datetime

from pipeline.models import Category, RawItem, Source
from pipeline.processing.ai_summarizer import (
    _build_user_prompt,
    _extractive_fallback,
    _parse_category,
)
from pipeline.processing.dedup import (
    _normalize_url,
    _title_similarity,
    deduplicate,
)
from pipeline.processing.relevance import (
    _engagement_score,
    _keyword_density_score,
    _recency_score,
    _source_authority_score,
    score_relevance,
)


class TestDedup:
    """Tests for deduplication logic."""

    def test_exact_url_dedup(self):
        items = [
            RawItem(
                id="a", title="Story A", url="https://example.com/story",
                source=Source.HACKERNEWS, score=100,
            ),
            RawItem(
                id="b", title="Story B", url="https://example.com/story",
                source=Source.RSS, score=50,
            ),
        ]
        result = deduplicate(items)
        assert len(result) == 1
        assert result[0].score == 100  # Higher score wins

    def test_url_normalization(self):
        assert _normalize_url("https://www.example.com/path/") == "example.com/path"
        assert _normalize_url("http://example.com/path") == "example.com/path"
        assert _normalize_url("https://Example.COM/Path") == "example.com/path"

    def test_title_similarity_identical(self):
        assert _title_similarity("Hello World Test", "Hello World Test") == 1.0

    def test_title_similarity_different(self):
        sim = _title_similarity("OpenAI releases GPT-5", "Google announces new phone")
        assert sim < 0.3

    def test_title_similarity_similar(self):
        sim = _title_similarity(
            "OpenAI releases GPT-5 with improved reasoning",
            "OpenAI announces GPT-5 with better reasoning capabilities",
        )
        assert sim > 0.4

    def test_no_duplicates(self, sample_raw_items):
        result = deduplicate(sample_raw_items)
        assert len(result) == len(sample_raw_items)  # All unique

    def test_empty_input(self):
        assert deduplicate([]) == []

    def test_title_dedup_keeps_better(self):
        items = [
            RawItem(
                id="a", title="AI model achieves breakthrough results",
                url="https://a.com", source=Source.RSS, score=10,
            ),
            RawItem(
                id="b", title="AI model achieves breakthrough results today",
                url="https://b.com", source=Source.HACKERNEWS, score=500,
            ),
        ]
        result = deduplicate(items)
        assert len(result) == 1
        assert result[0].score == 500


class TestRelevance:
    """Tests for relevance scoring."""

    def test_score_range(self, sample_raw_items):
        for item in sample_raw_items:
            scored = score_relevance(item)
            assert 0.0 <= scored.relevance_score <= 10.0

    def test_keyword_density(self):
        item = RawItem(
            id="t", title="AI LLM transformer deep learning",
            url="http://x.com", source=Source.RSS,
        )
        score = _keyword_density_score(item)
        assert score > 0

    def test_keyword_density_no_match(self):
        item = RawItem(id="t", title="How to bake a cake", url="http://x.com", source=Source.RSS)
        score = _keyword_density_score(item)
        assert score == 0.0

    def test_source_authority(self):
        arxiv_item = RawItem(id="t", title="t", url="http://x.com", source=Source.ARXIV)
        hn_item = RawItem(id="t", title="t", url="http://x.com", source=Source.HACKERNEWS)
        assert _source_authority_score(arxiv_item) > _source_authority_score(hn_item)

    def test_recency_recent(self):
        item = RawItem(
            id="t", title="t", url="http://x.com", source=Source.RSS,
            published_at=datetime.now(tz=UTC),
        )
        assert _recency_score(item) == 2.0

    def test_recency_none(self):
        item = RawItem(id="t", title="t", url="http://x.com", source=Source.RSS)
        assert _recency_score(item) == 1.0  # Unknown = middle

    def test_engagement_high(self):
        item = RawItem(
            id="t", title="t", url="http://x.com",
            source=Source.HACKERNEWS, score=1000,
        )
        assert _engagement_score(item) == 3.0

    def test_engagement_none(self):
        item = RawItem(id="t", title="t", url="http://x.com", source=Source.RSS)
        assert _engagement_score(item) == 0.0

    def test_high_relevance_item(self):
        """An item with lots of AI keywords, recent, high score should score high."""
        item = RawItem(
            id="t",
            title="OpenAI releases new LLM with transformer architecture",
            url="http://x.com",
            source=Source.HACKERNEWS,
            content="GPT model with deep learning and AI capabilities",
            score=800,
            published_at=datetime.now(tz=UTC),
        )
        scored = score_relevance(item)
        assert scored.relevance_score >= 7.0


class TestAISummarizer:
    """Tests for AI summarizer utilities (no API calls)."""

    def test_build_user_prompt(self, sample_raw_items):
        prompt = _build_user_prompt(sample_raw_items[:2])
        assert "[1]" in prompt
        assert "[2]" in prompt
        assert "OpenAI" in prompt

    def test_extractive_fallback(self):
        item = RawItem(
            id="t",
            title="A Great Title",
            url="http://x.com",
            source=Source.RSS,
            content="This is the first sentence. This is the second sentence. This is the third.",
        )
        result = _extractive_fallback(item)
        assert "summary" in result
        assert "category" in result
        assert "tags" in result
        assert "first sentence" in result["summary"]

    def test_extractive_fallback_no_content(self):
        item = RawItem(id="t", title="Just a Title", url="http://x.com", source=Source.RSS)
        result = _extractive_fallback(item)
        assert result["summary"].rstrip(".") == "Just a Title"

    def test_parse_category_valid(self):
        assert _parse_category("models") == Category.MODELS
        assert _parse_category("TOOLS") == Category.TOOLS
        assert _parse_category("  research  ") == Category.RESEARCH

    def test_parse_category_invalid(self):
        assert _parse_category("invalid") == Category.INDUSTRY  # Default fallback

    def test_extractive_category_detection(self):
        """Extractive fallback should guess category from keywords."""
        model_item = RawItem(
            id="t", title="New model benchmark results",
            url="http://x.com", source=Source.RSS,
            content="The model achieved state-of-the-art benchmark scores with fine-tuning.",
        )
        result = _extractive_fallback(model_item)
        assert result["category"] == "models"

        tutorial_item = RawItem(
            id="t", title="How to build an AI tutorial",
            url="http://x.com", source=Source.RSS,
            content="This guide walks you through building your first AI tutorial.",
        )
        result = _extractive_fallback(tutorial_item)
        assert result["category"] == "tutorials"

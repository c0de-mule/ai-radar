"""Shared test fixtures for AI Radar tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pipeline.models import (
    BriefingItem,
    BriefingStats,
    Category,
    DailyBriefing,
    RawItem,
    Source,
)


@pytest.fixture
def sample_raw_items() -> list[RawItem]:
    """A set of sample raw items from different sources."""
    return [
        RawItem(
            id="hn-12345",
            title="OpenAI releases GPT-5 with improved reasoning",
            url="https://openai.com/blog/gpt5",
            source=Source.HACKERNEWS,
            source_detail="Hacker News (850 pts)",
            content="OpenAI has released GPT-5, their latest model.",
            published_at=datetime(2025, 2, 10, 8, 0, tzinfo=UTC),
            score=850,
        ),
        RawItem(
            id="arxiv-2502.12345",
            title="A Novel Approach to Transformer Attention Mechanisms",
            url="https://arxiv.org/abs/2502.12345",
            source=Source.ARXIV,
            source_detail="arXiv (Smith, Jones)",
            content="We propose a new attention mechanism that reduces computational complexity.",
            authors=["Smith", "Jones"],
            published_at=datetime(2025, 2, 10, 6, 0, tzinfo=UTC),
        ),
        RawItem(
            id="rss-abcdef01",
            title="Getting Started with LangChain v2",
            url="https://blog.langchain.dev/getting-started-v2",
            source=Source.RSS,
            source_detail="LangChain Blog",
            content="A comprehensive guide to building AI applications with LangChain v2.",
            published_at=datetime(2025, 2, 9, 14, 0, tzinfo=UTC),
        ),
        RawItem(
            id="hn-12346",
            title="Google announces Gemini 2.5 Flash",
            url="https://blog.google/gemini-flash",
            source=Source.HACKERNEWS,
            source_detail="Hacker News (420 pts)",
            content="",
            published_at=datetime(2025, 2, 10, 10, 0, tzinfo=UTC),
            score=420,
        ),
        RawItem(
            id="rss-abcdef02",
            title="Anthropic raises $5B Series D funding",
            url="https://anthropic.com/news/series-d",
            source=Source.RSS,
            source_detail="Anthropic Blog",
            content="Anthropic has raised $5 billion in a new funding round.",
            published_at=datetime(2025, 2, 10, 12, 0, tzinfo=UTC),
        ),
    ]


@pytest.fixture
def sample_briefing_items() -> list[BriefingItem]:
    """Processed briefing items for output tests."""
    return [
        BriefingItem(
            id="hn-12345",
            title="OpenAI releases GPT-5 with improved reasoning",
            url="https://openai.com/blog/gpt5",
            source=Source.HACKERNEWS,
            source_detail="Hacker News (850 pts)",
            category=Category.MODELS,
            summary=(
                "OpenAI released GPT-5, featuring improved reasoning"
                " and 2x context window. Benchmarks show 15% improvement on MMLU."
            ),
            relevance_score=9.2,
            tags=["openai", "gpt-5", "llm"],
            published_at=datetime(2025, 2, 10, 8, 0, tzinfo=UTC),
        ),
        BriefingItem(
            id="arxiv-2502.12345",
            title="A Novel Approach to Transformer Attention Mechanisms",
            url="https://arxiv.org/abs/2502.12345",
            source=Source.ARXIV,
            source_detail="arXiv (Smith, Jones)",
            category=Category.RESEARCH,
            summary="Proposes a linear-time attention mechanism that achieves comparable accuracy.",
            relevance_score=7.5,
            tags=["attention", "transformer", "efficiency"],
        ),
        BriefingItem(
            id="rss-abcdef01",
            title="Getting Started with LangChain v2",
            url="https://blog.langchain.dev/getting-started-v2",
            source=Source.RSS,
            source_detail="LangChain Blog",
            category=Category.TUTORIALS,
            summary="Comprehensive tutorial covering LangChain v2's new features.",
            relevance_score=5.8,
            tags=["langchain", "tutorial", "rag"],
        ),
    ]


@pytest.fixture
def sample_briefing(sample_briefing_items) -> DailyBriefing:
    """A complete daily briefing for integration tests."""
    return DailyBriefing(
        date="2025-02-10",
        generated_at=datetime(2025, 2, 10, 14, 15, 0, tzinfo=UTC),
        headline="OpenAI releases GPT-5 with improved reasoning",
        stats=BriefingStats(
            total_items=3,
            sources={"hackernews": 1, "arxiv": 1, "rss": 1},
            categories={"models": 1, "research": 1, "tutorials": 1},
        ),
        items=sample_briefing_items,
    )


# --- Mock HTTP responses ---

MOCK_HN_TOP_STORIES = [12345, 12346, 12347]

MOCK_HN_STORY = {
    "id": 12345,
    "type": "story",
    "title": "OpenAI releases GPT-5 with improved reasoning",
    "url": "https://openai.com/blog/gpt5",
    "score": 850,
    "time": 1707552000,
    "descendants": 342,
}

MOCK_HN_NON_AI_STORY = {
    "id": 12347,
    "type": "story",
    "title": "How to build a wooden desk from scratch",
    "url": "https://example.com/woodworking",
    "score": 200,
    "time": 1707552000,
}

MOCK_ARXIV_RESPONSE = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2502.12345</id>
    <title>A Novel Approach to Transformer Attention</title>
    <summary>We propose a new attention mechanism
    that reduces complexity from quadratic to linear.
    </summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <published>2025-02-10T06:00:00Z</published>
    <link href="http://arxiv.org/abs/2502.12345"/>
  </entry>
</feed>"""

MOCK_RSS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>OpenAI Blog</title>
    <item>
      <title>Introducing GPT-5</title>
      <link>https://openai.com/blog/gpt5</link>
      <description>We are excited to announce GPT-5.</description>
      <pubDate>Mon, 10 Feb 2025 08:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""

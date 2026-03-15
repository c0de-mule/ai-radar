"""Tests for source fetchers with mocked HTTP responses."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from pipeline.sources.arxiv import _build_query, fetch_arxiv
from pipeline.sources.hackernews import _matches_ai_keywords, fetch_hackernews
from pipeline.sources.rss import _clean_html, _is_recent, fetch_rss
from tests.conftest import (
    MOCK_ARXIV_RESPONSE,
    MOCK_HN_NON_AI_STORY,
    MOCK_HN_STORY,
    MOCK_HN_TOP_STORIES,
    MOCK_RSS_RESPONSE,
)


class TestHackerNews:
    """Tests for the Hacker News fetcher."""

    def test_matches_ai_keywords_positive(self):
        assert _matches_ai_keywords("OpenAI releases new LLM model")
        assert _matches_ai_keywords("Deep learning breakthrough")
        assert _matches_ai_keywords("New AI agent framework")

    def test_matches_ai_keywords_negative(self):
        assert not _matches_ai_keywords("How to build a wooden desk")
        assert not _matches_ai_keywords("Best restaurants in NYC")

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_hackernews(self):
        respx.get("https://hacker-news.firebaseio.com/v0/topstories.json").mock(
            return_value=httpx.Response(200, json=MOCK_HN_TOP_STORIES)
        )
        respx.get("https://hacker-news.firebaseio.com/v0/item/12345.json").mock(
            return_value=httpx.Response(200, json=MOCK_HN_STORY)
        )
        respx.get("https://hacker-news.firebaseio.com/v0/item/12346.json").mock(
            return_value=httpx.Response(200, json={
                "id": 12346, "type": "story",
                "title": "Google AI breakthrough in reasoning",
                "url": "https://blog.google/ai", "score": 300, "time": 1707552000,
            })
        )
        respx.get("https://hacker-news.firebaseio.com/v0/item/12347.json").mock(
            return_value=httpx.Response(200, json=MOCK_HN_NON_AI_STORY)
        )

        items = await fetch_hackernews()
        # Should include AI stories, exclude woodworking
        assert len(items) >= 1
        assert all("hn-" in item.id for item in items)
        titles = [item.title for item in items]
        assert "How to build a wooden desk from scratch" not in titles

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_hackernews_api_error(self):
        respx.get("https://hacker-news.firebaseio.com/v0/topstories.json").mock(
            return_value=httpx.Response(500)
        )
        items = await fetch_hackernews()
        assert items == []


class TestArxiv:
    """Tests for the arXiv fetcher."""

    def test_build_query(self):
        q = _build_query(["cs.AI", "cs.LG"])
        assert "cat:cs.AI" in q
        assert "cat:cs.LG" in q
        assert " OR " in q

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_arxiv(self):
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=MOCK_ARXIV_RESPONSE)
        )
        items = await fetch_arxiv()
        assert len(items) == 1
        assert items[0].source.value == "arxiv"
        assert "Transformer" in items[0].title
        assert len(items[0].authors) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_arxiv_api_error(self):
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(503)
        )
        items = await fetch_arxiv()
        assert items == []


class TestRSS:
    """Tests for the RSS fetcher."""

    def test_is_recent_true(self):
        recent = datetime.now(tz=UTC) - timedelta(hours=1)
        assert _is_recent(recent, 48)

    def test_is_recent_false(self):
        old = datetime.now(tz=UTC) - timedelta(hours=100)
        assert not _is_recent(old, 48)

    def test_is_recent_none(self):
        assert _is_recent(None, 48)  # Unknown age = include

    def test_clean_html(self):
        assert _clean_html("<p>Hello <b>world</b></p>") == "Hello world"
        assert _clean_html("") == ""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_rss(self):
        # Build RSS with a recent pubDate so _is_recent passes
        now = datetime.now(tz=UTC)
        pub_date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
        recent_rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>OpenAI Blog</title>
    <item>
      <title>Introducing GPT-5 AI model</title>
      <link>https://openai.com/blog/gpt5</link>
      <description>We are excited to announce our latest AI model GPT-5.</description>
      <pubDate>{pub_date}</pubDate>
    </item>
  </channel>
</rss>"""
        # Mock OpenAI feed with valid data, all others return 404
        respx.get("https://openai.com/blog/rss.xml").mock(
            return_value=httpx.Response(200, text=recent_rss)
        )
        respx.get(url__regex=r".*").mock(return_value=httpx.Response(404))
        items = await fetch_rss()
        # Should get at least the OpenAI blog entry (GPT-5 + AI matches keywords)
        assert len(items) >= 1
        assert items[0].source.value == "rss"

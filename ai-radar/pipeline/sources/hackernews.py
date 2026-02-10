"""Hacker News source fetcher.

Uses the official HN Firebase API (no auth required) to fetch top stories,
then filters for AI-related content using keyword matching.

API docs: https://github.com/HackerNews/API
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from pipeline.config import AI_KEYWORDS, HN_MIN_SCORE, HN_TOP_STORIES_LIMIT
from pipeline.models import RawItem, Source

logger = logging.getLogger(__name__)

HN_BASE_URL = "https://hacker-news.firebaseio.com/v0"
_BATCH_SIZE = 20  # Fetch story details in batches to be polite


def _matches_ai_keywords(text: str) -> bool:
    """Check if text contains any AI-related keywords (case-insensitive)."""
    lower = text.lower()
    return any(kw in lower for kw in AI_KEYWORDS)


async def _fetch_story(client: httpx.AsyncClient, story_id: int) -> Optional[dict]:
    """Fetch a single story's details from the HN API.

    Returns None if the request fails or the item is not a story.
    """
    try:
        resp = await client.get(f"{HN_BASE_URL}/item/{story_id}.json")
        resp.raise_for_status()
        data = resp.json()
        if data and data.get("type") == "story" and not data.get("dead") and not data.get("deleted"):
            return data
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("Failed to fetch HN story %d: %s", story_id, exc)
    return None


async def fetch_hackernews() -> list[RawItem]:
    """Fetch AI-related top stories from Hacker News.

    Returns:
        List of RawItem objects for stories matching AI keywords
        with score >= HN_MIN_SCORE.
    """
    items: list[RawItem] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Get top story IDs
        try:
            resp = await client.get(f"{HN_BASE_URL}/topstories.json")
            resp.raise_for_status()
            story_ids: list[int] = resp.json()[:HN_TOP_STORIES_LIMIT]
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("Failed to fetch HN top stories: %s", exc)
            return items

        # 2. Fetch story details in batches
        for batch_start in range(0, len(story_ids), _BATCH_SIZE):
            batch = story_ids[batch_start : batch_start + _BATCH_SIZE]
            stories = []
            for sid in batch:
                story = await _fetch_story(client, sid)
                if story:
                    stories.append(story)

            # 3. Filter by AI keywords and minimum score
            for story in stories:
                title = story.get("title", "")
                url = story.get("url", f"https://news.ycombinator.com/item?id={story['id']}")
                score = story.get("score", 0)

                if score < HN_MIN_SCORE:
                    continue
                if not _matches_ai_keywords(title):
                    continue

                published = None
                if story.get("time"):
                    published = datetime.fromtimestamp(story["time"], tz=timezone.utc)

                items.append(
                    RawItem(
                        id=f"hn-{story['id']}",
                        title=title,
                        url=url,
                        source=Source.HACKERNEWS,
                        source_detail=f"Hacker News ({score} pts)",
                        content="",  # HN stories don't have body text
                        published_at=published,
                        score=score,
                    )
                )

    logger.info("Fetched %d AI-related stories from Hacker News", len(items))
    return items

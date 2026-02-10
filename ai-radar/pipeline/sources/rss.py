"""RSS/Atom feed source fetcher.

Parses a configurable list of AI blog feeds and extracts recent entries.
Uses feedparser for robust RSS/Atom handling.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import mktime

import feedparser
import httpx

from pipeline.config import AI_KEYWORDS, CONTENT_MAX_AGE_HOURS, RSS_FEEDS
from pipeline.models import RawItem, Source

logger = logging.getLogger(__name__)


def _matches_ai_keywords(text: str) -> bool:
    """Check if text contains any AI-related keywords."""
    lower = text.lower()
    return any(kw in lower for kw in AI_KEYWORDS)


def _parse_entry_date(entry: dict) -> datetime | None:
    """Extract published date from a feedparser entry."""
    for date_field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(date_field)
        if parsed:
            try:
                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            except (ValueError, OverflowError):
                continue
    return None


def _is_recent(published: datetime | None, max_age_hours: int) -> bool:
    """Check if an entry was published within the max age window."""
    if published is None:
        return True  # If we can't determine age, include it
    age = datetime.now(tz=timezone.utc) - published
    return age.total_seconds() < max_age_hours * 3600


def _clean_html(text: str) -> str:
    """Strip basic HTML tags from content. Not a full sanitizer."""
    import re

    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()[:2000]  # Cap content length


async def fetch_rss() -> list[RawItem]:
    """Fetch recent AI-related entries from configured RSS feeds.

    Returns:
        List of RawItem objects from entries published in the last
        CONTENT_MAX_AGE_HOURS hours.
    """
    items: list[RawItem] = []

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for feed_config in RSS_FEEDS:
            feed_name = feed_config["name"]
            feed_url = feed_config["url"]

            try:
                resp = await client.get(feed_url)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("Failed to fetch RSS feed '%s': %s", feed_name, exc)
                continue

            feed = feedparser.parse(resp.text)

            for entry in feed.entries:
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                content_blocks = entry.get("content", [])
                content = content_blocks[0].get("value", "") if content_blocks else summary
                published = _parse_entry_date(entry)

                if not title or not link:
                    continue
                if not _is_recent(published, CONTENT_MAX_AGE_HOURS):
                    continue

                # RSS feeds from AI blogs are inherently relevant,
                # but we still filter general-purpose feeds.
                full_text = f"{title} {summary}"
                if not _matches_ai_keywords(full_text):
                    continue

                items.append(
                    RawItem(
                        id=f"rss-{hash(link) & 0xFFFFFFFF:08x}",
                        title=title,
                        url=link,
                        source=Source.RSS,
                        source_detail=feed_name,
                        content=_clean_html(content),
                        published_at=published,
                    )
                )

            logger.debug("Parsed %d entries from '%s'", len(feed.entries), feed_name)

    logger.info("Fetched %d AI-related entries from RSS feeds", len(items))
    return items

"""arXiv source fetcher.

Queries the arXiv Atom API for recent papers in AI/ML categories.
Uses feedparser to handle the Atom XML response.

API docs: https://info.arxiv.org/help/api/user-manual.html
Rate limit: max 1 request every 3 seconds.
"""

from __future__ import annotations

import logging
from datetime import datetime

import feedparser
import httpx

from pipeline.config import ARXIV_CATEGORIES, ARXIV_MAX_RESULTS
from pipeline.models import RawItem, Source

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"


def _build_query(categories: list[str]) -> str:
    """Build an arXiv API search query for the given categories.

    Example output: 'cat:cs.AI OR cat:cs.LG OR cat:cs.CL'
    """
    return " OR ".join(f"cat:{cat}" for cat in categories)


def _parse_authors(entry: dict) -> list[str]:
    """Extract author names from a feedparser entry."""
    authors_raw = entry.get("authors", [])
    return [a.get("name", "") for a in authors_raw if a.get("name")]


def _parse_published(entry: dict) -> datetime | None:
    """Parse the published date from a feedparser entry."""
    published_str = entry.get("published", "")
    if not published_str:
        return None
    try:
        # arXiv format: 2025-02-10T14:30:00Z
        return datetime.fromisoformat(published_str.replace("Z", "+00:00"))
    except ValueError:
        return None


async def fetch_arxiv() -> list[RawItem]:
    """Fetch latest AI/ML papers from arXiv.

    Returns:
        List of RawItem objects for recent papers in configured categories.
    """
    items: list[RawItem] = []
    query = _build_query(ARXIV_CATEGORIES)

    params = {
        "search_query": query,
        "start": 0,
        "max_results": ARXIV_MAX_RESULTS,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(ARXIV_API_URL, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch arXiv papers: %s", exc)
            return items

    feed = feedparser.parse(resp.text)

    for entry in feed.entries:
        arxiv_id = entry.get("id", "").split("/abs/")[-1]
        title = entry.get("title", "").replace("\n", " ").strip()
        abstract = entry.get("summary", "").replace("\n", " ").strip()
        link = entry.get("link", entry.get("id", ""))
        authors = _parse_authors(entry)
        published = _parse_published(entry)

        if not title or not arxiv_id:
            continue

        items.append(
            RawItem(
                id=f"arxiv-{arxiv_id}",
                title=title,
                url=link,
                source=Source.ARXIV,
                source_detail=f"arXiv ({', '.join(authors[:2])}{'...' if len(authors) > 2 else ''})",
                content=abstract,
                authors=authors,
                published_at=published,
            )
        )

    logger.info("Fetched %d papers from arXiv", len(items))
    return items

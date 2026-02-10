"""Deduplication logic for raw items.

Two-stage dedup:
1. Exact URL match — keeps the item with higher engagement.
2. Title similarity — catches reposts/aggregation of the same story.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from pipeline.config import DEDUP_TITLE_SIMILARITY_THRESHOLD
from pipeline.models import RawItem

logger = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    """Normalize a URL for comparison (strip scheme, www, trailing slash)."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/")
    return f"{host}{path}".lower()


def _tokenize(text: str) -> set[str]:
    """Split text into lowercase word tokens for similarity comparison."""
    return {w.lower() for w in text.split() if len(w) > 2}


def _title_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity between two titles.

    Returns:
        Float between 0.0 (no overlap) and 1.0 (identical tokens).
    """
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _pick_better(existing: RawItem, challenger: RawItem) -> RawItem:
    """Choose the more authoritative/higher-engagement item."""
    # Prefer items with higher engagement scores
    existing_score = existing.score or 0
    challenger_score = challenger.score or 0
    if challenger_score > existing_score:
        return challenger
    return existing


def deduplicate(items: list[RawItem]) -> list[RawItem]:
    """Remove duplicate items by URL and title similarity.

    Args:
        items: List of raw items from all sources.

    Returns:
        Deduplicated list, preserving order of first occurrence.
    """
    # Stage 1: Exact URL dedup
    url_map: dict[str, RawItem] = {}
    for item in items:
        norm_url = _normalize_url(item.url)
        if norm_url in url_map:
            url_map[norm_url] = _pick_better(url_map[norm_url], item)
        else:
            url_map[norm_url] = item

    url_deduped = list(url_map.values())
    url_removed = len(items) - len(url_deduped)

    # Stage 2: Title similarity dedup
    kept: list[RawItem] = []
    for item in url_deduped:
        is_dup = False
        for existing in kept:
            sim = _title_similarity(item.title, existing.title)
            if sim >= DEDUP_TITLE_SIMILARITY_THRESHOLD:
                # Replace if the new item is better
                idx = kept.index(existing)
                kept[idx] = _pick_better(existing, item)
                is_dup = True
                break
        if not is_dup:
            kept.append(item)

    title_removed = len(url_deduped) - len(kept)
    total_removed = url_removed + title_removed

    if total_removed > 0:
        logger.info(
            "Dedup removed %d items (URL: %d, title: %d) — %d remaining",
            total_removed, url_removed, title_removed, len(kept),
        )

    return kept

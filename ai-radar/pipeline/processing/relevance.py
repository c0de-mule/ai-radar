"""Relevance scoring for raw items.

Assigns a 0-10 score based on keyword density, source authority,
recency, and engagement. Higher score = more likely to appear in
the daily briefing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pipeline.config import AI_KEYWORDS
from pipeline.models import RawItem, Source

logger = logging.getLogger(__name__)

# Source authority weights (higher = more trusted/authoritative)
_SOURCE_AUTHORITY: dict[Source, float] = {
    Source.ARXIV: 2.0,      # Peer-oriented research
    Source.RSS: 1.5,        # Curated AI blogs
    Source.HACKERNEWS: 1.0, # Community-driven, broader
}

# Max engagement score for normalization (HN points)
_MAX_ENGAGEMENT = 500


def _keyword_density_score(item: RawItem) -> float:
    """Score based on how many AI keywords appear in title + content.

    Returns:
        Float between 0.0 and 3.0.
    """
    text = f"{item.title} {item.content}".lower()
    matches = sum(1 for kw in AI_KEYWORDS if kw in text)
    # Diminishing returns: first few keywords matter most
    return min(3.0, matches * 0.3)


def _source_authority_score(item: RawItem) -> float:
    """Score based on source trustworthiness.

    Returns:
        Float between 0.0 and 2.0.
    """
    return _SOURCE_AUTHORITY.get(item.source, 1.0)


def _recency_score(item: RawItem) -> float:
    """Score based on how recent the item is.

    Items from the last 6 hours get max score; decays linearly to 48h.

    Returns:
        Float between 0.0 and 2.0.
    """
    if item.published_at is None:
        return 1.0  # Unknown age gets middle score

    now = datetime.now(tz=timezone.utc)
    age_hours = (now - item.published_at).total_seconds() / 3600

    if age_hours <= 6:
        return 2.0
    if age_hours <= 24:
        return 1.5
    if age_hours <= 48:
        return 1.0
    return 0.5


def _engagement_score(item: RawItem) -> float:
    """Score based on community engagement (HN points, etc.).

    Returns:
        Float between 0.0 and 3.0.
    """
    if item.score is None or item.score <= 0:
        return 0.0
    # Normalize: 500+ points = max score
    normalized = min(1.0, item.score / _MAX_ENGAGEMENT)
    return normalized * 3.0


def score_relevance(item: RawItem) -> RawItem:
    """Compute and assign a relevance score (0-10) to a raw item.

    Scoring formula:
        keyword_density (0-3) + source_authority (0-2) +
        recency (0-2) + engagement (0-3) = max 10.0

    Args:
        item: Raw item to score. Modified in place.

    Returns:
        The same item with relevance_score set.
    """
    score = (
        _keyword_density_score(item)
        + _source_authority_score(item)
        + _recency_score(item)
        + _engagement_score(item)
    )
    item.relevance_score = round(min(10.0, max(0.0, score)), 1)
    return item

"""AI Radar pipeline orchestrator.

Entry point for the daily briefing generation. Runs as:
    python -m pipeline.main

Stages:
    1. Fetch from all sources (HN, arXiv, RSS) concurrently
    2. Deduplicate across sources
    3. Score relevance
    4. Summarize top items with AI (Gemini → Claude → extractive)
    5. Assemble daily briefing
    6. Write JSON output files
    7. Send email digest
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from pipeline.config import (
    MAX_ITEMS_IN_BRIEFING,
    MAX_ITEMS_TO_SUMMARIZE,
    load_settings,
)
from pipeline.models import BriefingItem, BriefingStats, DailyBriefing, RawItem
from pipeline.output.email_digest import send_digest
from pipeline.output.json_writer import write_briefing
from pipeline.processing.ai_summarizer import summarize_batch
from pipeline.processing.dedup import deduplicate
from pipeline.processing.relevance import score_relevance
from pipeline.sources.arxiv import fetch_arxiv
from pipeline.sources.hackernews import fetch_hackernews
from pipeline.sources.rss import fetch_rss

# Project root / data directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def fetch_all_sources() -> list[RawItem]:
    """Fetch items from all sources concurrently.

    Returns:
        Combined list of RawItems from all sources.
    """
    logger.info("Fetching from all sources...")

    results = await asyncio.gather(
        fetch_hackernews(),
        fetch_arxiv(),
        fetch_rss(),
        return_exceptions=True,
    )

    all_items: list[RawItem] = []
    source_names = ["Hacker News", "arXiv", "RSS"]

    for name, result in zip(source_names, results, strict=True):
        if isinstance(result, Exception):
            logger.error("Failed to fetch from %s: %s", name, result)
        else:
            all_items.extend(result)
            logger.info("  %s: %d items", name, len(result))

    logger.info("Total raw items: %d", len(all_items))
    return all_items


def _compute_stats(items: list[BriefingItem]) -> BriefingStats:
    """Compute aggregate stats for the briefing."""
    sources: dict[str, int] = {}
    categories: dict[str, int] = {}
    for item in items:
        sources[item.source.value] = sources.get(item.source.value, 0) + 1
        categories[item.category.value] = categories.get(item.category.value, 0) + 1
    return BriefingStats(
        total_items=len(items),
        sources=sources,
        categories=categories,
    )


async def run_pipeline() -> DailyBriefing:
    """Execute the full pipeline and return the daily briefing.

    Returns:
        The assembled DailyBriefing, also written to disk.
    """
    settings = load_settings()
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    logger.info("=" * 60)
    logger.info("AI Radar — generating briefing for %s", today)
    logger.info("=" * 60)

    # 1. Fetch from all sources
    raw_items = await fetch_all_sources()

    if not raw_items:
        logger.warning("No items fetched from any source. Aborting.")
        sys.exit(1)

    # 2. Deduplicate
    unique_items = deduplicate(raw_items)
    logger.info("After dedup: %d items", len(unique_items))

    # 3. Score relevance
    for item in unique_items:
        score_relevance(item)
    unique_items.sort(key=lambda x: x.relevance_score, reverse=True)
    logger.info(
        "Top relevance score: %.1f (%s)",
        unique_items[0].relevance_score,
        unique_items[0].title[:60],
    )

    # 4. Take top N and summarize with AI
    top_items = unique_items[:MAX_ITEMS_TO_SUMMARIZE]
    logger.info("Sending top %d items to AI for summarization...", len(top_items))
    briefing_items = await summarize_batch(top_items, settings)

    # 5. Cap at briefing limit
    briefing_items = briefing_items[:MAX_ITEMS_IN_BRIEFING]

    # 6. Assemble daily briefing
    headline = briefing_items[0].title if briefing_items else "No items today"
    briefing = DailyBriefing(
        date=today,
        generated_at=datetime.now(tz=UTC),
        headline=headline,
        stats=_compute_stats(briefing_items),
        items=briefing_items,
    )

    # 7. Write JSON output
    output_path = write_briefing(briefing, DATA_DIR)
    logger.info("Briefing written to %s", output_path)

    # 8. Send email digest
    if settings.has_email:
        await send_digest(briefing, settings)
    else:
        logger.info("Email not configured — skipping digest")

    logger.info("=" * 60)
    logger.info("Done! %d items in today's briefing.", len(briefing_items))
    logger.info("=" * 60)

    return briefing


def main() -> None:
    """CLI entry point."""
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()

"""Data models for the AI Radar pipeline.

Defines the core types that flow through every stage:
  RawItem → (dedup, score, summarize) → BriefingItem → DailyBriefing
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Source(StrEnum):
    """Origin of a fetched item."""

    HACKERNEWS = "hackernews"
    ARXIV = "arxiv"
    RSS = "rss"


class Category(StrEnum):
    """Content category for a briefing item."""

    MODELS = "models"
    TOOLS = "tools"
    RESEARCH = "research"
    INDUSTRY = "industry"
    TUTORIALS = "tutorials"


# Display metadata for categories — used by frontend and email templates.
CATEGORY_META: dict[Category, dict[str, str]] = {
    Category.MODELS: {"label": "Models & Updates", "emoji": "🧠"},
    Category.TOOLS: {"label": "Tools & Libraries", "emoji": "🛠️"},
    Category.RESEARCH: {"label": "Research Papers", "emoji": "📄"},
    Category.INDUSTRY: {"label": "Industry News", "emoji": "📰"},
    Category.TUTORIALS: {"label": "Tutorials & Guides", "emoji": "📚"},
}


class RawItem(BaseModel):
    """An unprocessed item fetched from a source.

    This is the intermediate representation before AI summarization.
    Every source fetcher returns a list of these.
    """

    id: str = Field(description="Unique ID: '{source}-{source_id}'")
    title: str
    url: str
    source: Source
    source_detail: str = Field(
        default="",
        description="Human-readable source info, e.g. 'Hacker News (450 pts)'",
    )
    content: str = Field(
        default="",
        description="Raw content: article body, abstract, or description",
    )
    authors: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    score: int | None = Field(
        default=None,
        description="Engagement metric from source (HN points, etc.)",
    )
    relevance_score: float = Field(
        default=0.0,
        description="Computed relevance score (0-10), set by relevance scorer",
    )

    model_config = ConfigDict(frozen=False)  # Allow mutation during scoring phase


class BriefingItem(BaseModel):
    """A fully processed item ready for the daily briefing.

    Created by the AI summarizer from a scored RawItem.
    """

    id: str
    title: str
    url: str
    source: Source
    source_detail: str = ""
    category: Category
    summary: str = Field(description="AI-generated 2-3 sentence summary")
    relevance_score: float = Field(ge=0.0, le=10.0)
    tags: list[str] = Field(default_factory=list)
    published_at: datetime | None = None


class BriefingStats(BaseModel):
    """Aggregate statistics for a daily briefing."""

    total_items: int
    sources: dict[str, int] = Field(
        default_factory=dict,
        description="Item count per source",
    )
    categories: dict[str, int] = Field(
        default_factory=dict,
        description="Item count per category",
    )


class DailyBriefing(BaseModel):
    """A complete daily AI intelligence briefing.

    This is the top-level model serialized to data/YYYY-MM-DD.json
    and consumed by the frontend dashboard and email digest.
    """

    date: str = Field(description="ISO date string: YYYY-MM-DD")
    generated_at: datetime
    headline: str = Field(description="Top story headline for the day")
    stats: BriefingStats
    items: list[BriefingItem]

    def items_by_category(self) -> dict[Category, list[BriefingItem]]:
        """Group items by category, preserving relevance order within each group."""
        grouped: dict[Category, list[BriefingItem]] = {cat: [] for cat in Category}
        for item in self.items:
            grouped[item.category].append(item)
        return {cat: items for cat, items in grouped.items() if items}

"""AI summarization and categorization pipeline.

Takes scored RawItems and produces BriefingItems with:
- 2-3 sentence summaries
- Category classification
- Extracted tags

Uses a fallback chain: Gemini → Claude → extractive fallback.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from pipeline.config import AI_BATCH_SIZE, CLAUDE_MODEL, GEMINI_MODEL, Settings
from pipeline.models import BriefingItem, Category, RawItem

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an AI news curator. For each item, produce a JSON object with:
- "summary": A 2-3 sentence summary focused on what's new and why it matters.
- "category": One of: models, tools, research, industry, tutorials
- "tags": 3-5 lowercase tags (e.g. ["llm", "google", "benchmark"])

Respond with a JSON array of objects, one per input item, in the same order.
Only output valid JSON, no markdown or explanation."""


def _build_user_prompt(items: list[RawItem]) -> str:
    """Build the user prompt with items to summarize."""
    entries = []
    for i, item in enumerate(items):
        content_preview = item.content[:500] if item.content else "(no body text)"
        entries.append(
            f"[{i + 1}] Title: {item.title}\n"
            f"    Source: {item.source_detail}\n"
            f"    URL: {item.url}\n"
            f"    Content: {content_preview}"
        )
    return "Summarize and categorize these AI news items:\n\n" + "\n\n".join(entries)


async def _summarize_with_gemini(
    items: list[RawItem], settings: Settings
) -> list[dict[str, Any]] | None:
    """Attempt summarization using Google Gemini.

    Returns:
        List of dicts with summary/category/tags, or None on failure.
    """
    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)

        # Run sync Gemini client in a thread to avoid blocking the event loop
        def _call_gemini() -> str:
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=_build_user_prompt(items),
                config=genai.types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.3,
                    response_mime_type="application/json",
                ),
            )
            return resp.text

        response_text = await asyncio.to_thread(_call_gemini)
        text = response_text.strip()
        # Handle potential markdown code fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        results = json.loads(text)
        if isinstance(results, list) and len(results) == len(items):
            return results
        logger.warning("Gemini returned %d results for %d items", len(results), len(items))
        return results if isinstance(results, list) else None
    except Exception as exc:
        logger.warning("Gemini summarization failed: %s", exc)
        return None


async def _summarize_with_claude(
    items: list[RawItem], settings: Settings
) -> list[dict[str, Any]] | None:
    """Attempt summarization using Anthropic Claude.

    Returns:
        List of dicts with summary/category/tags, or None on failure.
    """
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # Run sync Anthropic client in a thread to avoid blocking the event loop
        def _call_claude() -> str:
            resp = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _build_user_prompt(items)}],
            )
            return resp.content[0].text

        response_text = await asyncio.to_thread(_call_claude)
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        results = json.loads(text)
        if isinstance(results, list):
            return results
        return None
    except Exception as exc:
        logger.warning("Claude summarization failed: %s", exc)
        return None


def _extractive_fallback(item: RawItem) -> dict[str, Any]:
    """Last-resort: extract summary from content and guess category.

    Used when both AI providers fail.
    """
    # Take first 2 sentences as summary
    content = item.content or item.title
    sentences = content.replace("\n", " ").split(". ")
    summary = ". ".join(sentences[:2]).strip()
    if summary and not summary.endswith("."):
        summary += "."
    if not summary:
        summary = item.title

    # Simple keyword-based category guess
    text_lower = f"{item.title} {item.content}".lower()
    if any(kw in text_lower for kw in ("model", "benchmark", "parameter", "weights", "fine-tun")):
        category = "models"
    elif any(
        kw in text_lower for kw in ("library", "framework", "sdk", "tool", "release", "api")
    ):
        category = "tools"
    elif any(kw in text_lower for kw in ("paper", "arxiv", "theorem", "proof", "novel")):
        category = "research"
    elif any(kw in text_lower for kw in ("tutorial", "guide", "how to", "learn", "course")):
        category = "tutorials"
    else:
        category = "industry"

    return {"summary": summary[:300], "category": category, "tags": []}


def _parse_category(raw: str) -> Category:
    """Safely parse a category string into a Category enum."""
    try:
        return Category(raw.lower().strip())
    except ValueError:
        return Category.INDUSTRY  # Safe default


def _apply_ai_result(item: RawItem, ai_result: dict[str, Any]) -> BriefingItem:
    """Merge a RawItem with its AI-generated summary to create a BriefingItem."""
    return BriefingItem(
        id=item.id,
        title=item.title,
        url=item.url,
        source=item.source,
        source_detail=item.source_detail,
        category=_parse_category(ai_result.get("category", "industry")),
        summary=ai_result.get("summary", item.title)[:500],
        relevance_score=item.relevance_score,
        tags=[t.lower().strip() for t in ai_result.get("tags", [])[:5]],
        published_at=item.published_at,
    )


async def summarize_batch(
    items: list[RawItem], settings: Settings
) -> list[BriefingItem]:
    """Summarize and categorize a batch of items using AI.

    Processes items in batches of AI_BATCH_SIZE. Falls back through
    the provider chain on failure: Gemini → Claude → extractive.

    Args:
        items: Scored and sorted raw items to process.
        settings: Runtime settings with API keys.

    Returns:
        List of BriefingItem objects ready for the daily briefing.
    """
    briefing_items: list[BriefingItem] = []

    for batch_start in range(0, len(items), AI_BATCH_SIZE):
        batch = items[batch_start : batch_start + AI_BATCH_SIZE]
        ai_results: list[dict[str, Any]] | None = None

        # Fallback chain: Gemini → Claude → extractive
        if settings.has_gemini:
            ai_results = await _summarize_with_gemini(batch, settings)

        if ai_results is None and settings.has_claude:
            logger.info("Falling back to Claude for batch %d", batch_start // AI_BATCH_SIZE)
            ai_results = await _summarize_with_claude(batch, settings)

        if ai_results is None:
            logger.warning("Both AI providers failed, using extractive fallback for batch %d",
                           batch_start // AI_BATCH_SIZE)
            ai_results = [_extractive_fallback(item) for item in batch]

        # Merge AI results with raw items
        for i, item in enumerate(batch):
            if i < len(ai_results):
                briefing_items.append(_apply_ai_result(item, ai_results[i]))
            else:
                # Fewer results than items — use fallback for remainder
                briefing_items.append(
                    _apply_ai_result(item, _extractive_fallback(item))
                )

    logger.info("Summarized %d items into briefing items", len(briefing_items))
    return briefing_items

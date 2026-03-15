"""JSON output writer for daily briefings.

Writes three files:
  - data/YYYY-MM-DD.json — the full daily briefing
  - data/latest.json — copy of today's briefing (frontend entry point)
  - data/index.json — manifest of all available dates
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pipeline.models import DailyBriefing

logger = logging.getLogger(__name__)


def _update_index(data_dir: Path, date_str: str) -> None:
    """Add today's date to the index manifest.

    Creates the index file if it doesn't exist. Maintains reverse
    chronological order (newest first).
    """
    index_path = data_dir / "index.json"

    if index_path.exists():
        try:
            index_data = json.loads(index_path.read_text())
        except (json.JSONDecodeError, OSError):
            index_data = {"dates": [], "total_briefings": 0}
    else:
        index_data = {"dates": [], "total_briefings": 0}

    dates: list[str] = index_data.get("dates", [])

    # Avoid duplicates (re-running pipeline same day)
    if date_str not in dates:
        dates.insert(0, date_str)

    index_data["dates"] = dates
    index_data["total_briefings"] = len(dates)

    index_path.write_text(json.dumps(index_data, indent=2) + "\n")
    logger.debug("Updated index.json with %d dates", len(dates))


def write_briefing(briefing: DailyBriefing, data_dir: Path) -> Path:
    """Write a daily briefing to disk as JSON.

    Creates three files:
      1. data/{date}.json — the full briefing
      2. data/latest.json — copy for the frontend to load by default
      3. data/index.json — updated manifest of all dates

    Args:
        briefing: The assembled daily briefing.
        data_dir: Path to the data/ directory.

    Returns:
        Path to the written daily briefing file.
    """
    data_dir.mkdir(parents=True, exist_ok=True)

    # Serialize with ISO datetime formatting
    briefing_json = briefing.model_dump_json(indent=2)

    # 1. Write dated file
    dated_path = data_dir / f"{briefing.date}.json"
    dated_path.write_text(briefing_json + "\n")
    logger.info("Wrote briefing to %s", dated_path)

    # 2. Write latest.json (same content, stable URL for frontend)
    latest_path = data_dir / "latest.json"
    latest_path.write_text(briefing_json + "\n")

    # 3. Update index manifest
    _update_index(data_dir, briefing.date)

    return dated_path

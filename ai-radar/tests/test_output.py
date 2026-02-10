"""Tests for output generation — JSON writer and email digest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.output.json_writer import write_briefing, _update_index
from pipeline.output.email_digest import _render_digest_html


class TestJSONWriter:
    """Tests for the JSON file writer."""

    def test_write_briefing(self, tmp_path, sample_briefing):
        data_dir = tmp_path / "data"
        output_path = write_briefing(sample_briefing, data_dir)

        # Dated file
        assert output_path.exists()
        assert output_path.name == "2025-02-10.json"
        content = json.loads(output_path.read_text())
        assert content["date"] == "2025-02-10"
        assert len(content["items"]) == 3

        # Latest file
        latest = data_dir / "latest.json"
        assert latest.exists()
        latest_content = json.loads(latest.read_text())
        assert latest_content["date"] == "2025-02-10"

        # Index file
        index = data_dir / "index.json"
        assert index.exists()
        index_content = json.loads(index.read_text())
        assert "2025-02-10" in index_content["dates"]
        assert index_content["total_briefings"] == 1

    def test_write_briefing_creates_directory(self, tmp_path, sample_briefing):
        data_dir = tmp_path / "nested" / "data"
        write_briefing(sample_briefing, data_dir)
        assert data_dir.exists()

    def test_update_index_no_duplicates(self, tmp_path):
        index_path = tmp_path / "index.json"
        _update_index(tmp_path, "2025-02-10")
        _update_index(tmp_path, "2025-02-10")  # Same date again

        index_data = json.loads(index_path.read_text())
        assert index_data["dates"].count("2025-02-10") == 1

    def test_update_index_ordering(self, tmp_path):
        _update_index(tmp_path, "2025-02-08")
        _update_index(tmp_path, "2025-02-09")
        _update_index(tmp_path, "2025-02-10")

        index_data = json.loads((tmp_path / "index.json").read_text())
        assert index_data["dates"][0] == "2025-02-10"  # Newest first

    def test_briefing_json_roundtrip(self, tmp_path, sample_briefing):
        """Verify the written JSON can be deserialized back into a DailyBriefing."""
        from pipeline.models import DailyBriefing

        data_dir = tmp_path / "data"
        output_path = write_briefing(sample_briefing, data_dir)
        restored = DailyBriefing.model_validate_json(output_path.read_text())
        assert restored.date == sample_briefing.date
        assert len(restored.items) == len(sample_briefing.items)


class TestEmailDigest:
    """Tests for email digest HTML rendering."""

    def test_render_digest_html(self, sample_briefing):
        html = _render_digest_html(sample_briefing, "https://example.github.io/ai-radar/")
        assert "AI Radar" in html
        assert "OpenAI" in html
        assert "2025-02-10" in html
        assert "https://example.github.io/ai-radar/" in html

    def test_render_digest_has_categories(self, sample_briefing):
        html = _render_digest_html(sample_briefing, "https://example.com")
        assert "Models" in html
        assert "Research" in html

    def test_render_digest_has_links(self, sample_briefing):
        html = _render_digest_html(sample_briefing, "https://example.com")
        assert "openai.com" in html
        assert "arxiv.org" in html

# 🛰️ AI Radar

**Auto-curated daily AI intelligence briefings from the web's top sources.**

AI Radar is a Python pipeline that aggregates AI news from Hacker News, arXiv, and 10 major AI blogs, scores each item for relevance, summarizes them using a multi-LLM fallback chain (Gemini → Claude → extractive), and publishes a daily briefing to a web dashboard and optional email digest.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

---

## Architecture

```
┌─────────────┐  ┌──────────┐  ┌──────────┐
│ Hacker News │  │  arXiv   │  │ 10 RSS   │
│  Firebase   │  │ Atom API │  │  Feeds   │
└──────┬──────┘  └────┬─────┘  └────┬─────┘
       │              │             │
       └──────────────┼─────────────┘
                      │  async fetch (concurrent)
                      ▼
              ┌───────────────┐
              │  Dedup Layer  │  URL normalization + Jaccard title similarity
              └───────┬───────┘
                      ▼
              ┌───────────────┐
              │   Relevance   │  Keyword density + source authority
              │    Scoring    │  + recency decay + engagement
              └───────┬───────┘
                      ▼
              ┌───────────────┐
              │ AI Summarizer │  Gemini → Claude → extractive fallback
              │  (batched)    │  Categorize + tag + summarize
              └───────┬───────┘
                      ▼
         ┌────────────┴────────────┐
         ▼                         ▼
  ┌──────────────┐         ┌──────────────┐
  │  JSON Output │         │ Email Digest │
  │  (dashboard) │         │   (Resend)   │
  └──────────────┘         └──────────────┘
```

## Features

- **Multi-source aggregation** — Hacker News (Firebase API), arXiv (cs.AI, cs.LG, cs.CL), and 10 curated RSS feeds (OpenAI, Anthropic, Google AI, Meta AI, Hugging Face, and more)
- **Concurrent fetching** — All sources and individual story lookups run via `asyncio.gather` for fast pipeline execution
- **Smart deduplication** — URL normalization + Jaccard similarity on titles catches cross-posted stories
- **Relevance scoring** — Multi-factor scoring (keyword density, source authority, recency, engagement) with configurable weights
- **AI-powered summarization** — Three-tier fallback chain: Google Gemini → Anthropic Claude → extractive fallback. Always produces results, even without API keys
- **Daily briefing dashboard** — Dark-themed web UI with category filtering, search, date navigation, and skeleton loading states
- **Email digest** — Jinja2-templated HTML emails sent via Resend, grouped by category
- **Automated via GitHub Actions** — Daily cron job generates briefings, commits data, and deploys dashboard via GitHub Pages
- **44 tests** — Comprehensive test suite with `pytest`, `pytest-asyncio`, and `respx` HTTP mocking

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Async runtime | `asyncio` |
| HTTP client | `httpx` (async) |
| Data validation | Pydantic v2 |
| AI providers | Google Gemini (`google-genai`), Anthropic Claude (`anthropic`) |
| Feed parsing | `feedparser` |
| Email | Resend API + Jinja2 templates |
| Frontend | Vanilla HTML/CSS/JS (no build step) |
| CI/CD | GitHub Actions |
| Linting | Ruff |
| Testing | pytest + pytest-asyncio + respx |

## Quick Start

### Prerequisites

- Python 3.11 or higher
- At least one AI API key (Gemini or Anthropic) for AI-powered summaries — *or run without for extractive-only mode*

### Setup

```bash
# Clone the repo
git clone https://github.com/c0de-mule/ai-radar.git
cd ai-radar/ai-radar

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Run the pipeline

```bash
python -m pipeline.main
```

Output is written to `data/YYYY-MM-DD.json` and `data/latest.json`.

### View the dashboard

```bash
# Serve the docs directory locally
python -m http.server 8000 --directory docs
# Open http://localhost:8000
```

### Run tests

```bash
pip install -e ".[dev]"
pytest
```

## Configuration

All pipeline parameters are in `pipeline/config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_ITEMS_TO_SUMMARIZE` | 30 | Top N items sent to AI for summarization |
| `MAX_ITEMS_IN_BRIEFING` | 25 | Final briefing cap |
| `MAX_ITEMS_IN_EMAIL` | 15 | Items per email digest |
| `DEDUP_TITLE_SIMILARITY_THRESHOLD` | 0.7 | Jaccard similarity threshold for title dedup |
| `CONTENT_MAX_AGE_HOURS` | 48 | Only include items from the last 48 hours |
| `HN_MIN_SCORE` | 20 | Minimum HN score to include a story |
| `AI_BATCH_SIZE` | 5 | Items per AI API call |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | One of Gemini/Claude | Google Gemini API key |
| `ANTHROPIC_API_KEY` | One of Gemini/Claude | Anthropic Claude API key |
| `RESEND_API_KEY` | No | Resend API key for email digest |
| `EMAIL_RECIPIENTS` | No | Comma-separated list of email addresses |
| `DASHBOARD_URL` | No | URL to the web dashboard (used in emails) |

> **Note:** The pipeline works without any API keys using the extractive fallback summarizer, producing functional but lower-quality summaries.

## License

MIT — see [LICENSE](LICENSE).

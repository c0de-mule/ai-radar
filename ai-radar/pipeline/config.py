"""Configuration for the AI Radar pipeline.

All tunable parameters live here: sources, keywords, API keys, and limits.
API keys are loaded from environment variables (set as GitHub Secrets in CI).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# AI keyword filter — items must contain at least one of these to pass
# ---------------------------------------------------------------------------
AI_KEYWORDS: list[str] = [
    # Core AI/ML terms
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "neural network", "llm", "large language model", "nlp",
    "natural language processing", "computer vision",
    # Models & architectures
    "transformer", "diffusion", "gpt", "claude", "gemini", "llama",
    "mistral", "phi-", "qwen", "deepseek", "stable diffusion", "midjourney",
    "dall-e", "sora", "whisper", "codex",
    # Techniques
    "fine-tuning", "fine tuning", "rlhf", "rag", "retrieval augmented",
    "prompt engineering", "chain of thought", "cot", "few-shot", "zero-shot",
    "embedding", "vector database", "tokenizer", "quantization", "lora",
    "qlora", "distillation", "mixture of experts", "moe",
    # Tools & infra
    "openai", "anthropic", "hugging face", "huggingface",
    "langchain", "llamaindex", "ollama", "vllm", "pytorch", "tensorflow",
    "jax", "mlx", "onnx", "triton", "cuda",
    # Applications
    "chatbot", "copilot", "ai agent", "ai coding", "text-to-image",
    "text-to-video", "text-to-speech", "speech-to-text",
    "autonomous", "self-driving", "robotics",
    # Industry
    "agi", "ai safety", "alignment", "ai regulation", "ai policy",
    "ai ethics", "superintelligence", "frontier model",
]

# ---------------------------------------------------------------------------
# RSS feed sources
# ---------------------------------------------------------------------------
RSS_FEEDS: list[dict[str, str]] = [
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
    {"name": "Meta AI Blog", "url": "https://ai.meta.com/blog/rss/"},
    {"name": "Anthropic Blog", "url": "https://www.anthropic.com/rss.xml"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "Lilian Weng", "url": "https://lilianweng.github.io/index.xml"},
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/"},
    {"name": "Latent Space", "url": "https://www.latent.space/feed"},
    {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed"},
    {"name": "The Batch (deeplearning.ai)", "url": "https://www.deeplearning.ai/the-batch/feed/"},
]

# ---------------------------------------------------------------------------
# arXiv categories
# ---------------------------------------------------------------------------
ARXIV_CATEGORIES: list[str] = ["cs.AI", "cs.LG", "cs.CL"]
ARXIV_MAX_RESULTS: int = 50

# ---------------------------------------------------------------------------
# Hacker News
# ---------------------------------------------------------------------------
HN_TOP_STORIES_LIMIT: int = 100
HN_MIN_SCORE: int = 20  # Ignore low-engagement stories

# ---------------------------------------------------------------------------
# Pipeline limits
# ---------------------------------------------------------------------------
MAX_ITEMS_TO_SUMMARIZE: int = 30  # Send top N to AI for summarization
MAX_ITEMS_IN_BRIEFING: int = 25  # Final briefing cap
MAX_ITEMS_IN_EMAIL: int = 15  # Email should be scannable in 2 min
DEDUP_TITLE_SIMILARITY_THRESHOLD: float = 0.7
CONTENT_MAX_AGE_HOURS: int = 48  # Only include items from last 48h

# ---------------------------------------------------------------------------
# AI summarization
# ---------------------------------------------------------------------------
GEMINI_MODEL: str = "gemini-2.5-flash"
CLAUDE_MODEL: str = "claude-haiku-4-20250414"
AI_BATCH_SIZE: int = 5  # Items per API call to stay within token limits

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_FROM: str = "AI Radar <radar@resend.dev>"


@dataclass
class Settings:
    """Runtime settings loaded from environment variables.

    In GitHub Actions these come from repository secrets.
    Locally, set them in a .env file or export in your shell.
    """

    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    resend_api_key: str = field(default_factory=lambda: os.environ.get("RESEND_API_KEY", ""))
    email_recipients: list[str] = field(
        default_factory=lambda: [
            addr.strip()
            for addr in os.environ.get("EMAIL_RECIPIENTS", "").split(",")
            if addr.strip()
        ]
    )
    dashboard_url: str = field(
        default_factory=lambda: os.environ.get(
            "DASHBOARD_URL", "https://everettcento.github.io/ai-radar/"
        )
    )

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_claude(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_email(self) -> bool:
        return bool(self.resend_api_key and self.email_recipients)


def load_settings() -> Settings:
    """Load settings from environment. Call once at pipeline start."""
    return Settings()

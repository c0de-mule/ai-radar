"""Email digest generation and sending.

Renders the daily briefing into an HTML email using a Jinja2 template
and sends it via the Resend API.
"""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from pipeline.config import EMAIL_FROM, MAX_ITEMS_IN_EMAIL, Settings
from pipeline.models import CATEGORY_META, Category, DailyBriefing

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def _render_digest_html(briefing: DailyBriefing, dashboard_url: str) -> str:
    """Render the email digest HTML from the Jinja2 template.

    Args:
        briefing: Today's daily briefing.
        dashboard_url: URL to the web dashboard.

    Returns:
        Rendered HTML string.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("digest.html")

    # Group items by category, limited to email max
    grouped = briefing.items_by_category()
    email_items: dict[str, list] = {}
    total_shown = 0

    for cat in Category:
        if cat not in grouped or total_shown >= MAX_ITEMS_IN_EMAIL:
            continue
        remaining = MAX_ITEMS_IN_EMAIL - total_shown
        cat_items = grouped[cat][:remaining]
        if cat_items:
            meta = CATEGORY_META[cat]
            email_items[f"{meta['emoji']} {meta['label']}"] = cat_items
            total_shown += len(cat_items)

    return template.render(
        briefing=briefing,
        grouped_items=email_items,
        dashboard_url=dashboard_url,
    )


async def send_digest(briefing: DailyBriefing, settings: Settings) -> bool:
    """Generate and send the daily email digest.

    Args:
        briefing: Today's daily briefing.
        settings: Runtime settings with API key and recipients.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    if not settings.has_email:
        logger.info("Email not configured — skipping digest")
        return False

    html = _render_digest_html(briefing, settings.dashboard_url)

    try:
        import resend

        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": EMAIL_FROM,
                "to": settings.email_recipients,
                "subject": f"🛰️ AI Radar — {briefing.headline}",
                "html": html,
            }
        )
        logger.info("Sent digest email to %d recipients", len(settings.email_recipients))
        return True
    except Exception as exc:
        logger.error("Failed to send digest email: %s", exc)
        return False

"""Plain-text and HTML email rendering.

The HTML uses table layout and inline styles for broad email-client
compatibility. All scraped values (titles, URLs) are HTML-escaped before
they reach the markup.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from html import escape

from .match import enrich_job
from .models import AppConfig, JobListing
from .out import short_error

EMAIL_THEME = {
    "background": "#F3F1F8",
    "header": "#1C1A31",
    "text": "#111827",
    "muted": "#757982",
    "panel": "#FFFFFF",
    "border": "#E5E7EB",
    "soft_muted": "#D1D5DB",
    "gradient": "#7D46D8 0%, #0093B8 34%, #C0E021 68%, #EE263E 100%",
    "cards": [
        {"name": "VIOLET", "accent": "#7D46D8", "soft": "#F1ECFB"},
        {"name": "TEAL", "accent": "#0093B8", "soft": "#E6F7FB"},
        {"name": "MINT", "accent": "#00A892", "soft": "#E6FAF7"},
        {"name": "LIME", "accent": "#8DB600", "soft": "#F8FCDD"},
        {"name": "RED", "accent": "#EE263E", "soft": "#FDE9EC"},
        {"name": "BLUE", "accent": "#2563EB", "soft": "#EAF1FF"},
        {"name": "AMBER", "accent": "#D97706", "soft": "#FFF4DB"},
    ],
}


class EmailError(Exception):
    """An alert email could not be sent."""


def format_email_body(jobs: list[JobListing]) -> str:
    lines = [
        f"Role Radar found {len(jobs)} new role(s).",
        "",
    ]

    for i, job in enumerate(jobs, 1):
        lines.append(f"{i}. {job.title}")
        if job.property_name:
            lines.append(f"   {job.property_name}")
        lines.append(f"   {job.url or '(no link)'}")
        lines.append("")

    return "\n".join(lines).rstrip()


def send_email(cfg: AppConfig,
               subject: str,
               body: str,
               html_body: str | None = None) -> None:
    """Send a STARTTLS SMTP message, raising EmailError on any failure."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.email_user
    msg["To"] = cfg.email_to

    msg.set_content(body)

    # Multipart alternative: clients pick HTML when supported, else plain text.
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as server:
            server.starttls()  # upgrade the plaintext connection before login
            server.login(cfg.email_user, cfg.email_password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as err:
        raise EmailError(
            f"Failed to send via {cfg.smtp_host}:{cfg.smtp_port}: "
            f"{short_error(err)}"
        )


def _button_html(url: str) -> str:
    if not url:
        return (
            f'<p style="color:{EMAIL_THEME["muted"]};margin:14px 0 0;">'
            "No link available</p>"
        )

    return (
        f'<a href="{url}" '
        f'style="display:inline-block;margin-top:16px;padding:10px 15px;'
        f'border-radius:999px;background:{EMAIL_THEME["text"]};color:#ffffff;'
        f'text-decoration:none;font-size:14px;font-weight:700;">'
        "Learn more</a>"
    )


def _email_card(job: JobListing, index: int) -> str:
    # Cycle through the fixed palette so consecutive cards alternate accents.
    color = EMAIL_THEME["cards"][(index - 1) % len(EMAIL_THEME["cards"])]
    property_name = escape(job.property_name or "New match")
    button = _button_html(escape(job.url))

    return (
        '<tr>'
        '<td style="padding:0 0 14px;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{color["soft"]};border:1px solid {EMAIL_THEME["border"]};'
        f'border-left:6px solid {color["accent"]};border-radius:14px;overflow:hidden;">'
        '<tr>'
        '<td style="padding:18px 20px;">'
        f'<div style="font-size:13px;line-height:1.4;color:{EMAIL_THEME["muted"]};'
        'font-weight:700;margin-bottom:7px;">'
        f'{property_name}</div>'
        '<div style="font-size:20px;line-height:1.3;font-weight:800;'
        f'color:{EMAIL_THEME["text"]};">'
        f'{escape(job.title)}</div>'
        f'{button}'
        '</td>'
        '</tr>'
        '</table>'
        '</td>'
        '</tr>'
    )


def _email_shell(count: int, cards_html: str, status_label: str) -> str:
    role_word = "role" if count == 1 else "roles"

    return (
        '<!doctype html>'
        '<html>'
        f'<body style="margin:0;padding:0;background:{EMAIL_THEME["background"]};">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{EMAIL_THEME["background"]};padding:28px 12px;'
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;"
        '">'
        '<tr><td align="center">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="max-width:640px;background:{EMAIL_THEME["panel"]};border-radius:20px;'
        f'overflow:hidden;border:1px solid {EMAIL_THEME["soft_muted"]};">'
        '<tr><td style="padding:0;height:8px;'
        f'background:linear-gradient(90deg,{EMAIL_THEME["gradient"]});"></td></tr>'
        '<tr>'
        f'<td style="padding:30px;background:{EMAIL_THEME["header"]};color:#ffffff;">'
        '<div style="font-size:13px;letter-spacing:.12em;text-transform:uppercase;'
        'color:#B9BBC5;margin-bottom:10px;font-weight:800;">Role Radar</div>'
        '<div style="font-size:30px;line-height:1.15;font-weight:850;">'
        f'{count} {status_label} {role_word} found</div>'
        '<div style="margin-top:10px;font-size:15px;line-height:1.5;color:#d1d5db;">'
        'Fresh matches from your watched job titles.</div>'
        '</td></tr>'
        '<tr><td style="padding:24px 30px 10px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        f'{cards_html}'
        '</table></td></tr>'
        f'<tr><td style="padding:10px 30px 26px;color:{EMAIL_THEME["muted"]};'
        'font-size:13px;line-height:1.5;">'
        'Duplicate alerts are suppressed using saved seen-role state.'
        '</td></tr>'
        '</table>'
        '</td></tr>'
        '</table>'
        '</body>'
        '</html>'
    )


def format_email_html(jobs: list[JobListing],
                      status_label: str = "new") -> str:
    """Render the full alert email; status_label heads the count ("new"/"matching")."""
    cards_html = "\n".join(_email_card(enrich_job(job), i)
                           for i, job in enumerate(jobs, 1))
    return _email_shell(len(jobs), cards_html, status_label)

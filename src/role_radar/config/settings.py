"""Environment-backed configuration for Role Radar."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from ..models import AppConfig


class ConfigError(Exception):
    """Required configuration is missing or invalid."""


def _split(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _valid_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def resolve_config(env_path: Path) -> AppConfig:
    """Build an AppConfig from .env plus process environment defaults.

    load_dotenv does not override variables already present in the
    environment, so an exported shell value wins over the .env file.
    """
    load_dotenv(env_path)

    raw_port = os.getenv("SMTP_PORT", "587").strip()
    try:
        smtp_port = int(raw_port)
    except ValueError:
        raise ConfigError(f"SMTP_PORT must be an integer (got {raw_port!r}).")

    email_user = os.getenv("EMAIL_USER", "").strip()
    return AppConfig(
        url=os.getenv("JOB_BOARD_URL", "").strip(),
        keywords=_split(os.getenv("JOB_TITLES", "")),
        exclude=_split(os.getenv("EXCLUDE_TITLES", "")),
        item_class=os.getenv("JOB_ITEM_CLASS", "vizi-item-title").strip(),
        email_user=email_user,
        email_password=os.getenv("EMAIL_PASSWORD", ""),
        email_to=os.getenv("EMAIL_TO", "").strip() or email_user,
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com").strip(),
        smtp_port=smtp_port,
    )


def require_config(cfg: AppConfig, env_path: Path, *, require_email: bool) -> None:
    """Raise ConfigError if required settings are absent.

    Email credentials are only enforced when require_email is set, so
    `check` and `doctor` can validate the board config without them.
    """
    missing = []
    if not cfg.url:
        missing.append("JOB_BOARD_URL")
    elif not _valid_http_url(cfg.url):
        raise ConfigError("JOB_BOARD_URL must be a valid http(s) URL.")
    if not cfg.keywords:
        missing.append("JOB_TITLES")
    if require_email:
        if not cfg.email_user:
            missing.append("EMAIL_USER")
        if not cfg.email_password:
            missing.append("EMAIL_PASSWORD")
        if not cfg.smtp_host:
            missing.append("SMTP_HOST")

    if missing:
        prefix = "Missing required config"
        if not env_path.exists():
            prefix = "Missing .env and required config"
        raise ConfigError(
            f"{prefix}: {', '.join(missing)}. "
            f"Copy .env.example to {env_path.name} and fill it in."
        )


def format_config(cfg: AppConfig) -> str:
    """Render resolved config for `config show`, never echoing the password."""
    def shown(value: str) -> str:
        return value if value else "(not set)"

    # Report only whether the password exists; its value never reaches output.
    password = "set (hidden)" if cfg.email_password else "(not set)"
    rows = [
        ("JOB_BOARD_URL", shown(cfg.url)),
        ("JOB_TITLES", shown(", ".join(cfg.keywords))),
        ("EXCLUDE_TITLES", shown(", ".join(cfg.exclude))),
        ("JOB_ITEM_CLASS", shown(cfg.item_class)),
        ("EMAIL_USER", shown(cfg.email_user)),
        ("EMAIL_PASSWORD", password),
        ("EMAIL_TO", shown(cfg.email_to)),
        ("SMTP_HOST", shown(cfg.smtp_host)),
        ("SMTP_PORT", str(cfg.smtp_port)),
    ]
    lines = ["Role Radar configuration (resolved):"]
    lines += [f"  {name:<15}: {value}" for name, value in rows]
    return "\n".join(lines)

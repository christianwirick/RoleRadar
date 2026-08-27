"""Tests for config loading and display."""

from role_radar.config import format_config
from role_radar.models import AppConfig


def test_format_config_masks_password():
    cfg = AppConfig(
        url="https://example.com",
        keywords=("analyst",),
        exclude=(),
        item_class="vizi-item-title",
        email_user="me@example.com",
        email_password="super-secret-value",
        email_to="me@example.com",
        smtp_host="smtp.gmail.com",
        smtp_port=587,
    )
    out = format_config(cfg)
    assert "super-secret-value" not in out
    assert "set (hidden)" in out
    assert "me@example.com" in out


def test_format_config_marks_unset_password():
    cfg = AppConfig(
        url="",
        keywords=(),
        exclude=(),
        item_class="vizi-item-title",
        email_user="",
        email_password="",
        email_to="",
        smtp_host="smtp.gmail.com",
        smtp_port=587,
    )
    out = format_config(cfg)
    pw_line = next(line for line in out.splitlines() if "EMAIL_PASSWORD" in line)
    assert pw_line.strip().endswith("(not set)")

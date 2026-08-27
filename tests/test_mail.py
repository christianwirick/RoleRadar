"""Tests for email rendering."""

from role_radar import mail
from role_radar.models import JobListing


def test_format_email_body_lists_title_property_and_url():
    body = mail.format_email_body(
        [JobListing("Data Analyst", "https://x/1", "M Resort")]
    )
    assert "Data Analyst" in body
    assert "M Resort" in body
    assert "https://x/1" in body


def test_format_email_html_uses_theme_and_escapes_content():
    html = mail.format_email_html(
        [JobListing("Data <Analyst>", "https://x/1?team=<finance>")]
    )
    assert mail.EMAIL_THEME["header"] in html
    assert "Data &lt;Analyst&gt;" in html
    assert "https://x/1?team=&lt;finance&gt;" in html
    assert "VIOLET MATCH" not in html
    assert "Open role" not in html
    assert "Learn more" in html

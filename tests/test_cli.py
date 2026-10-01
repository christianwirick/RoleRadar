"""Tests for the simplified Role Radar CLI."""

from pathlib import Path

import pytest

from role_radar import cli as rr
from role_radar import mail, out, scraper, state
from role_radar.scraper import BrowserStatus

SAMPLE_HTML = """
<html><body>
  <a href="https://jobs.example.com/1"><h3 class="vizi-item-title">Senior Data Analyst</h3></a>
  <a href="https://jobs.example.com/2"><h3 class="vizi-item-title">IT Support Analyst</h3></a>
  <a href="https://jobs.example.com/3"><h3 class="vizi-item-title">Marketing Manager</h3></a>
</body></html>
"""

CONFIG_VARS = [
    "JOB_BOARD_URL",
    "JOB_TITLES",
    "EXCLUDE_TITLES",
    "JOB_ITEM_CLASS",
    "EMAIL_USER",
    "EMAIL_PASSWORD",
    "EMAIL_TO",
    "SMTP_HOST",
    "SMTP_PORT",
]


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    """Keep every test off real files, logs, and environment config."""
    app_dir = tmp_path / "RoleRadar"
    monkeypatch.setattr(rr, "APP_DIR", app_dir)
    monkeypatch.setattr(rr, "ENV_PATH", app_dir / ".env")
    monkeypatch.setattr(rr, "SEEN_PATH", app_dir / "seen_jobs.json")
    monkeypatch.setattr(rr, "LOG_PATH", app_dir / "role_radar.log")
    monkeypatch.setattr(out, "setup_logging", lambda _path: None)

    for var in CONFIG_VARS:
        monkeypatch.delenv(var, raising=False)

    return tmp_path


def _set_board(monkeypatch):
    monkeypatch.setenv("JOB_BOARD_URL", "https://example.com")
    monkeypatch.setenv("JOB_TITLES", "analyst")
    monkeypatch.setattr(scraper, "fetch_html", lambda *a, **k: SAMPLE_HTML)


def _set_email(monkeypatch):
    monkeypatch.setenv("EMAIL_USER", "me@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "app-password")


def test_runtime_paths_live_outside_repo():
    expected = Path.home() / ".config" / "RoleRadar"
    assert rr.APP_DIR == expected
    assert rr.ENV_PATH == expected / ".env"
    assert rr.SEEN_PATH == expected / "seen_jobs.json"
    assert rr.LOG_PATH == expected / "role_radar.log"


def test_test_scans_without_sending_or_persisting(monkeypatch, capsys, tmp_path):
    _set_board(monkeypatch)
    sent = []
    monkeypatch.setattr(rr, "send_email", lambda *a, **k: sent.append(1))

    assert rr.main(["test"]) == 0

    output = capsys.readouterr().out
    assert "Role Radar — test" in output
    assert "Senior Data Analyst" in output
    assert sent == []
    assert not (tmp_path / "RoleRadar" / "seen_jobs.json").exists()


def test_test_does_not_require_email(monkeypatch):
    _set_board(monkeypatch)
    assert rr.main(["test"]) == 0


def test_run_sends_then_dedupes(monkeypatch, tmp_path):
    _set_board(monkeypatch)
    _set_email(monkeypatch)
    sent = []
    monkeypatch.setattr(
        rr,
        "send_email",
        lambda cfg, subj, body, html=None: sent.append(subj),
    )

    assert rr.main(["run"]) == 0
    assert len(sent) == 1
    state_path = tmp_path / "RoleRadar" / "seen_jobs.json"
    assert "https://jobs.example.com/1" in state.load_seen(state_path)

    sent.clear()
    assert rr.main(["run"]) == 0
    assert sent == []


def test_re_resends_seen_roles_without_clearing_first(monkeypatch, tmp_path, capsys):
    _set_board(monkeypatch)
    _set_email(monkeypatch)
    state_path = tmp_path / "RoleRadar" / "seen_jobs.json"
    state.save_seen({"https://jobs.example.com/1", "keep-me"}, state_path)
    sent = []
    monkeypatch.setattr(
        rr,
        "send_email",
        lambda cfg, subj, body, html=None: sent.append(subj),
    )

    assert rr.main(["re"]) == 0

    output = capsys.readouterr().out
    assert "Retesting 2 current role(s)." in output
    assert len(sent) == 1
    remembered = state.load_seen(state_path)
    assert "https://jobs.example.com/1" in remembered
    assert "keep-me" in remembered


def test_re_email_failure_preserves_existing_state(monkeypatch, tmp_path):
    _set_board(monkeypatch)
    _set_email(monkeypatch)
    state_path = tmp_path / "RoleRadar" / "seen_jobs.json"
    original = {"https://jobs.example.com/1", "keep-me"}
    state.save_seen(original, state_path)

    def boom(*a, **k):
        raise mail.EmailError("smtp refused")

    monkeypatch.setattr(rr, "send_email", boom)

    assert rr.main(["re"]) == 1
    assert state.load_seen(state_path) == original


def test_run_missing_config_is_exit_2(monkeypatch):
    assert rr.main(["run"]) == 2


def test_run_scrape_failure_is_exit_1_no_send(monkeypatch):
    _set_board(monkeypatch)
    _set_email(monkeypatch)

    def boom(*a, **k):
        raise scraper.ScrapeError("network down")

    sent = []
    monkeypatch.setattr(scraper, "fetch_html", boom)
    monkeypatch.setattr(rr, "send_email", lambda *a, **k: sent.append(1))

    assert rr.main(["run"]) == 1
    assert sent == []


def test_run_email_failure_is_exit_1_no_state(monkeypatch, tmp_path):
    _set_board(monkeypatch)
    _set_email(monkeypatch)

    def boom(*a, **k):
        raise mail.EmailError("smtp refused")

    monkeypatch.setattr(rr, "send_email", boom)

    assert rr.main(["run"]) == 1
    assert not (tmp_path / "RoleRadar" / "seen_jobs.json").exists()


def test_conf_masks_password(monkeypatch, capsys):
    monkeypatch.setenv("JOB_BOARD_URL", "https://example.com")
    monkeypatch.setenv("JOB_TITLES", "analyst")
    monkeypatch.setenv("EMAIL_PASSWORD", "do-not-print-me")

    assert rr.main(["conf"]) == 0

    output = capsys.readouterr().out
    assert "do-not-print-me" not in output
    assert "set (hidden)" in output


def test_conf_bad_port_is_exit_2(monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "not-a-number")
    assert rr.main(["conf"]) == 2


def test_jobs_lists_remembered_jobs(capsys, tmp_path):
    state_path = tmp_path / "RoleRadar" / "seen_jobs.json"
    state.save_seen({"https://x/1", "https://x/2"}, state_path)

    assert rr.main(["jobs"]) == 0

    output = capsys.readouterr().out
    assert "2 role(s) remembered" in output
    assert "https://x/1" in output


def test_reset_clears_state(capsys, tmp_path):
    state_path = tmp_path / "RoleRadar" / "seen_jobs.json"
    state.save_seen({"https://x/1", "https://x/2"}, state_path)

    assert rr.main(["reset"]) == 0

    assert "Forgot 2" in capsys.readouterr().out
    assert state.load_seen(state_path) == set()


def test_check_launches_browser(monkeypatch, tmp_path, capsys):
    _set_board(monkeypatch)
    _set_email(monkeypatch)
    app_dir = tmp_path / "RoleRadar"
    app_dir.mkdir()
    (app_dir / ".env").write_text("JOB_BOARD_URL=https://example.com\n")

    monkeypatch.setattr(
        scraper,
        "check_browser",
        lambda: BrowserStatus(
            browser_version="152.0.0",
            driver_version="152.0.0",
            driver_path="/tmp/chromedriver",
        ),
    )

    assert rr.main(["check"]) == 0

    output = capsys.readouterr().out
    assert "Chrome 152.0.0 launched successfully" in output
    assert "ChromeDriver 152.0.0 is working" in output
    assert "Ready to run." in output


def test_check_reports_browser_failure(monkeypatch, tmp_path, capsys):
    _set_board(monkeypatch)
    _set_email(monkeypatch)
    app_dir = tmp_path / "RoleRadar"
    app_dir.mkdir()
    (app_dir / ".env").write_text("JOB_BOARD_URL=https://example.com\n")

    def boom():
        raise scraper.ScrapeError("Chrome/ChromeDriver launch failed: blocked")

    monkeypatch.setattr(scraper, "check_browser", boom)

    assert rr.main(["check"]) == 2
    assert "Chrome/ChromeDriver launch failed" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv",
    [
        ["doctor"],
        ["config", "show"],
        ["seen", "list"],
        ["seen", "reset"],
        ["titles", "show"],
        ["preview-email"],
        ["export-clean"],
        ["version"],
        ["clear"],
    ],
)
def test_removed_commands_are_usage_errors(argv):
    with pytest.raises(SystemExit) as exc:
        rr.main(argv)
    assert exc.value.code == 2


def test_no_command_is_usage_error():
    with pytest.raises(SystemExit) as exc:
        rr.main([])
    assert exc.value.code == 2


def test_unknown_command_is_usage_error():
    with pytest.raises(SystemExit) as exc:
        rr.main(["bogus"])
    assert exc.value.code == 2

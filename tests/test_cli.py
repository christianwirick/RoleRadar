"""Tests for the simplified Role Radar CLI."""

import pytest

from role_radar import cli as rr
from role_radar import mail, out, scraper, state

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
    monkeypatch.setattr(rr, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(rr, "SEEN_PATH", tmp_path / "seen.json")
    monkeypatch.setattr(rr, "LOG_PATH", tmp_path / "logs" / "role_radar.log")
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


def test_test_scans_without_sending_or_persisting(monkeypatch, capsys, tmp_path):
    _set_board(monkeypatch)
    sent = []
    monkeypatch.setattr(rr, "send_email", lambda *a, **k: sent.append(1))

    assert rr.main(["test"]) == 0

    output = capsys.readouterr().out
    assert "Role Radar — test" in output
    assert "Senior Data Analyst" in output
    assert sent == []
    assert not (tmp_path / "seen.json").exists()


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
    assert "https://jobs.example.com/1" in state.load_seen(tmp_path / "seen.json")

    sent.clear()
    assert rr.main(["run"]) == 0
    assert sent == []


def test_re_resets_state_then_runs_again(monkeypatch, tmp_path, capsys):
    _set_board(monkeypatch)
    _set_email(monkeypatch)
    state.save_seen({"https://jobs.example.com/1"}, tmp_path / "seen.json")
    sent = []
    monkeypatch.setattr(
        rr,
        "send_email",
        lambda cfg, subj, body, html=None: sent.append(subj),
    )

    assert rr.main(["re"]) == 0
    assert "Forgot 1 remembered role(s)" in capsys.readouterr().out
    assert len(sent) == 1
    assert "https://jobs.example.com/1" in state.load_seen(tmp_path / "seen.json")


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
    assert not (tmp_path / "seen.json").exists()


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
    state.save_seen({"https://x/1", "https://x/2"}, tmp_path / "seen.json")

    assert rr.main(["jobs"]) == 0

    output = capsys.readouterr().out
    assert "2 role(s) remembered" in output
    assert "https://x/1" in output


def test_reset_clears_state(capsys, tmp_path):
    state.save_seen({"https://x/1", "https://x/2"}, tmp_path / "seen.json")

    assert rr.main(["reset"]) == 0

    assert "Forgot 2" in capsys.readouterr().out
    assert state.load_seen(tmp_path / "seen.json") == set()


def test_check_passes_with_ready_config(monkeypatch, tmp_path, capsys):
    _set_board(monkeypatch)
    _set_email(monkeypatch)
    (tmp_path / ".env").write_text("JOB_BOARD_URL=https://example.com\n")
    (tmp_path / "logs").mkdir()

    assert rr.main(["check"]) == 0

    output = capsys.readouterr().out
    assert "Role Radar — check" in output
    assert "Ready to run." in output


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

"""Tests for the role_radar CLI and I/O edges — offline (fetch/email mocked)."""

import zipfile

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

CONFIG_VARS = ["JOB_BOARD_URL", "JOB_TITLES", "EXCLUDE_TITLES", "JOB_ITEM_CLASS",
               "EMAIL_USER", "EMAIL_PASSWORD", "EMAIL_TO", "SMTP_HOST", "SMTP_PORT"]


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    """Keep every test off real files, real logging, and real env config."""
    monkeypatch.setattr(rr, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(rr, "SEEN_PATH", tmp_path / "seen.json")
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


# --- check (dry run) --------------------------------------------------------
def test_check_reports_without_sending_or_persisting(monkeypatch, capsys, tmp_path):
    _set_board(monkeypatch)
    sent = []
    monkeypatch.setattr(rr, "send_email", lambda *a, **k: sent.append(1))

    assert rr.main(["check"]) == 0
    out = capsys.readouterr().out
    assert "check (dry run)" in out
    assert "Senior Data Analyst" in out
    assert sent == []                              # nothing sent
    assert not (tmp_path / "seen.json").exists()   # state untouched


def test_check_does_not_require_email(monkeypatch):
    _set_board(monkeypatch)            # no EMAIL_USER / EMAIL_PASSWORD set
    assert rr.main(["check"]) == 0


# --- run --------------------------------------------------------------------
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
    assert rr.main(["run"]) == 0       # second run: nothing new
    assert sent == []


def test_run_missing_config_is_exit_2(monkeypatch):
    # No JOB_BOARD_URL / JOB_TITLES configured.
    assert rr.main(["run"]) == 2


def test_run_invalid_url_is_exit_2(monkeypatch):
    monkeypatch.setenv("JOB_BOARD_URL", "not-a-url")
    monkeypatch.setenv("JOB_TITLES", "analyst")
    _set_email(monkeypatch)

    assert rr.main(["run"]) == 2


def test_run_missing_smtp_host_is_exit_2(monkeypatch):
    _set_board(monkeypatch)
    _set_email(monkeypatch)
    monkeypatch.setenv("SMTP_HOST", "")

    assert rr.main(["run"]) == 2


def test_run_scrape_failure_is_exit_1_no_send(monkeypatch):
    monkeypatch.setenv("JOB_BOARD_URL", "https://example.com")
    monkeypatch.setenv("JOB_TITLES", "analyst")
    _set_email(monkeypatch)

    def boom(*a, **k):
        raise scraper.ScrapeError("network down")

    sent = []
    monkeypatch.setattr(scraper, "fetch_html", boom)
    monkeypatch.setattr(rr, "send_email", lambda *a, **k: sent.append(1))

    assert rr.main(["run"]) == 1       # no false success
    assert sent == []


def test_run_email_failure_is_exit_1_no_state(monkeypatch, tmp_path):
    _set_board(monkeypatch)
    _set_email(monkeypatch)

    def boom(*a, **k):
        raise mail.EmailError("smtp refused")

    monkeypatch.setattr(rr, "send_email", boom)

    assert rr.main(["run"]) == 1
    assert not (tmp_path / "seen.json").exists()   # state not advanced on failure


# --- config show ------------------------------------------------------------
def test_config_show_masks_password(monkeypatch, capsys):
    monkeypatch.setenv("JOB_BOARD_URL", "https://example.com")
    monkeypatch.setenv("JOB_TITLES", "analyst")
    monkeypatch.setenv("EMAIL_PASSWORD", "do-not-print-me")

    assert rr.main(["config", "show"]) == 0
    out = capsys.readouterr().out
    assert "do-not-print-me" not in out
    assert "set (hidden)" in out


def test_config_show_bad_port_is_exit_2(monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "not-a-number")
    assert rr.main(["config", "show"]) == 2


# --- seen list / reset ------------------------------------------------------
def test_seen_list_and_reset(monkeypatch, capsys, tmp_path):
    state.save_seen({"https://x/1", "https://x/2"}, tmp_path / "seen.json")

    assert rr.main(["seen", "list"]) == 0
    assert "2 role(s) remembered" in capsys.readouterr().out

    assert rr.main(["seen", "reset"]) == 0
    assert "Forgot 2" in capsys.readouterr().out
    assert state.load_seen(tmp_path / "seen.json") == set()


def test_top_level_reset_matches_seen_reset(monkeypatch, capsys, tmp_path):
    state.save_seen({"https://x/1"}, tmp_path / "seen.json")

    assert rr.main(["reset"]) == 0
    assert "Forgot 1" in capsys.readouterr().out
    assert state.load_seen(tmp_path / "seen.json") == set()


# --- titles -----------------------------------------------------------------
def test_titles_show(monkeypatch, capsys):
    monkeypatch.setenv("JOB_TITLES", "Senior Analyst, Data Analyst")

    assert rr.main(["titles", "show"]) == 0
    out = capsys.readouterr().out
    assert "Senior Analyst" in out
    assert "Data Analyst" in out


def test_titles_set_and_add(monkeypatch, tmp_path):
    assert rr.main(["titles", "set", "senior analyst, data analyst"]) == 0
    assert "JOB_TITLES=senior analyst, data analyst" in (tmp_path / ".env").read_text()

    assert rr.main(["titles", "add", "data analyst, marketing analyst"]) == 0
    env_text = (tmp_path / ".env").read_text()
    assert "JOB_TITLES=senior analyst, data analyst, marketing analyst" in env_text


# --- preview email ----------------------------------------------------------
def test_preview_email_writes_html_without_state_change(monkeypatch, tmp_path):
    preview_path = tmp_path / "preview.html"
    monkeypatch.setattr(rr, "PREVIEW_PATH", preview_path)

    assert rr.main(["preview-email"]) == 0
    html = preview_path.read_text()
    assert "Role Radar" in html
    assert "Senior Financial Analyst" in html
    assert not (tmp_path / "seen.json").exists()


def test_preview_email_real_uses_current_matches(monkeypatch, tmp_path):
    _set_board(monkeypatch)
    preview_path = tmp_path / "preview.html"
    monkeypatch.setattr(rr, "PREVIEW_PATH", preview_path)

    assert rr.main(["preview-email", "--real"]) == 0
    html = preview_path.read_text()
    assert "2 matching roles found" in html
    assert "Senior Data Analyst" in html
    assert not (tmp_path / "seen.json").exists()


# --- doctor / export --------------------------------------------------------
def test_doctor_passes_with_ready_config(monkeypatch, tmp_path):
    _set_board(monkeypatch)
    _set_email(monkeypatch)
    (tmp_path / ".env").write_text("JOB_BOARD_URL=https://example.com\n")
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(rr, "LOG_PATH", log_dir / "role_radar.log")

    assert rr.main(["doctor"]) == 0


def test_export_clean_excludes_local_runtime_files(tmp_path):
    output = tmp_path / "role-radar.zip"

    assert rr.main(["export-clean", "--output", str(output)]) == 0

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())

    assert "pyproject.toml" in names
    assert "src/role_radar/__main__.py" in names
    assert "src/role_radar/cli.py" in names
    assert not any(".egg-info/" in name for name in names)
    assert "src/role_radar/match.py" in names
    assert ".env" not in names
    assert not any(name.startswith(".git/") for name in names)
    assert not any(name.startswith(".venv/") for name in names)
    assert not any(name.startswith("__pycache__/") for name in names)
    assert not any(name.startswith("data/") for name in names)
    assert not any(name.startswith("logs/") for name in names)


# --- version ----------------------------------------------------------------
def test_version_subcommand(capsys):
    assert rr.main(["version"]) == 0
    assert "role-radar" in capsys.readouterr().out


def test_version_flag_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        rr.main(["--version"])
    assert exc.value.code == 0
    assert "role-radar" in capsys.readouterr().out


# --- usage errors -----------------------------------------------------------
def test_no_command_is_usage_error():
    with pytest.raises(SystemExit) as exc:
        rr.main([])
    assert exc.value.code == 2


def test_unknown_command_is_usage_error():
    with pytest.raises(SystemExit) as exc:
        rr.main(["bogus"])
    assert exc.value.code == 2

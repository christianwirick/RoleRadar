"""Tests for production runtime paths."""

from pathlib import Path

from role_radar import cli


def test_runtime_paths_live_outside_repo():
    expected = Path.home() / ".config" / "RoleRadar"

    assert cli.APP_DIR == expected
    assert cli.ENV_PATH == expected / ".env"
    assert cli.SEEN_PATH == expected / "seen_jobs.json"
    assert cli.LOG_PATH == expected / "role_radar.log"

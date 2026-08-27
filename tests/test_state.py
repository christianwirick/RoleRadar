"""Tests for seen-role state."""

import pytest

from role_radar import state


def test_format_seen_list():
    assert "No roles remembered" in state.format_seen_list(set())
    out = state.format_seen_list({"u2", "u1"})
    assert "2 role(s) remembered" in out
    assert out.index("u1") < out.index("u2")


def test_seen_roundtrip(tmp_path):
    p = tmp_path / "seen.json"
    state.save_seen({"a", "b"}, p)
    assert state.load_seen(p) == {"a", "b"}


def test_load_seen_missing_file_is_empty(tmp_path):
    assert state.load_seen(tmp_path / "nope.json") == set()


def test_load_seen_corrupt_file_is_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ not json")
    assert state.load_seen(p) == set()


def test_save_seen_is_atomic_no_tmp_left(tmp_path):
    p = tmp_path / "seen.json"
    state.save_seen({"x"}, p)
    assert p.exists()
    assert not (tmp_path / "seen.json.tmp").exists()


def test_save_seen_unwritable_raises_state_error(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    with pytest.raises(state.StateError):
        state.save_seen({"a"}, blocker / "sub" / "seen.json")

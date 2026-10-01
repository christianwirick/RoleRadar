"""Tests for terminal status messaging."""

from role_radar import out


def test_status_message_groups_are_complete():
    assert set(out.STATUS_MESSAGES) == {"scan", "match", "new", "finish"}
    assert all(len(messages) == 15 for messages in out.STATUS_MESSAGES.values())


def test_status_prints_selected_message(monkeypatch, capsys):
    monkeypatch.setattr(out.random, "choice", lambda choices: choices[0])

    selected = out.status("scan")

    assert selected == "Sweeping the radar..."
    assert "Sweeping the radar..." in capsys.readouterr().out


def test_pulse_does_not_repeat_previous_message(monkeypatch):
    pulse = out.Pulse("scan", "done")
    pulse._last_message = out.STATUS_MESSAGES["scan"][0]
    monkeypatch.setattr(out.random, "choice", lambda choices: choices[0])

    selected = pulse._pick()

    assert selected != pulse._last_message or selected != out.STATUS_MESSAGES["scan"][0]
    assert selected == out.STATUS_MESSAGES["scan"][1]

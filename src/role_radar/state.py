"""Seen-role state storage."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .out import short_error

log = logging.getLogger("role_radar.state")


class StateError(Exception):
    """The seen-jobs state file could not be written."""


def load_seen(path: Path) -> set[str]:
    """Load the set of seen role keys.

    A missing file is normal on first run. A corrupt or unreadable file is
    non-fatal: warn and start fresh rather than block an alert run (the cost
    is at most re-alerting current roles, never a crash).
    """
    path = Path(path)
    try:
        data = json.loads(path.read_text())
        return set(data.get("seen", []))
    except FileNotFoundError:
        return set()
    except (json.JSONDecodeError, OSError) as err:
        log.warning("Could not read state %s (%s); starting fresh.",
                    path, short_error(err))
        return set()


def save_seen(seen: set[str], path: Path) -> None:
    """Persist seen keys, writing to a temp file then renaming.

    The write-then-rename keeps the live state file intact if the process is
    interrupted mid-write.
    """
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps({"seen": sorted(seen)}, indent=2))
        tmp.replace(path)  # atomic on the same filesystem
    except OSError as err:
        raise StateError(f"Could not write state file {path}: {short_error(err)}")


def format_seen_list(seen: set[str]) -> str:
    if not seen:
        return "No roles remembered yet."
    keys = sorted(seen)
    return "\n".join([f"{len(keys)} role(s) remembered:"] + [f"  {k}" for k in keys])

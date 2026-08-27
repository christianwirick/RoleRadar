"""Terminal output and logging helpers."""

from __future__ import annotations

import itertools
import logging
import os
import sys
import threading
import time
from pathlib import Path


def short_error(err: object, limit: int = 200) -> str:
    """Collapse an exception to a single trimmed line for logs and messages.

    Keeps a full traceback from flooding user-facing output.
    """
    if not err:
        return ""
    return str(err).strip().splitlines()[0][:limit]


def _style(code: str) -> str:
    # Drop ANSI codes when output is redirected/piped or NO_COLOR is set.
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return ""
    return code


_BOLD = _style("\033[1m")
_DIM = _style("\033[2m")
_GREEN = _style("\033[32m")
_BLUE = _style("\033[34m")
_YELLOW = _style("\033[33m")
_RESET = _style("\033[0m")


def say(message: str = "") -> None:
    print(message, flush=True)


def header(title: str) -> None:
    say()
    say(f"{_BOLD}{title}{_RESET}")
    say(f"{_DIM}{'─' * len(title)}{_RESET}")


def ok(message: str) -> None:
    say(f"{_GREEN}✓{_RESET} {message}")


def info(message: str) -> None:
    say(f"{_BLUE}•{_RESET} {message}")


def warn(message: str) -> None:
    say(f"{_YELLOW}!{_RESET} {message}")


class Pulse:
    """Context manager that prints periodic "still working" ticks.

    A daemon thread emits progress lines every ``interval`` seconds during a
    long step (e.g. the scrape) and reports elapsed time on clean exit.
    """

    phrases = (
        "Scanning the board...",
        "Still hunting...",
        "Reading every listing...",
        "Almost through the stack...",
    )

    def __init__(self, label: str, done_label: str, interval: int = 5) -> None:
        self.label = label
        self.done_label = done_label
        self.interval = interval
        self.started = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self):
        self.started = time.monotonic()
        info(self.label)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop.set()
        self._thread.join(timeout=0.2)

        if exc_type is None:
            elapsed = time.monotonic() - self.started
            ok(f"{self.done_label} in {elapsed:.1f}s.")

        return False

    def _run(self) -> None:
        for phrase in itertools.cycle(self.phrases):
            if self._stop.wait(self.interval):
                return
            elapsed = time.monotonic() - self.started
            say(f"{_DIM}  {phrase} ({elapsed:.0f}s){_RESET}")


def setup_logging(log_path: Path) -> None:
    """Log INFO+ to the file and WARNING+ to stderr, keeping stdout for results."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    file_handler.setLevel(logging.INFO)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    console.setLevel(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers[:] = [file_handler, console]

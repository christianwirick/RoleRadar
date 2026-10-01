"""Terminal output and logging helpers."""

from __future__ import annotations

import logging
import os
import random
import sys
import threading
import time
from pathlib import Path

STATUS_MESSAGES = {
    "scan": (
        "Sweeping the radar...",
        "Scanning the job boards...",
        "Seeing what just dropped...",
        "Checking what the internet cooked up...",
        "Peeking at the latest roles...",
        "Doing a little job-market lurking...",
        "Seeing who is hiring rn...",
        "Checking for fresh drops...",
        "Poking around the job market...",
        "Looking for something kinda perfect...",
        "Seeing what is hiding out there...",
        "Giving the radar a spin...",
        "Checking the career group chat...",
        "Seeing what just hit the market...",
        "Doing some professional snooping...",
    ),
    "match": (
        "Filtering out the meh...",
        "Keeping the good stuff...",
        "Finding the roles that actually matter...",
        "Separating signal from corporate noise...",
        "Checking the vibes...",
        "Looking for main-character opportunities...",
        "Cutting the filler...",
        "Finding the ones worth opening...",
        "Removing the absolutely nots...",
        "Looking for suspiciously good matches...",
        "Checking if the titles pass the vibe check...",
        "Trimming the job-board chaos...",
        "Keeping only the interesting ones...",
        "Finding roles with potential...",
        "Making the algorithm earn its keep...",
    ),
    "new": (
        "Checking if we have seen these before...",
        "Looking for fresh faces...",
        "Seeing what is actually new...",
        "Checking for new lore...",
        "Removing the reruns...",
        "Looking for fresh signals...",
        "Seeing who entered the chat...",
        "Checking what changed while you were gone...",
        "Looking for the new-new...",
        "Skipping the déjà vu...",
        "Seeing what just joined the party...",
        "Checking for unexpected plot twists...",
        "Looking for roles you have not stalked yet...",
        "Seeing if anything new popped off...",
        "Checking for fresh career content...",
    ),
    "finish": (
        "Putting the good ones in a neat little pile...",
        "Making one last sweep...",
        "Giving the radar one more spin...",
        "Collecting the finalists...",
        "Getting the good stuff ready...",
        "Doing the final vibe check...",
        "Putting the shortlist together...",
        "Making sure we did not miss a banger...",
        "Wrapping up the career reconnaissance...",
        "Bringing the best matches home...",
        "Checking under one last rock...",
        "Finishing the job-market side quest...",
        "Polishing the shortlist...",
        "Getting your career loot together...",
        "Preparing the reveal...",
    ),
}


def short_error(err: object, limit: int = 200) -> str:
    """Collapse an exception to one trimmed line for logs and messages."""
    if not err:
        return ""
    return str(err).strip().splitlines()[0][:limit]


def _style(code: str) -> str:
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


def status(kind: str) -> str:
    """Print and return one status message from the requested pool."""
    message = random.choice(STATUS_MESSAGES[kind])
    info(message)
    return message


class Pulse:
    """Print rotating status messages while a long step is running."""

    def __init__(
        self,
        kind: str,
        done_label: str,
        interval: int = 5,
    ) -> None:
        if kind not in STATUS_MESSAGES:
            raise ValueError(f"Unknown status kind: {kind}")
        self.kind = kind
        self.done_label = done_label
        self.interval = interval
        self.started = 0.0
        self._last_message = ""
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self):
        self.started = time.monotonic()
        self._emit()
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop.set()
        self._thread.join(timeout=0.2)

        if exc_type is None:
            elapsed = time.monotonic() - self.started
            ok(f"{self.done_label} in {elapsed:.1f}s.")

        return False

    def _pick(self) -> str:
        choices = STATUS_MESSAGES[self.kind]
        if len(choices) == 1:
            return choices[0]

        available = tuple(message for message in choices if message != self._last_message)
        message = random.choice(available)
        self._last_message = message
        return message

    def _emit(self) -> None:
        info(self._pick())

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            elapsed = time.monotonic() - self.started
            say(f"{_DIM}  {self._pick()} ({elapsed:.0f}s){_RESET}")


def setup_logging(log_path: Path) -> None:
    """Log INFO+ to file and WARNING+ to stderr; keep stdout for results."""
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    file_handler.setLevel(logging.INFO)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers[:] = [file_handler, console]

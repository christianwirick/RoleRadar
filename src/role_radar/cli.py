"""Command-line interface for Role Radar."""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from . import match, out, scraper
from .config import ConfigError, format_config, require_config, resolve_config
from .mail import EmailError, format_email_body, format_email_html, send_email
from .models import AppConfig
from .state import StateError, format_seen_list, load_seen, save_seen

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_PATH = PROJECT_ROOT / ".env"
LOG_PATH = PROJECT_ROOT / "logs" / "role_radar.log"
SEEN_PATH = PROJECT_ROOT / "data" / "seen_jobs.json"

log = logging.getLogger("role_radar")


def cmd_run(*, dry_run: bool = False) -> int:
    """Scan the board; optionally send and save new matches."""
    started = time.monotonic()
    mode = "test" if dry_run else "run"

    out.header(f"Role Radar — {mode}")
    out.info("Loading settings...")
    cfg = resolve_config(ENV_PATH)
    require_config(cfg, ENV_PATH, require_email=not dry_run)
    out.ok("Settings locked.")

    log.info("Role Radar starting: %s.", "test" if dry_run else "run")
    out.info(f"Watching: {', '.join(cfg.keywords)}")
    out.info(f"Board: {cfg.url}")

    with out.Pulse("Opening the board...", "Board loaded"):
        all_jobs, matched = scraper.scan_board(cfg)

    out.info("Reading roles...")
    out.ok(f"Scraped {len(all_jobs)} listing(s).")

    out.info("Matching titles...")
    out.ok(f"Matched {len(matched)} listing(s).")

    out.info("Checking what’s new...")
    seen = load_seen(SEEN_PATH)
    fresh = match.select_new(matched, seen)
    out.ok(f"Found {len(fresh)} new role(s).")

    log.info(
        "Scraped %d · matched %d · new %d.",
        len(all_jobs),
        len(matched),
        len(fresh),
    )

    out.header("Results")

    if dry_run:
        print(match.format_test_report(len(all_jobs), len(matched), fresh))
        out.ok(f"Done in {time.monotonic() - started:.1f}s.")
        return 0

    if not fresh:
        log.info("Nothing new to send.")
        out.warn("No new roles to email.")
        out.ok(f"Done in {time.monotonic() - started:.1f}s.")
        return 0

    with out.Pulse(f"Sending alert to {cfg.email_to}...", "Email sent"):
        send_email(
            cfg,
            f"Role Radar: {len(fresh)} new role(s) found",
            format_email_body(fresh),
            format_email_html(fresh),
        )

    log.info("Email sent to %s with %d role(s).", cfg.email_to, len(fresh))

    out.info("Remembering sent roles...")
    seen.update(job.key for job in fresh)
    save_seen(seen, SEEN_PATH)
    log.info("State updated; remembering %d role(s).", len(seen))

    out.ok(f"Emailed {len(fresh)} new role(s) to {cfg.email_to}.")
    out.ok(f"Done in {time.monotonic() - started:.1f}s.")
    return 0


def cmd_conf() -> int:
    """Print resolved configuration with the password hidden."""
    print(format_config(resolve_config(ENV_PATH)))
    return 0


def cmd_jobs() -> int:
    """List jobs that Role Radar already remembers."""
    print(format_seen_list(load_seen(SEEN_PATH)))
    return 0


def cmd_reset() -> int:
    """Forget all saved job state."""
    count = len(load_seen(SEEN_PATH))
    save_seen(set(), SEEN_PATH)
    print(f"Forgot {count} remembered role(s). State cleared.")
    return 0


def cmd_clear() -> int:
    """Clear the terminal screen."""
    print("\033[2J\033[H", end="", flush=True)
    return 0


def _check_rows(cfg: AppConfig) -> tuple[list[str], list[str]]:
    ok = []
    issues = []

    if ENV_PATH.exists():
        ok.append(f".env found at {ENV_PATH}")
    else:
        issues.append(f".env missing. Create or link {ENV_PATH.name}.")

    try:
        require_config(cfg, ENV_PATH, require_email=True)
        ok.append("Required run configuration is present.")
    except ConfigError as err:
        issues.append(str(err))

    if cfg.email_password:
        ok.append("EMAIL_PASSWORD is set and hidden from output.")

    for label, path in (("State", SEEN_PATH.parent), ("Log", LOG_PATH.parent)):
        if path.is_dir():
            ok.append(f"{label} folder ready: {path}")
        else:
            issues.append(f"{label} folder missing: {path}")

    try:
        __import__("selenium")
        ok.append("Selenium is installed.")
    except ImportError:
        issues.append("Selenium is not installed. Run: make setup")

    return ok, issues


def cmd_check() -> int:
    """Validate local configuration and dependencies."""
    out.header("Role Radar — check")
    cfg = resolve_config(ENV_PATH)
    ok, issues = _check_rows(cfg)

    for row in ok:
        out.ok(row)
    for row in issues:
        out.warn(row)

    if issues:
        out.warn("Check found setup issues.")
        return 2

    out.ok("Ready to run.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rr",
        description="Watch a job board and email new matching roles.",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    test_parser = sub.add_parser("test", help="Scan without email or state changes.")
    test_parser.set_defaults(handler=lambda _args: cmd_run(dry_run=True))

    check_parser = sub.add_parser("check", help="Validate local setup.")
    check_parser.set_defaults(handler=lambda _args: cmd_check())

    run_parser = sub.add_parser("run", help="Scan, email new matches, and save state.")
    run_parser.set_defaults(handler=lambda _args: cmd_run())

    re_parser = sub.add_parser("re", help="Run Role Radar again.")
    re_parser.set_defaults(handler=lambda _args: cmd_run())

    clear_parser = sub.add_parser("clear", help="Clear the terminal screen.")
    clear_parser.set_defaults(handler=lambda _args: cmd_clear())

    jobs_parser = sub.add_parser("jobs", help="Show remembered jobs.")
    jobs_parser.set_defaults(handler=lambda _args: cmd_jobs())

    conf_parser = sub.add_parser("conf", help="Show resolved configuration.")
    conf_parser.set_defaults(handler=lambda _args: cmd_conf())

    reset_parser = sub.add_parser("reset", help="Forget all remembered jobs.")
    reset_parser.set_defaults(handler=lambda _args: cmd_reset())

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command in {"test", "run", "re"}:
        out.setup_logging(LOG_PATH)

    try:
        return args.handler(args)
    except ConfigError as err:
        log.error("Configuration error: %s", err)
        return 2
    except scraper.ScrapeError as err:
        log.error("Scrape failed: %s", err)
        return 1
    except EmailError as err:
        log.error("Email failed: %s", err)
        return 1
    except StateError as err:
        log.error("File error: %s", err)
        return 1
    except Exception as err:
        log.exception("Unexpected error: %s", err)
        return 1

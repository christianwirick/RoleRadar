"""Command-line interface for Role Radar."""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from . import __version__, match, out, pack, scraper
from .config import ConfigError, format_config, require_config, resolve_config
from .mail import EmailError, format_email_body, format_email_html, send_email
from .models import AppConfig, JobListing
from .state import StateError, format_seen_list, load_seen, save_seen

# All paths are resolved relative to this file so the CLI behaves the same
# from any working directory (e.g. when launched from cron).
PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_PATH = PROJECT_ROOT / ".env"
LOG_PATH = PROJECT_ROOT / "logs" / "role_radar.log"
SEEN_PATH = PROJECT_ROOT / "data" / "seen_jobs.json"
PREVIEW_PATH = PROJECT_ROOT / "data" / "email_preview.html"
EXPORT_PATH = PROJECT_ROOT / "dist" / "role-radar-clean.zip"

log = logging.getLogger("role_radar")

# Sample data so `preview-email` renders without scraping or credentials.
PREVIEW_JOBS = [
    JobListing(
        title="Senior Financial Analyst",
        url="https://careers.example.com/senior-financial-analyst",
        property_name="Lakeside Resort",
    ),
    JobListing(
        title="Data Analyst",
        url="https://careers.example.com/data-analyst",
        property_name="Corporate Analytics",
    ),
    JobListing(
        title="Marketing Analyst",
        url="https://careers.example.com/marketing-analyst",
        property_name="Regional Marketing",
    ),
]


def cmd_run(dry_run: bool) -> int:
    """Scrape, match, and report new roles.

    Backs both `run` and `check`. In dry_run mode it stops after printing the
    report — no email is sent and seen-role state is left untouched.
    """
    started = time.monotonic()
    mode = "check" if dry_run else "run"

    out.header(f"Role Radar — {mode}")
    out.info("Loading settings...")
    cfg = resolve_config(ENV_PATH)
    require_config(cfg, ENV_PATH, require_email=not dry_run)
    out.ok("Settings locked.")

    log.info("Role Radar starting: %s.", "check (dry run)" if dry_run else "run")
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

    log.info("Scraped %d · matched %d · new %d.",
             len(all_jobs), len(matched), len(fresh))

    out.header("Results")

    if dry_run:
        print(match.format_check_report(len(all_jobs), len(matched), fresh))
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
    # Only record roles as seen after a successful send, so a failed email
    # does not silently suppress the next alert.
    out.info("Remembering sent roles...")
    seen.update(job.key for job in fresh)
    save_seen(seen, SEEN_PATH)
    log.info("State updated; remembering %d role(s).", len(seen))

    out.ok(f"Emailed {len(fresh)} new role(s) to {cfg.email_to}.")
    out.ok(f"Done in {time.monotonic() - started:.1f}s.")
    return 0


def cmd_config_show() -> int:
    print(format_config(resolve_config(ENV_PATH)))
    return 0


def _write_env_value(key: str, value: str) -> None:
    """Set one key in .env in place, preserving all other lines and comments."""
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    new_line = f"{key}={value}"

    output = []
    replaced = False
    for line in lines:
        if line.startswith(f"{key}="):
            output.append(new_line)
            replaced = True
        else:
            output.append(line)

    if not replaced:
        output.append(new_line)

    ENV_PATH.write_text("\n".join(output) + "\n")


def _normalize_titles(raw: str) -> list[str]:
    """Split a comma list into trimmed, lowercased titles, de-duped in order."""
    seen = set()
    titles = []

    for part in raw.split(","):
        title = " ".join(part.strip().split()).lower()
        if title and title not in seen:
            seen.add(title)
            titles.append(title)

    return titles


def cmd_titles_set(raw_titles: str) -> int:
    titles = _normalize_titles(raw_titles)
    if not titles:
        raise ConfigError("Provide at least one job title.")

    _write_env_value("JOB_TITLES", ", ".join(titles))
    print("Updated JOB_TITLES:")
    for title in titles:
        print(f"  - {title}")
    return 0


def cmd_titles_add(raw_titles: str) -> int:
    cfg = resolve_config(ENV_PATH)
    added = _normalize_titles(raw_titles)
    combined = _normalize_titles(", ".join(list(cfg.keywords) + added))

    if not combined:
        raise ConfigError("Provide at least one job title.")

    _write_env_value("JOB_TITLES", ", ".join(combined))
    print("Updated JOB_TITLES:")
    for title in combined:
        print(f"  - {title}")
    return 0


def cmd_titles_show() -> int:
    titles = resolve_config(ENV_PATH).keywords
    if not titles:
        print("No watched titles configured.")
        return 0

    print("Watched titles:")
    for title in titles:
        print(f"  - {title}")
    return 0


def cmd_seen_list() -> int:
    print(format_seen_list(load_seen(SEEN_PATH)))
    return 0


def cmd_seen_reset() -> int:
    count = len(load_seen(SEEN_PATH))
    save_seen(set(), SEEN_PATH)
    print(f"Forgot {count} remembered role(s). State cleared.")
    return 0


def cmd_version() -> int:
    print(f"role-radar {__version__}")
    return 0


def cmd_preview_email(real: bool = False) -> int:
    """Write an HTML email preview to disk without sending or touching state.

    With real=True it scrapes the live board for current matches; otherwise it
    renders the built-in sample jobs.
    """
    if real:
        out.header("Role Radar — preview email")
        out.info("Loading settings...")
        cfg = resolve_config(ENV_PATH)
        require_config(cfg, ENV_PATH, require_email=False)
        out.ok("Settings locked.")

        with out.Pulse("Opening the board...", "Board loaded"):
            _all_jobs, jobs = scraper.scan_board(cfg)

        out.ok(f"Using {len(jobs)} current matched role(s).")
        html = format_email_html(jobs, status_label="matching")
    else:
        html = format_email_html(PREVIEW_JOBS)

    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote email preview: {PREVIEW_PATH}")
    return 0


def _doctor_rows(cfg: AppConfig) -> tuple[list[str], list[str]]:
    ok = []
    issues = []

    if ENV_PATH.exists():
        ok.append(f".env found at {ENV_PATH}")
    else:
        issues.append(f".env missing. Copy .env.example to {ENV_PATH.name}.")

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
        issues.append("Selenium is not installed. Install with: pip install -e '.[dev]'")

    return ok, issues


def cmd_doctor() -> int:
    out.header("Role Radar — doctor")
    cfg = resolve_config(ENV_PATH)
    ok, issues = _doctor_rows(cfg)

    for row in ok:
        out.ok(row)
    for row in issues:
        out.warn(row)

    if issues:
        out.warn("Doctor found setup issues.")
        return 2

    out.ok("Ready to run.")
    return 0


def cmd_export_clean(output: str | None = None) -> int:
    # A relative --output is resolved under the project dir, not the CWD.
    output_path = Path(output).expanduser() if output else EXPORT_PATH
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    written = pack.export_clean(PROJECT_ROOT, output_path)
    print(f"Wrote clean export: {output_path}")
    print(f"Included {written} file(s).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="role-radar",
        description="Watch a job board and email new matching roles.",
    )
    parser.add_argument("--version", action="version",
                        version=f"role-radar {__version__}")

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    run_parser = sub.add_parser("run", help="Scrape, email, and save state.")
    run_parser.set_defaults(handler=lambda _args: cmd_run(dry_run=False))

    check_parser = sub.add_parser("check", help="Dry run with no email or save.")
    check_parser.set_defaults(handler=lambda _args: cmd_run(dry_run=True))

    reset_parser = sub.add_parser("reset", help="Forget all remembered roles.")
    reset_parser.set_defaults(handler=lambda _args: cmd_seen_reset())

    doctor_parser = sub.add_parser("doctor", help="Validate local setup.")
    doctor_parser.set_defaults(handler=lambda _args: cmd_doctor())

    config_parser = sub.add_parser("config", help="Inspect configuration.")
    config_sub = config_parser.add_subparsers(dest="action", metavar="<action>")
    config_sub.required = True
    config_show = config_sub.add_parser("show", help="Print masked config.")
    config_show.set_defaults(handler=lambda _args: cmd_config_show())

    seen_parser = sub.add_parser("seen", help="Inspect or reset seen roles.")
    seen_sub = seen_parser.add_subparsers(dest="action", metavar="<action>")
    seen_sub.required = True
    seen_list = seen_sub.add_parser("list", help="List remembered roles.")
    seen_list.set_defaults(handler=lambda _args: cmd_seen_list())
    seen_reset = seen_sub.add_parser("reset", help="Forget remembered roles.")
    seen_reset.set_defaults(handler=lambda _args: cmd_seen_reset())

    titles_parser = sub.add_parser("titles", help="Manage watched titles.")
    titles_sub = titles_parser.add_subparsers(dest="action", metavar="<action>")
    titles_sub.required = True

    titles_show = titles_sub.add_parser("show", help="Print watched titles.")
    titles_show.set_defaults(handler=lambda _args: cmd_titles_show())

    titles_set = titles_sub.add_parser("set", help="Replace watched titles.")
    titles_set.add_argument("titles", help="Comma-separated job titles.")
    titles_set.set_defaults(handler=lambda args: cmd_titles_set(args.titles))

    titles_add = titles_sub.add_parser("add", help="Append watched titles.")
    titles_add.add_argument("titles", help="Comma-separated job titles.")
    titles_add.set_defaults(handler=lambda args: cmd_titles_add(args.titles))

    preview = sub.add_parser("preview-email", help="Write an HTML email preview.")
    preview.add_argument("--real", action="store_true",
                         help="Preview current matched jobs from the live board.")
    preview.set_defaults(handler=lambda args: cmd_preview_email(args.real))

    export = sub.add_parser("export-clean", help="Write a safe share zip.")
    export.add_argument("--output",
                        help=f"Zip path (default: {EXPORT_PATH.relative_to(PROJECT_ROOT)}).")
    export.set_defaults(handler=lambda args: cmd_export_clean(args.output))

    version = sub.add_parser("version", help="Print version.")
    version.set_defaults(handler=lambda _args: cmd_version())
    return parser


def main(argv: list[str] | None = None) -> int:
    # Only the commands that scrape or send touch the log file; the rest stay
    # quiet so inspection commands don't create log noise.
    args = build_parser().parse_args(argv)

    if args.command in ("run", "check") or (
        args.command == "preview-email" and getattr(args, "real", False)
    ):
        out.setup_logging(LOG_PATH)

    # Map known failure types to documented exit codes (2 = config/usage,
    # 1 = runtime failure); anything unexpected is logged with a traceback.
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
    except (StateError, pack.PackError) as err:
        log.error("File error: %s", err)
        return 1
    except Exception as err:
        log.exception("Unexpected error: %s", err)
        return 1

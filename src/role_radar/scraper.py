"""Job board scraping and browser diagnostics."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

from . import match
from .models import AppConfig, JobListing
from .out import short_error

RENDER_TIMEOUT = 30
FETCH_RETRIES = 3
RETRY_BACKOFF = 5
STABLE_POLLS = 4
STABLE_POLL_INTERVAL = 0.75

log = logging.getLogger("role_radar.scraper")


class ScrapeError(Exception):
    """The browser or job board could not be used."""


@dataclass(frozen=True)
class BrowserStatus:
    """Details from a successful Chrome/ChromeDriver launch."""

    browser_version: str
    driver_version: str
    driver_path: str


def _chrome_options():
    from selenium.webdriver.chrome.options import Options

    options = Options()
    for arg in (
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ):
        options.add_argument(arg)
    return options


def check_browser() -> BrowserStatus:
    """Launch headless Chrome and return detected browser/driver details."""
    try:
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException
    except ImportError as err:
        raise ScrapeError("Selenium is not installed. Run: make setup") from err

    driver_path = os.getenv("SE_CHROMEDRIVER", "").strip()
    if driver_path:
        path = Path(driver_path).expanduser()
        if not path.is_file():
            raise ScrapeError(f"SE_CHROMEDRIVER does not exist: {path}")
        if not os.access(path, os.X_OK):
            raise ScrapeError(f"SE_CHROMEDRIVER is not executable: {path}")

    try:
        with webdriver.Chrome(options=_chrome_options()) as driver:
            driver.get("data:text/html,<title>RoleRadar check</title>")
            caps = driver.capabilities
            browser_version = str(caps.get("browserVersion", "unknown"))
            chrome_caps = caps.get("chrome", {})
            driver_version = str(chrome_caps.get("chromedriverVersion", "")).split(" ")[0]
            resolved_driver_path = driver_path or str(getattr(driver.service, "path", "") or "")
            return BrowserStatus(
                browser_version=browser_version,
                driver_version=driver_version,
                driver_path=resolved_driver_path,
            )
    except WebDriverException as err:
        raise ScrapeError(
            "Chrome/ChromeDriver launch failed: "
            f"{short_error(err)}"
        ) from err


def _wait_for_stable_listings(
    driver,
    item_class: str,
    *,
    timeout: float = RENDER_TIMEOUT,
    stable_polls: int = STABLE_POLLS,
    poll_interval: float = STABLE_POLL_INTERVAL,
) -> int:
    """Wait until the number of rendered listings stops changing."""
    from selenium.webdriver.common.by import By

    deadline = time.monotonic() + timeout
    last_count = -1
    stable_count = 0

    while time.monotonic() < deadline:
        count = len(driver.find_elements(By.CLASS_NAME, item_class))

        if count > 0 and count == last_count:
            stable_count += 1
            if stable_count >= stable_polls:
                return count
        else:
            stable_count = 0
            last_count = count

        time.sleep(poll_interval)

    raise ScrapeError(
        f"Job listings did not finish loading within {timeout:.0f}s "
        f"(last count: {max(last_count, 0)})."
    )


def fetch_html(
    url: str,
    item_class: str,
    timeout: int = RENDER_TIMEOUT,
    retries: int = FETCH_RETRIES,
) -> str:
    """Return rendered HTML after the listing count becomes stable."""
    try:
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException
    except ImportError as err:
        raise ScrapeError("Selenium is not installed. Run: make setup") from err

    last_err: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            with webdriver.Chrome(options=_chrome_options()) as driver:
                driver.get(url)
                count = _wait_for_stable_listings(
                    driver,
                    item_class,
                    timeout=timeout,
                )
                log.info("Rendered listing count stabilized at %d.", count)
                return driver.page_source
        except (WebDriverException, ScrapeError) as err:
            last_err = err
            log.warning(
                "Fetch attempt %d/%d failed: %s",
                attempt,
                retries,
                short_error(err),
            )
            if attempt < retries:
                time.sleep(RETRY_BACKOFF * attempt)

    raise ScrapeError(
        f"Could not fetch job board after {retries} attempts: "
        f"{short_error(last_err)}"
    )


def scan_board(cfg: AppConfig) -> tuple[list[JobListing], list[JobListing]]:
    """Fetch the board and return all jobs plus jobs matching the filters."""
    html = fetch_html(cfg.url, cfg.item_class)
    all_jobs = match.extract_jobs(html, cfg.item_class)
    matched = match.filter_jobs(all_jobs, cfg.keywords, cfg.exclude)
    return all_jobs, matched

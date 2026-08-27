"""Job board scraping.

Assumes a JavaScript-rendered board: the page is loaded in headless Chrome
and we wait for the title elements (``item_class``) to appear before reading
the DOM. A board that serves static HTML would only need this module changed.
"""

from __future__ import annotations

import logging
import time

from . import match
from .models import AppConfig, JobListing
from .out import short_error

RENDER_TIMEOUT = 10
FETCH_RETRIES = 3
RETRY_BACKOFF = 5

log = logging.getLogger("role_radar.scraper")


class ScrapeError(Exception):
    """The job board could not be fetched."""


def fetch_html(url: str,
               item_class: str,
               timeout: int = RENDER_TIMEOUT,
               retries: int = FETCH_RETRIES) -> str:
    """Return the rendered page source, retrying transient driver failures.

    Selenium is imported lazily so non-scraping commands (and the offline
    test suite) run without a browser or driver installed.
    """
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    options = Options()
    for arg in ("--headless=new", "--disable-gpu", "--no-sandbox",
                "--disable-dev-shm-usage"):
        options.add_argument(arg)

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            with webdriver.Chrome(options=options) as driver:
                driver.get(url)
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CLASS_NAME, item_class))
                )
                return driver.page_source
        except WebDriverException as err:
            last_err = err
            log.warning("Fetch attempt %d/%d failed: %s",
                        attempt, retries, short_error(err))
            if attempt < retries:
                time.sleep(RETRY_BACKOFF * attempt)  # linear backoff

    raise ScrapeError(
        f"Could not fetch job board after {retries} attempts: "
        f"{short_error(last_err)}"
    )


def scan_board(cfg: AppConfig) -> tuple[list[JobListing], list[JobListing]]:
    """Fetch the board and return (all scraped jobs, jobs matching filters)."""
    html = fetch_html(cfg.url, cfg.item_class)
    all_jobs = match.extract_jobs(html, cfg.item_class)
    matched = match.filter_jobs(all_jobs, cfg.keywords, cfg.exclude)
    return all_jobs, matched

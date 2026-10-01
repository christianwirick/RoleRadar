"""Tests for browser diagnostics and rendered-list stabilization."""

import pytest

from role_radar import scraper


class FakeDriver:
    def __init__(self, counts):
        self._counts = iter(counts)
        self._last = 0

    def find_elements(self, _by, _item_class):
        try:
            self._last = next(self._counts)
        except StopIteration:
            pass
        return [object()] * self._last


def test_wait_for_stable_listings_waits_for_same_nonzero_count():
    driver = FakeDriver([0, 2, 4, 4, 4, 4])

    count = scraper._wait_for_stable_listings(
        driver,
        "vizi-item-title",
        timeout=1,
        stable_polls=3,
        poll_interval=0,
    )

    assert count == 4


def test_wait_for_stable_listings_times_out_without_jobs():
    driver = FakeDriver([0])

    with pytest.raises(scraper.ScrapeError, match="did not finish loading"):
        scraper._wait_for_stable_listings(
            driver,
            "vizi-item-title",
            timeout=0.001,
            stable_polls=2,
            poll_interval=0,
        )


def test_check_browser_rejects_missing_explicit_driver(monkeypatch, tmp_path):
    missing = tmp_path / "chromedriver"
    monkeypatch.setenv("SE_CHROMEDRIVER", str(missing))

    with pytest.raises(scraper.ScrapeError, match="does not exist"):
        scraper.check_browser()

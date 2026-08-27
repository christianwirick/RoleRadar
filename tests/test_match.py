"""Tests for job matching and reports."""

from role_radar import match
from role_radar.models import JobListing

SAMPLE_HTML = """
<html><body>
  <a href="https://jobs.example.com/1"><h3 class="vizi-item-title">Senior Data Analyst</h3></a>
  <a href="https://jobs.example.com/2"><h3 class="vizi-item-title">IT Support Analyst</h3></a>
  <a href="https://jobs.example.com/3"><h3 class="vizi-item-title">Marketing Manager</h3></a>
  <h3 class="vizi-item-title">Analytics Lead (no link)</h3>
</body></html>
"""


def test_extract_jobs_returns_all_titles_and_urls():
    jobs = match.extract_jobs(SAMPLE_HTML, "vizi-item-title")
    assert [job.title for job in jobs] == [
        "Senior Data Analyst",
        "IT Support Analyst",
        "Marketing Manager",
        "Analytics Lead (no link)",
    ]
    assert jobs[0].url == "https://jobs.example.com/1"
    assert jobs[3].url == ""


def test_property_from_vizi_url():
    url = "https://vizi.vizirecruiter.com/M-Resort-4403/393463/index.html"
    assert match.property_from_url(url) == "M Resort"


def test_filter_matches_keyword_case_insensitive():
    jobs = match.extract_jobs(SAMPLE_HTML, "vizi-item-title")
    titles = [job.title for job in match.filter_jobs(jobs, ("ANALYST",), ())]
    assert "Senior Data Analyst" in titles
    assert "Marketing Manager" not in titles


def test_filter_applies_exclusions():
    jobs = match.extract_jobs(SAMPLE_HTML, "vizi-item-title")
    titles = [
        job.title
        for job in match.filter_jobs(jobs, ("analyst",), ("IT Support Analyst",))
    ]
    assert "IT Support Analyst" not in titles
    assert "Senior Data Analyst" in titles


def test_filter_no_match_returns_empty():
    jobs = match.extract_jobs(SAMPLE_HTML, "vizi-item-title")
    assert match.filter_jobs(jobs, ("nonexistent",), ()) == []


def test_job_key_prefers_url_then_title():
    assert JobListing("A", "https://x/1").key == "https://x/1"
    assert JobListing("A").key == "A"


def test_select_new_drops_seen_and_keeps_order():
    jobs = [
        JobListing("A", "u1"),
        JobListing("B", "u2"),
        JobListing("C"),
    ]
    new = match.select_new(jobs, {"u1"})
    assert [job.title for job in new] == ["B", "C"]


def test_format_job_table_shows_property():
    table = match.format_job_table(
        [JobListing("Financial Analyst", "https://x/1", "M Resort")]
    )
    assert "Financial Analyst" in table
    assert "M Resort" in table


def test_format_check_report_shows_counts_and_roles():
    new = [JobListing("Data Analyst", "https://x/1", "M Resort")]
    report = match.format_check_report(scraped=10, matched=2, new_jobs=new)
    assert "Scraped 10" in report
    assert "matched filter(s)" in report
    assert "1 new" in report
    assert "Data Analyst" in report
    assert "M Resort" in report
    assert "No email sent" in report


def test_format_check_report_handles_nothing_new():
    report = match.format_check_report(scraped=10, matched=2, new_jobs=[])
    assert "Nothing new" in report

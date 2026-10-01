"""Pure job parsing, filtering, and terminal formatting."""

from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from .models import JobListing


def extract_jobs(html: str, item_class: str) -> list[JobListing]:
    """Parse job titles and links from board HTML.

    Assumes each title element is wrapped by an ``<a>`` whose href is the
    role's URL; entries without that anchor keep an empty URL.
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for entry in soup.find_all(class_=item_class):
        title = entry.get_text(strip=True)
        if not title:
            continue
        link = entry.find_parent("a")
        url = link["href"] if (link and link.has_attr("href")) else ""
        jobs.append(enrich_job(JobListing(title=title, url=url)))
    return jobs


def property_from_url(url: str) -> str:
    """Best-effort property/employer label from the first URL path segment.

    A heuristic for boards that namespace roles by location, e.g.
    ``/lakeside-resort-123/role.html`` -> ``Lakeside Resort``. Trailing id
    suffixes and ``.html`` segments are dropped; returns "" when nothing fits.
    """
    if not url:
        return ""

    path_parts = [
        part for part in urlparse(url).path.split("/")
        if part and not part.endswith(".html")
    ]
    if not path_parts:
        return ""

    segment = unquote(path_parts[0])
    segment = re.sub(r"-\d+$", "", segment)
    words = segment.replace("-", " ").replace("_", " ").split()
    return " ".join(word.capitalize() for word in words)


def enrich_job(job: JobListing) -> JobListing:
    if job.property_name:
        return job
    return JobListing(
        title=job.title,
        url=job.url,
        property_name=property_from_url(job.url),
    )


def filter_jobs(jobs: list[JobListing],
                keywords: tuple[str, ...],
                exclude: tuple[str, ...]) -> list[JobListing]:
    """Keep jobs whose title contains any keyword; exclusions take priority.

    Matching is case-insensitive substring matching on the title.
    """
    kw = [k.lower() for k in keywords]
    ex = [e.lower() for e in exclude]
    kept = []
    for job in jobs:
        low = job.title.lower()
        if any(x in low for x in ex):  # an exclude term always wins
            continue
        if any(k in low for k in kw):
            kept.append(job)
    return kept


def select_new(jobs: list[JobListing], seen: set[str]) -> list[JobListing]:
    """Drop jobs already alerted on, compared by their dedupe key."""
    return [job for job in jobs if job.key not in seen]


def _clip(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    return value[:width - 1] + "…"


def format_job_table(jobs: list[JobListing]) -> str:
    if not jobs:
        return ""

    rows = [("#", "Title", "Property")]
    rows.extend(
        (
            str(i),
            _clip(job.title, 42),
            _clip(job.property_name or "-", 28),
        )
        for i, job in enumerate(jobs, 1)
    )

    widths = [max(len(row[i]) for row in rows) for i in range(3)]
    lines = [
        f"{rows[0][0]:>{widths[0]}}  "
        f"{rows[0][1]:<{widths[1]}}  "
        f"{rows[0][2]:<{widths[2]}}",
        f"{'-' * widths[0]}  {'-' * widths[1]}  {'-' * widths[2]}",
    ]
    lines.extend(
        f"{row[0]:>{widths[0]}}  {row[1]:<{widths[1]}}  {row[2]:<{widths[2]}}"
        for row in rows[1:]
    )
    return "\n".join(lines)


def format_test_report(scraped: int,
                        matched: int,
                        new_jobs: list[JobListing]) -> str:
    lines = [
        "Role Radar — test",
        f"Scraped {scraped} listing(s) · {matched} matched filter(s) · "
        f"{len(new_jobs)} new",
        "",
    ]
    if new_jobs:
        lines.append("NEW ROLES (not yet alerted):")
        lines.append(format_job_table(new_jobs))
        lines.append("")
        lines.append("LINKS:")
        for i, job in enumerate(new_jobs, 1):
            lines.append(f"  {i}. {job.url or '(no link)'}")
    else:
        lines.append("Nothing new since the last run.")
    lines += ["", "No email sent · state unchanged."]
    return "\n".join(lines)

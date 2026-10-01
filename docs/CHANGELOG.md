# Changelog

All notable changes to RoleRadar are documented here.

## 0.1.0 — Radar, polished

- Move config, remembered-job state, and logs to `~/.config/RoleRadar`.
- Make `rr check` launch real headless Chrome and verify ChromeDriver.
- Make `rr re` resend current matches without deleting remembered state first.
- Wait for the rendered job count to stabilize before scraping the page.
- Add rotating status messages for scan, match, new-role, and finish stages.
- Remove stale command wording and repo-local runtime directories.
- Refresh the README and add a project graphic.
- Add browser smoke coverage and repository secret-leak sanity checks to CI.

## 0.0.2 — Simplified CLI

- Replace the long `role-radar` command with `rr`.
- Reduce the CLI to `test`, `check`, `run`, `re`, `jobs`, `conf`, and `reset`.
- Make `rr re` clear remembered jobs before running again.
- Remove the unused `rr clear` command.
- Remove the unused clean-export module and stale Makefile configuration.
- Recommend keeping the real `.env` outside the repository.
- Keep the existing scrape, match, deduplicate, email, and state behavior.

## 0.0.1 — Initial Release

- Monitor JavaScript-rendered job boards with Selenium.
- Match configurable job-title keywords and exclusions.
- Track previously seen roles to avoid duplicate alerts.
- Send email notifications for newly discovered matches.
- Include pytest, Ruff linting, and GitHub Actions CI.

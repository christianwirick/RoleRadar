# Changelog

All notable changes to RoleRadar are documented here.

## 0.0.2 — Simplified CLI

- Replace the long `role-radar` command with `rr`.
- Reduce the CLI to `test`, `check`, `run`, `re`, `jobs`, `conf`, and `reset`.
- Make `rr re` clear remembered jobs before running again.
- Remove the unused `rr clear` command.
- Remove the unused clean-export module and stale Makefile configuration.
- Recommend keeping the real `.env` outside the repository and linking it into the project.
- Keep the existing scrape, match, deduplicate, email, and state behavior.

## 0.0.1 — Initial Release

- Monitor JavaScript-rendered job boards with Selenium.
- Match configurable job-title keywords and exclusions.
- Track previously seen roles to avoid duplicate alerts.
- Send email notifications for newly discovered matches.
- Preview email output without sending.
- Validate local configuration with the `doctor` command.
- Export a clean, shareable copy of the project.
- Provide a packaged `role-radar` CLI.
- Include pytest, Ruff linting, and GitHub Actions CI.

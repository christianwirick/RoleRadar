# Roadmap

RoleRadar stays small on purpose. These are the improvements worth considering next.

## Next

- Store richer remembered-job details so `rr jobs` can show title, property, URL, and first-seen time.
- Normalize relative job URLs with the board URL.
- Add a migration path if the state format changes.
- Add an optional scheduler example for macOS `launchd`.
- Improve browser diagnostics for version mismatch and macOS Gatekeeper failures.

## Later

- Support another job-board layout through a small scraper adapter.
- Add optional location filters.
- Add optional exact-title matching alongside substring matching.
- Package a polished install path that does not require activating the project virtual environment.

## Not planned

RoleRadar is not trying to become a web app, database service, account platform, or general-purpose job-search engine.

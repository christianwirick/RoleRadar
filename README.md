# Role Radar

[![CI](https://github.com/christianwirick/RoleRadar/actions/workflows/ci.yml/badge.svg)](https://github.com/christianwirick/RoleRadar/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Ruff](https://img.shields.io/badge/lint-Ruff-261230)
![Version](https://img.shields.io/badge/version-0.0.1-7D46D8)

Role Radar is a small Python CLI that watches a job board and alerts you when new roles match your configured titles.

## Features

- Loads JavaScript-rendered job boards with Selenium
- Filters jobs using configurable title keywords
- Supports excluded titles
- Remembers previously seen roles
- Emails only new matches
- Supports dry runs and email previews
- Keeps credentials and runtime files out of Git

## Requirements

- Python 3.10+
- Google Chrome

## Install

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e '.[dev]'
    cp .env.example .env

Edit `.env` with your job board, title filters, and email settings.

## Usage

Check without sending email or changing saved state:

    role-radar check

Run normally:

    role-radar run

Other commands:

    role-radar doctor
    role-radar config show
    role-radar titles show
    role-radar seen list
    role-radar preview-email
    role-radar export-clean
    role-radar --version

The package can also run directly:

    python -m role_radar check

## Configuration

Example settings:

    JOB_BOARD_URL=https://careers.example.com/openings
    JOB_TITLES=analyst,data analyst,analytics
    EXCLUDE_TITLES=IT Support Analyst

    EMAIL_USER=you@example.com
    EMAIL_PASSWORD=your-app-password
    EMAIL_TO=you@example.com

    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587

`.env` is ignored by Git.

## Tests

    pytest

Tests run offline and do not require a live job board or real email account.

## Structure

    .
    ├── src/
    │   └── role_radar/
    │       ├── config/
    │       │   ├── __init__.py
    │       │   └── settings.py
    │       ├── __init__.py
    │       ├── __main__.py
    │       ├── cli.py
    │       ├── mail.py
    │       ├── match.py
    │       ├── models.py
    │       ├── out.py
    │       ├── pack.py
    │       ├── scraper.py
    │       └── state.py
    ├── tests/
    ├── data/
    ├── logs/
    ├── CHANGELOG.md
    ├── LICENSE
    ├── Makefile
    ├── .env.example
    ├── .gitignore
    ├── pyproject.toml
    └── README.md

# RoleRadar

[![CI](https://github.com/christianwirick/RoleRadar/actions/workflows/ci.yml/badge.svg)](https://github.com/christianwirick/RoleRadar/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Ruff](https://img.shields.io/badge/lint-Ruff-261230)
![Version](https://img.shields.io/badge/version-0.0.1-7D46D8)
![License](https://img.shields.io/badge/license-BSD--3--Clause-green)

A lightweight Python CLI that watches job boards and emails new matching roles.

**Monitor → Match → Deduplicate → Notify**

## What it does

- Scrapes JavaScript-rendered job boards with Selenium
- Matches roles against configurable title keywords
- Remembers previously seen jobs
- Emails only newly discovered matches
- Supports dry runs, diagnostics, and email previews

## Quick start

```bash
git clone https://github.com/christianwirick/RoleRadar.git
cd RoleRadar

make setup
cp .env.example .env
```

Edit `.env`, then verify your configuration:

```bash
make doctor
```

Check the board without sending email:

```bash
role-radar check
```

Run normally:

```bash
role-radar run
```

## Commands

| Command | Purpose |
| --- | --- |
| `role-radar check` | Scan without sending email or updating state |
| `role-radar run` | Scan and notify about new matches |
| `role-radar doctor` | Validate local configuration |
| `role-radar config show` | Show resolved configuration |
| `role-radar titles show` | Show title filters |
| `role-radar seen list` | Show previously seen roles |
| `role-radar preview-email` | Generate a local email preview |
| `role-radar export-clean` | Create a clean project export |

## Configuration

Copy the example file:

```bash
cp .env.example .env
```

The main settings are:

- job board URL
- included job titles
- excluded job titles
- email credentials and recipient
- SMTP configuration

See [`.env.example`](.env.example) for the complete template.

## Development

```bash
make check
```

This runs:

- Ruff
- pytest

The test suite runs offline and does not require a live job board or email account.

## License

BSD 3-Clause. Reuse and modification are permitted as long as the copyright and license notice are retained.

See [LICENSE](LICENSE).

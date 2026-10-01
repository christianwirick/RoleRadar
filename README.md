# RoleRadar

[![CI](https://github.com/christianwirick/RoleRadar/actions/workflows/ci.yml/badge.svg)](https://github.com/christianwirick/RoleRadar/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Ruff](https://img.shields.io/badge/lint-Ruff-261230)
![Version](https://img.shields.io/badge/version-0.0.2-7D46D8)
![License](https://img.shields.io/badge/license-BSD--3--Clause-green)

A lightweight Python CLI that watches job boards and emails new matching roles.

**Monitor → Match → Deduplicate → Notify**

## Quick start

```bash
git clone https://github.com/christianwirick/RoleRadar.git
cd RoleRadar
make setup
source .venv/bin/activate
```

Keep the real configuration outside the repository:

```bash
mkdir -p ~/.config/RoleRadar
cp .env.example ~/.config/RoleRadar/.env
ln -s ~/.config/RoleRadar/.env .env
chmod 600 ~/.config/RoleRadar/.env
```

Edit `~/.config/RoleRadar/.env`, then use `rr`.

## Commands

| Command | Purpose |
| --- | --- |
| `rr test` | Scan the live board without email or state changes |
| `rr check` | Validate local configuration and dependencies |
| `rr run` | Scan, email new matches, and save state |
| `rr re` | Clear remembered jobs, then run again |
| `rr jobs` | Show jobs already remembered |
| `rr conf` | Show resolved configuration with the password hidden |
| `rr reset` | Clear remembered job state |

## Typical use

Validate the setup:

```bash
rr check
```

Test the board without sending email:

```bash
rr test
```

Send alerts for new matches:

```bash
rr run
```

Retest the full email flow, including jobs already seen:

```bash
rr re
```

See remembered jobs:

```bash
rr jobs
```

Clear remembered jobs without running:

```bash
rr reset
```

## Configuration

The main settings are:

- job board URL
- included job titles
- excluded job titles
- email credentials and recipient
- SMTP configuration

See [`.env.example`](.env.example) for the template.

## Development

```bash
make check
```

This runs Ruff and pytest.

## License

BSD 3-Clause. See [LICENSE](LICENSE).

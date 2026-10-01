# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a security vulnerability.

Use GitHub's private vulnerability reporting for this repository when available. Include:

- the affected file or behavior
- steps to reproduce
- the impact you observed
- a minimal proof of concept, if useful

## Secrets

RoleRadar reads credentials from:

```text
~/.config/RoleRadar/.env
```

Do not commit that file or paste credentials into issues, pull requests, screenshots, or logs.

The checked-in `.env.example` contains placeholders only.

## Runtime data

RoleRadar keeps its state and log outside the repository:

```text
~/.config/RoleRadar/seen_jobs.json
~/.config/RoleRadar/role_radar.log
```

## Supported version

Security fixes are applied to the latest release on `main`.

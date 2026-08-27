"""Clean source export.

Builds a shareable zip of source and docs only, excluding secrets (.env),
runtime state, logs, local exports, VCS metadata, and caches.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from .out import short_error


class PackError(Exception):
    """The clean export could not be written."""


def should_export(base_dir: Path, path: Path) -> bool:
    """Return True if a path belongs in the clean export.

    Denylist-based: excludes VCS/venv/cache directories, runtime folders,
    the secret .env, and generated artifacts by name or suffix.
    """
    rel = path.relative_to(base_dir)
    parts = set(rel.parts)

    # Editable/package installs create generated metadata that should never
    # appear in a clean source export.
    if any(part.endswith(".egg-info") for part in rel.parts):
        return False

    if path.is_dir():
        return False
    if parts & {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}:
        return False
    if parts & {"data", "logs", "dist"}:  # runtime state, logs, local exports
        return False
    if path.name in {".env", "role-radar.env", ".DS_Store"}:
        return False
    if path.suffix in {".pyc", ".pyo", ".zip", ".log"}:
        return False
    return True


def export_clean(base_dir: Path, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    try:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(base_dir.rglob("*")):
                if should_export(base_dir, path):
                    archive.write(path, path.relative_to(base_dir))
                    written += 1
    except OSError as err:
        raise PackError(f"Could not write export {output_path}: {short_error(err)}")

    return written

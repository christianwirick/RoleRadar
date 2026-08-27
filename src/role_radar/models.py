"""Shared data objects for Role Radar."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    url: str
    keywords: tuple[str, ...]
    exclude: tuple[str, ...]
    item_class: str
    email_user: str
    email_password: str
    email_to: str
    smtp_host: str
    smtp_port: int


@dataclass(frozen=True)
class JobListing:
    title: str
    url: str = ""
    property_name: str = ""

    @property
    def key(self) -> str:
        """Stable identity for de-duplication: the URL, or the title if none."""
        return self.url or self.title

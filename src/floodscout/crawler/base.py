from __future__ import annotations

from typing import Protocol

from floodscout.core.models import CrawlTask, RawPost


class WeiboCrawler(Protocol):
    def fetch(self, task: CrawlTask) -> list[RawPost]:
        """Fetch raw posts for a task."""

    def supports(self, source_type: str) -> bool:
        """Whether crawler supports source_type."""

    def healthcheck(self) -> tuple[bool, str]:
        """Return crawler health status."""

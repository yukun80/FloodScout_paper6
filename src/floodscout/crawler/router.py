from __future__ import annotations

from floodscout.core.models import CrawlTask, RawPost
from floodscout.crawler.base import WeiboCrawler
from floodscout.crawler.real_weibo import WeiboCrawlerError


class CrawlBackendRouter:
    """Route crawling requests across API and browser crawler backends."""

    def __init__(
        self,
        api_crawler: WeiboCrawler | None,
        browser_crawler: WeiboCrawler | None,
        mode: str = "hybrid",
    ) -> None:
        self.api_crawler = api_crawler
        self.browser_crawler = browser_crawler
        self.mode = mode

    def supports(self, source_type: str) -> bool:
        if self.mode == "api":
            return bool(self.api_crawler and self.api_crawler.supports(source_type))
        if self.mode == "crawl4ai":
            return bool(self.browser_crawler and self.browser_crawler.supports(source_type))
        return True

    def healthcheck(self) -> tuple[bool, str]:
        checks: list[str] = []
        if self.api_crawler:
            ok, msg = self.api_crawler.healthcheck()
            checks.append(f"api={ok}:{msg}")
        if self.browser_crawler:
            ok, msg = self.browser_crawler.healthcheck()
            checks.append(f"browser={ok}:{msg}")
        if not checks:
            return False, "no crawler backends configured"
        return True, "; ".join(checks)

    def fetch(self, task: CrawlTask) -> list[RawPost]:
        if self.mode == "api":
            return self._fetch_with(self.api_crawler, task)
        if self.mode == "crawl4ai":
            return self._fetch_with(self.browser_crawler, task)

        if task.source_type in {"topic_browser", "detail_browser"}:
            return self._fetch_with_fallback(primary=self.browser_crawler, fallback=self.api_crawler, task=task)
        return self._fetch_with_fallback(primary=self.api_crawler, fallback=self.browser_crawler, task=task)

    def _fetch_with_fallback(
        self,
        primary: WeiboCrawler | None,
        fallback: WeiboCrawler | None,
        task: CrawlTask,
    ) -> list[RawPost]:
        if primary and primary.supports(task.source_type):
            try:
                return primary.fetch(task)
            except Exception as exc:  # noqa: BLE001
                if not fallback or not fallback.supports(task.source_type):
                    raise WeiboCrawlerError(f"primary crawler failed: {exc}") from exc
                return fallback.fetch(task)
        if fallback and fallback.supports(task.source_type):
            return fallback.fetch(task)
        raise WeiboCrawlerError(f"No crawler supports source_type={task.source_type}")

    def _fetch_with(self, crawler: WeiboCrawler | None, task: CrawlTask) -> list[RawPost]:
        if crawler is None:
            raise WeiboCrawlerError("crawler backend is not configured")
        if not crawler.supports(task.source_type):
            raise WeiboCrawlerError(f"crawler does not support source_type={task.source_type}")
        return crawler.fetch(task)


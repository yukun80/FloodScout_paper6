from __future__ import annotations

import asyncio
import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

from floodscout.core.models import CrawlTask, RawPost
from floodscout.crawler.real_weibo import WeiboCrawlerError, clean_weibo_html

_DETAIL_URL_RE = re.compile(r"https?://m\.weibo\.cn/detail/(\d+)")
_TEXT_RE = re.compile(r'"text"\s*:\s*"([^"]+)"')


@dataclass(slots=True)
class Crawl4AIWeiboCrawlerConfig:
    cookie: str | None = None
    headless: bool = True
    page_timeout_ms: int = 30000
    wait_for_selector: str = ".card-wrap"
    max_scroll_times: int = 4
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )


class Crawl4AIWeiboCrawler:
    """Browser-based crawler for topic/detail fallback crawling."""

    def __init__(self, config: Crawl4AIWeiboCrawlerConfig | None = None) -> None:
        self.config = config or Crawl4AIWeiboCrawlerConfig()

    def supports(self, source_type: str) -> bool:
        return source_type in {"topic_browser", "detail_browser", "keyword_api"}

    def healthcheck(self) -> tuple[bool, str]:
        try:
            from crawl4ai import AsyncWebCrawler  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            return False, f"crawl4ai import failed: {exc}"
        return True, "crawl4ai ready"

    def fetch(self, task: CrawlTask) -> list[RawPost]:
        ok, msg = self.healthcheck()
        if not ok:
            raise WeiboCrawlerError(msg)
        return asyncio.run(self._fetch_async(task))

    async def _fetch_async(self, task: CrawlTask) -> list[RawPost]:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        browser_cfg = BrowserConfig(
            headless=self.config.headless,
            user_agent=self.config.user_agent,
            headers=self._build_headers(),
        )
        run_cfg = CrawlerRunConfig(
            page_timeout=self.config.page_timeout_ms,
            wait_for=self.config.wait_for_selector,
            remove_overlay_elements=True,
        )
        url = task.entry_url or self._build_search_url(task.keyword)

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)

        if not getattr(result, "success", False):
            raise WeiboCrawlerError(f"crawl4ai crawl failed for url={url}")

        markdown = str(getattr(result, "markdown", "") or "")
        html_text = str(getattr(result, "html", "") or "")
        return self._parse_posts(task=task, source_url=url, markdown=markdown, html_text=html_text)

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept-Language": "zh-CN,zh;q=0.9"}
        if self.config.cookie:
            headers["Cookie"] = self.config.cookie
        return headers

    def _build_search_url(self, keyword: str) -> str:
        return f"https://m.weibo.cn/search?containerid=100103type=1%26q%3D{quote_plus(keyword)}"

    def _parse_posts(
        self,
        task: CrawlTask,
        source_url: str,
        markdown: str,
        html_text: str,
    ) -> list[RawPost]:
        now = datetime.now(timezone.utc)
        text_pool = f"{markdown}\n{html_text}"
        post_ids = list(dict.fromkeys(_DETAIL_URL_RE.findall(text_pool)))
        text_candidates = _TEXT_RE.findall(html_text)

        posts: list[RawPost] = []
        for idx, post_id in enumerate(post_ids):
            text_raw = ""
            if idx < len(text_candidates):
                text_raw = clean_weibo_html(html.unescape(text_candidates[idx]))
            if not text_raw:
                text_raw = self._guess_text_from_markdown(markdown, idx)
            if not text_raw:
                continue
            posts.append(
                RawPost(
                    post_id=str(post_id),
                    publish_time_raw=now.isoformat(),
                    crawl_time=now,
                    text_raw=text_raw,
                    media_urls=[],
                    source_url=f"https://m.weibo.cn/detail/{post_id}",
                    search_keyword=task.keyword,
                    city_hint=task.city,
                    crawl_source="browser",
                    text_markdown=markdown[:4000] or None,
                    topic=task.topic,
                    source_entry_url=source_url,
                )
            )
        return posts

    def _guess_text_from_markdown(self, markdown: str, idx: int) -> str:
        lines = [line.strip() for line in markdown.splitlines() if line.strip()]
        if not lines:
            return ""
        offset = min(idx, len(lines) - 1)
        return clean_weibo_html(lines[offset])


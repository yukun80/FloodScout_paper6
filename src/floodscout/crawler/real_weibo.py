from __future__ import annotations

import html
import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dateutil import parser as dt_parser

from floodscout.core.models import CrawlTask, RawPost

_CN_TZ = timezone(timedelta(hours=8))
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class WeiboCrawlerError(RuntimeError):
    pass


@dataclass(slots=True)
class RealWeiboCrawlerConfig:
    api_url: str = "https://m.weibo.cn/api/container/getIndex"
    config_url: str = "https://m.weibo.cn/api/config"
    request_timeout: float = 20.0
    max_pages: int = 3
    sleep_seconds: float = 1.0
    max_retries: int = 3
    retry_backoff_seconds: float = 1.2
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )
    cookie: str | None = None


class RealWeiboCrawler:
    """Production crawler adapter for Weibo mobile search API."""

    def __init__(self, config: RealWeiboCrawlerConfig | None = None) -> None:
        self.config = config or RealWeiboCrawlerConfig()

    def validate_cookie(self) -> tuple[bool, str]:
        if not self.config.cookie:
            return False, "cookie is empty"

        payload = self._request_json_with_retries(
            url=self.config.config_url,
            headers=self._build_headers(),
            context="cookie-check",
        )

        data = payload.get("data") or {}
        login = bool(data.get("login"))
        if login:
            nick = str(data.get("nick") or "")
            return True, f"login=true nick={nick or 'unknown'}"
        return False, "login=false (cookie may be expired or invalid)"

    def fetch(self, task: CrawlTask) -> list[RawPost]:
        start = date.fromisoformat(task.start_date)
        end = date.fromisoformat(task.end_date)

        results: list[RawPost] = []
        seen: set[str] = set()

        for page in range(1, self.config.max_pages + 1):
            payload = self._request_page(keyword=task.keyword, page=page)
            mblogs = _extract_mblogs(payload)
            if not mblogs:
                break

            older_hit = False
            in_range_count = 0

            for mblog in mblogs:
                post = self._build_raw_post(task, mblog)
                if post is None:
                    continue

                publish_day = dt_parser.parse(post.publish_time_raw).date()
                if publish_day > end:
                    continue
                if publish_day < start:
                    older_hit = True
                    continue

                if post.post_id in seen:
                    continue

                seen.add(post.post_id)
                in_range_count += 1
                results.append(post)

            if older_hit and in_range_count == 0:
                break

            if page < self.config.max_pages and self.config.sleep_seconds > 0:
                time.sleep(self.config.sleep_seconds)

        return results

    def _request_page(self, keyword: str, page: int) -> dict[str, Any]:
        params = {
            "containerid": f"100103type=1&q={keyword}",
            "page_type": "searchall",
            "page": str(page),
        }
        url = f"{self.config.api_url}?{urlencode(params)}"
        payload = self._request_json_with_retries(
            url=url,
            headers=self._build_headers(keyword=keyword),
            context=f"search page={page}",
        )

        ok = payload.get("ok")
        if ok not in (1, "1", True, None):
            msg = payload.get("msg") or payload.get("msg_subtype") or "unknown response"
            raise WeiboCrawlerError(f"search response not ok page={page}: {msg}")

        return payload

    def _request_json_with_retries(self, url: str, headers: dict[str, str], context: str) -> dict[str, Any]:
        error: Exception | None = None
        for attempt in range(1, self.config.max_retries + 1):
            req = Request(url=url, headers=headers, method="GET")
            try:
                with urlopen(req, timeout=self.config.request_timeout) as resp:
                    body = resp.read().decode("utf-8", errors="ignore")
                payload: dict[str, Any] = json.loads(body)
                return payload
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                error = exc
                if attempt >= self.config.max_retries:
                    break
                time.sleep(self.config.retry_backoff_seconds * attempt)
            except Exception as exc:  # noqa: BLE001
                raise WeiboCrawlerError(f"{context} failed: {exc}") from exc

        raise WeiboCrawlerError(
            f"{context} failed after {self.config.max_retries} retries: {error}"
        )

    def _build_headers(self, keyword: str | None = None) -> dict[str, str]:
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "application/json,text/plain,*/*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://m.weibo.cn/",
        }
        if keyword:
            headers["Referer"] = f"https://m.weibo.cn/search?containerid=100103type=1&q={keyword}"
        if self.config.cookie:
            headers["Cookie"] = self.config.cookie
        return headers

    def _build_raw_post(self, task: CrawlTask, mblog: dict[str, Any]) -> RawPost | None:
        post_id = str(mblog.get("id") or mblog.get("mid") or "").strip()
        if not post_id:
            return None

        publish_dt = parse_weibo_created_at(str(mblog.get("created_at", "")))

        text_candidate = (
            mblog.get("raw_text")
            or (mblog.get("longText") or {}).get("longTextContent")
            or mblog.get("text")
            or ""
        )
        text = clean_weibo_html(str(text_candidate))
        if not text:
            return None

        media_urls = extract_media_urls(mblog)
        user = mblog.get("user") or {}

        return RawPost(
            post_id=post_id,
            author_id=str(user.get("id")) if user.get("id") is not None else None,
            author_name=user.get("screen_name"),
            publish_time_raw=publish_dt.isoformat(),
            crawl_time=datetime.now(timezone.utc),
            text_raw=text,
            media_urls=media_urls,
            repost_count=int(mblog.get("reposts_count") or 0),
            comment_count=int(mblog.get("comments_count") or 0),
            like_count=int(mblog.get("attitudes_count") or 0),
            source_url=f"https://m.weibo.cn/detail/{post_id}",
            search_keyword=task.keyword,
            city_hint=task.city,
        )


def _extract_mblogs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") or {}
    cards = data.get("cards") or []

    mblogs: list[dict[str, Any]] = []
    for card in cards:
        if not isinstance(card, dict):
            continue

        mblog = card.get("mblog")
        if isinstance(mblog, dict):
            mblogs.append(mblog)

        group = card.get("card_group") or []
        for sub in group:
            if not isinstance(sub, dict):
                continue
            sub_mblog = sub.get("mblog")
            if isinstance(sub_mblog, dict):
                mblogs.append(sub_mblog)

    return mblogs


def clean_weibo_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = _HTML_TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def parse_weibo_created_at(value: str, now: datetime | None = None) -> datetime:
    now = now or datetime.now(_CN_TZ)
    text = value.strip()
    if not text:
        return now

    if text == "刚刚":
        return now

    minute_match = re.fullmatch(r"(\d+)\s*分钟前", text)
    if minute_match:
        return now - timedelta(minutes=int(minute_match.group(1)))

    hour_match = re.fullmatch(r"(\d+)\s*小时前", text)
    if hour_match:
        return now - timedelta(hours=int(hour_match.group(1)))

    if text.startswith("昨天"):
        hhmm = text.removeprefix("昨天").strip() or "00:00"
        parsed_time = datetime.strptime(hhmm, "%H:%M").time()
        return datetime.combine(now.date() - timedelta(days=1), parsed_time, tzinfo=now.tzinfo)

    if text.startswith("今天"):
        hhmm = text.removeprefix("今天").strip() or "00:00"
        parsed_time = datetime.strptime(hhmm, "%H:%M").time()
        return datetime.combine(now.date(), parsed_time, tzinfo=now.tzinfo)

    md_dash_match = re.fullmatch(r"(\d{2})-(\d{2})(?:\s+(\d{2}):(\d{2}))?", text)
    if md_dash_match:
        month = int(md_dash_match.group(1))
        day = int(md_dash_match.group(2))
        hour = int(md_dash_match.group(3) or 0)
        minute = int(md_dash_match.group(4) or 0)
        candidate = datetime(now.year, month, day, hour, minute, tzinfo=now.tzinfo)
        if candidate > now + timedelta(days=1):
            candidate = candidate.replace(year=candidate.year - 1)
        return candidate

    md_cn_match = re.fullmatch(r"(\d{1,2})月(\d{1,2})日(?:\s+(\d{1,2}):(\d{1,2}))?", text)
    if md_cn_match:
        month = int(md_cn_match.group(1))
        day = int(md_cn_match.group(2))
        hour = int(md_cn_match.group(3) or 0)
        minute = int(md_cn_match.group(4) or 0)
        candidate = datetime(now.year, month, day, hour, minute, tzinfo=now.tzinfo)
        if candidate > now + timedelta(days=1):
            candidate = candidate.replace(year=candidate.year - 1)
        return candidate

    try:
        parsed = dt_parser.parse(text)
    except Exception:  # noqa: BLE001
        return now

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=now.tzinfo)

    return parsed.astimezone(now.tzinfo)


def extract_media_urls(mblog: dict[str, Any]) -> list[str]:
    urls: list[str] = []

    pics = mblog.get("pics") or []
    for pic in pics:
        if not isinstance(pic, dict):
            continue
        if isinstance(pic.get("large"), dict) and pic["large"].get("url"):
            urls.append(str(pic["large"]["url"]))
        elif pic.get("url"):
            urls.append(str(pic["url"]))

    page_info = mblog.get("page_info") or {}
    page_pic = page_info.get("page_pic") or {}
    if page_pic.get("url"):
        urls.append(str(page_pic["url"]))

    return sorted(set(urls))

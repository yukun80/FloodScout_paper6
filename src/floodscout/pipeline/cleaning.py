from __future__ import annotations

import re
from dateutil import parser as dt_parser

from floodscout.core.models import NormalizedPost, RawPost

_URL_RE = re.compile(r"https?://\S+")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    text = _URL_RE.sub(" ", text)
    text = text.replace("\n", " ").strip()
    text = _WHITESPACE_RE.sub(" ", text)
    return text


def normalize_posts(raw_posts: list[RawPost]) -> list[NormalizedPost]:
    items: list[NormalizedPost] = []
    for raw in raw_posts:
        publish_time = dt_parser.parse(raw.publish_time_raw)
        items.append(
            NormalizedPost(
                platform=raw.platform,
                post_id=raw.post_id,
                publish_time=publish_time,
                text_clean=clean_text(raw.text_raw),
                search_keyword=raw.search_keyword,
                city_hint=raw.city_hint,
                media_urls=raw.media_urls,
            )
        )
    return items

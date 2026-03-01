from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from floodscout.core.models import CrawlTask, RawPost


class MockWeiboCrawler:
    """Local deterministic crawler for pipeline validation.

    Replace this class with a real crawler implementation when connecting
    to external data sources.
    """

    def fetch(self, task: CrawlTask) -> list[RawPost]:
        seed = hashlib.md5(task.task_id.encode("utf-8")).hexdigest()[:8]
        base_texts = [
            f"{task.city} 出现严重积水，部分路口车辆无法通行，水深约30厘米。",
            f"{task.city} 暴雨导致地下车库进水，请附近居民注意安全。",
            f"{task.city} 天气不错，今天出门散步。",
        ]

        posts: list[RawPost] = []
        for idx, text in enumerate(base_texts):
            post_id = f"{seed}-{idx}"
            posts.append(
                RawPost(
                    post_id=post_id,
                    author_id=f"author-{idx}",
                    author_name=f"user_{idx}",
                    publish_time_raw=f"{task.start_date} 10:0{idx}:00",
                    crawl_time=datetime.now(timezone.utc),
                    text_raw=text,
                    media_urls=[],
                    repost_count=idx * 3,
                    comment_count=idx * 2,
                    like_count=idx * 5,
                    source_url=f"https://weibo.example/{post_id}",
                    search_keyword=task.keyword,
                    city_hint=task.city,
                )
            )
        return posts

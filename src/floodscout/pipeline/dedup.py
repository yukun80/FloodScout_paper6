from __future__ import annotations

import hashlib

from floodscout.core.models import NormalizedPost


def _fingerprint(text: str) -> str:
    return hashlib.sha1(text.lower().encode("utf-8")).hexdigest()


def deduplicate_posts(posts: list[NormalizedPost]) -> list[NormalizedPost]:
    seen_text: set[str] = set()
    seen_post_id: set[str] = set()
    deduped: list[NormalizedPost] = []
    for post in posts:
        if post.post_id in seen_post_id:
            continue
        seen_post_id.add(post.post_id)
        fp = _fingerprint(post.text_clean)
        if fp in seen_text:
            continue
        seen_text.add(fp)
        deduped.append(post)
    return deduped

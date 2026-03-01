from __future__ import annotations

import hashlib

from floodscout.core.models import NormalizedPost


def _fingerprint(text: str) -> str:
    return hashlib.sha1(text.lower().encode("utf-8")).hexdigest()


def deduplicate_posts(posts: list[NormalizedPost]) -> list[NormalizedPost]:
    seen: set[str] = set()
    deduped: list[NormalizedPost] = []
    for post in posts:
        fp = _fingerprint(post.text_clean)
        if fp in seen:
            continue
        seen.add(fp)
        deduped.append(post)
    return deduped

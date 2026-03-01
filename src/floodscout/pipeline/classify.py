from __future__ import annotations

from floodscout.core.models import ClassifiedPost, NormalizedPost

_FLOOD_FACT_TERMS = ("积水", "内涝", "被淹", "进水")
_HELP_TERMS = ("求助", "被困", "救援")
_TRAFFIC_TERMS = ("拥堵", "封路", "无法通行", "交通")
_METAPHOR_TERMS = ("淹没在", "作业淹没", "信息洪流")


def classify_post(post: NormalizedPost) -> ClassifiedPost:
    text = post.text_clean

    if any(token in text for token in _METAPHOR_TERMS):
        return ClassifiedPost(post=post, label="emotion_or_metaphor", score=0.9, reason="metaphor term matched")

    if any(token in text for token in _HELP_TERMS):
        return ClassifiedPost(post=post, label="help_request", score=0.85, reason="help term matched")

    if any(token in text for token in _TRAFFIC_TERMS):
        return ClassifiedPost(post=post, label="traffic_impact", score=0.8, reason="traffic term matched")

    if any(token in text for token in _FLOOD_FACT_TERMS):
        return ClassifiedPost(post=post, label="flood_fact", score=0.88, reason="flood fact term matched")

    return ClassifiedPost(post=post, label="rumor_risk", score=0.4, reason="insufficient flood evidence")


def classify_posts(posts: list[NormalizedPost]) -> list[ClassifiedPost]:
    return [classify_post(p) for p in posts]

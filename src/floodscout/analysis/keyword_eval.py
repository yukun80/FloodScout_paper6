from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from floodscout.utils.jsonl import iter_jsonl


@dataclass(slots=True)
class KeywordMetric:
    keyword: str
    total_posts: int
    related_posts: int
    related_ratio: float
    avg_confidence: float


def evaluate_keywords(posts_file: Path, facts_file: Path) -> list[KeywordMetric]:
    keyword_posts: dict[str, int] = {}
    post_to_keyword: dict[str, str] = {}

    for item in iter_jsonl(posts_file):
        keyword = str(item.get("search_keyword") or "")
        post_id = str(item.get("post_id") or "")
        if not keyword or not post_id:
            continue
        keyword_posts[keyword] = keyword_posts.get(keyword, 0) + 1
        post_to_keyword[post_id] = keyword

    related_counts: dict[str, int] = {}
    conf_sum: dict[str, float] = {}

    for fact in iter_jsonl(facts_file):
        post_id = str(fact.get("post_id") or "")
        keyword = post_to_keyword.get(post_id)
        if not keyword:
            continue
        related_counts[keyword] = related_counts.get(keyword, 0) + 1
        conf_sum[keyword] = conf_sum.get(keyword, 0.0) + float(fact.get("confidence") or 0.0)

    metrics: list[KeywordMetric] = []
    for keyword in sorted(keyword_posts):
        total = keyword_posts[keyword]
        related = related_counts.get(keyword, 0)
        ratio = (related / total) if total else 0.0
        avg_conf = (conf_sum.get(keyword, 0.0) / related) if related else 0.0
        metrics.append(
            KeywordMetric(
                keyword=keyword,
                total_posts=total,
                related_posts=related,
                related_ratio=round(ratio, 4),
                avg_confidence=round(avg_conf, 4),
            )
        )

    return metrics


def write_keyword_metrics_csv(metrics: list[KeywordMetric], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["keyword", "total_posts", "related_posts", "related_ratio", "avg_confidence"])
        for m in metrics:
            writer.writerow([m.keyword, m.total_posts, m.related_posts, m.related_ratio, m.avg_confidence])

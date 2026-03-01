from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path

from floodscout.utils.jsonl import iter_jsonl


@dataclass(slots=True)
class ReviewSample:
    post_id: str
    city: str
    label: str
    confidence: float
    search_keyword: str
    text_clean: str
    human_label: str = ""
    human_note: str = ""


def build_review_samples(
    posts_file: Path,
    facts_file: Path,
    sample_size: int,
    seed: int = 42,
) -> list[ReviewSample]:
    post_meta: dict[str, tuple[str, str, str]] = {}
    for post in iter_jsonl(posts_file):
        post_id = str(post.get("post_id") or "")
        if not post_id:
            continue
        post_meta[post_id] = (
            str(post.get("city_hint") or ""),
            str(post.get("search_keyword") or ""),
            str(post.get("text_clean") or ""),
        )

    all_samples: list[ReviewSample] = []
    for fact in iter_jsonl(facts_file):
        post_id = str(fact.get("post_id") or "")
        meta = post_meta.get(post_id)
        if not meta:
            continue
        city, keyword, text_clean = meta
        all_samples.append(
            ReviewSample(
                post_id=post_id,
                city=city,
                label=str(fact.get("label") or fact.get("event_type") or "unknown"),
                confidence=float(fact.get("confidence") or 0.0),
                search_keyword=keyword,
                text_clean=text_clean,
            )
        )

    if sample_size <= 0:
        return []
    if sample_size >= len(all_samples):
        return all_samples

    # Keep half from low-confidence edge cases and half random for broad coverage.
    uncertain = sorted(all_samples, key=lambda x: x.confidence)[: sample_size // 2]
    uncertain_ids = {s.post_id for s in uncertain}
    pool = [s for s in all_samples if s.post_id not in uncertain_ids]

    rnd = random.Random(seed)
    rest = rnd.sample(pool, k=min(sample_size - len(uncertain), len(pool)))
    return uncertain + rest


def write_review_csv(samples: list[ReviewSample], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "post_id",
                "city",
                "label",
                "confidence",
                "search_keyword",
                "text_clean",
                "human_label",
                "human_note",
            ]
        )
        for s in samples:
            writer.writerow(
                [
                    s.post_id,
                    s.city,
                    s.label,
                    s.confidence,
                    s.search_keyword,
                    s.text_clean,
                    s.human_label,
                    s.human_note,
                ]
            )

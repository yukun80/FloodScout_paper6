import csv
import json
from pathlib import Path

from floodscout.analysis.keyword_eval import evaluate_keywords, write_keyword_metrics_csv
from floodscout.analysis.review_sampling import build_review_samples, write_review_csv


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False))
            f.write("\n")


def test_evaluate_keywords_and_write(tmp_path: Path) -> None:
    posts = tmp_path / "posts.jsonl"
    facts = tmp_path / "facts.jsonl"
    out = tmp_path / "keyword.csv"

    _write_jsonl(
        posts,
        [
            {"post_id": "p1", "search_keyword": "广州 内涝"},
            {"post_id": "p2", "search_keyword": "广州 内涝"},
            {"post_id": "p3", "search_keyword": "深圳 积水"},
        ],
    )
    _write_jsonl(
        facts,
        [
            {"post_id": "p1", "confidence": 0.8},
            {"post_id": "p3", "confidence": 0.9},
        ],
    )

    metrics = evaluate_keywords(posts, facts)
    assert len(metrics) == 2

    write_keyword_metrics_csv(metrics, out)
    with out.open("r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0][0] == "keyword"


def test_review_sampling_and_write(tmp_path: Path) -> None:
    posts = tmp_path / "posts.jsonl"
    facts = tmp_path / "facts.jsonl"
    out = tmp_path / "review.csv"

    _write_jsonl(
        posts,
        [
            {
                "post_id": "p1",
                "city_hint": "广州",
                "search_keyword": "广州 内涝",
                "text_clean": "广州积水严重",
            },
            {
                "post_id": "p2",
                "city_hint": "广州",
                "search_keyword": "广州 积水",
                "text_clean": "广州路口积水",
            },
        ],
    )
    _write_jsonl(
        facts,
        [
            {"post_id": "p1", "label": "flood_fact", "confidence": 0.9},
            {"post_id": "p2", "label": "traffic_impact", "confidence": 0.7},
        ],
    )

    samples = build_review_samples(posts, facts, sample_size=1, seed=7)
    assert len(samples) == 1

    write_review_csv(samples, out)
    assert out.exists()

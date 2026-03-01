from __future__ import annotations

import re

from floodscout.core.models import ClassifiedPost, ExtractedFact

_DEPTH_RE = re.compile(r"(\d{1,3})\s*(?:cm|厘米)")
_ROAD_BLOCKED_TERMS = ("无法通行", "封路", "中断")
_PEOPLE_TRAPPED_TERMS = ("被困", "等待救援")


def _extract_depth_cm(text: str) -> int | None:
    m = _DEPTH_RE.search(text)
    if not m:
        return None
    return int(m.group(1))


def extract_facts(items: list[ClassifiedPost]) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    for item in items:
        if item.label in {"emotion_or_metaphor", "rumor_risk"}:
            continue

        text = item.post.text_clean
        facts.append(
            ExtractedFact(
                post_id=item.post.post_id,
                city=item.post.city_hint,
                event_type=item.label,
                water_depth_cm=_extract_depth_cm(text),
                road_blocked=any(t in text for t in _ROAD_BLOCKED_TERMS),
                people_trapped=any(t in text for t in _PEOPLE_TRAPPED_TERMS),
                confidence=item.score,
                label=item.label,
                event_time=item.post.publish_time,
            )
        )
    return facts

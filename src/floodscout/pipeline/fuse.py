from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median

from floodscout.core.models import AggregatedEvent, ExtractedFact

_GRID_STEP_DEG = 0.009  # about 1km for latitude

def aggregate_events(facts: list[ExtractedFact]) -> list[AggregatedEvent]:
    groups: dict[tuple[str, str, str, str], list[ExtractedFact]] = defaultdict(list)
    for fact in facts:
        bucket = floor_time_30m(fact.event_time)
        grid_id = build_grid_id(fact.lng, fact.lat)
        groups[(fact.city, grid_id, bucket.isoformat(), fact.event_type)].append(fact)

    events: list[AggregatedEvent] = []
    for (city, grid_id, bucket_iso, event_type), items in groups.items():
        bucket = datetime.fromisoformat(bucket_iso)
        end_time = bucket + timedelta(minutes=30)
        depths = [item.water_depth_cm for item in items if item.water_depth_cm is not None]
        lngs = [item.lng for item in items if item.lng is not None]
        lats = [item.lat for item in items if item.lat is not None]
        event_id_seed = f"{city}|{grid_id}|{bucket_iso}|{event_type}|{len(items)}"
        event_id = hashlib.md5(event_id_seed.encode("utf-8")).hexdigest()[:12]
        conf = sum(_fact_confidence(i) for i in items) / len(items)
        sorted_items = sorted(items, key=lambda x: _fact_confidence(x), reverse=True)
        events.append(
            AggregatedEvent(
                event_id=event_id,
                city=city,
                date=bucket.date().isoformat(),
                start_time=bucket.isoformat(),
                end_time=end_time.isoformat(),
                grid_id=grid_id,
                center_lng=round(sum(lngs) / len(lngs), 6) if lngs else None,
                center_lat=round(sum(lats) / len(lats), 6) if lats else None,
                event_type=event_type,
                evidence_count=len(items),
                help_request_count=sum(1 for i in items if i.label == "help_request"),
                median_water_depth_cm=int(median(depths)) if depths else None,
                event_confidence=round(conf, 3),
                post_ids=[i.post_id for i in items],
                top_evidence_posts=[i.post_id for i in sorted_items[:5]],
            )
        )
    return events


def floor_time_30m(ts: datetime) -> datetime:
    minute = 30 if ts.minute >= 30 else 0
    return ts.replace(minute=minute, second=0, microsecond=0)


def build_grid_id(lng: float | None, lat: float | None) -> str:
    if lng is None or lat is None:
        return "NO_GEO"
    x = int((lng + 180.0) / _GRID_STEP_DEG)
    y = int((lat + 90.0) / _GRID_STEP_DEG)
    return f"G{x}_{y}"


def _fact_confidence(fact: ExtractedFact) -> float:
    return min(1.0, max(0.0, fact.confidence * 0.8 + fact.geo_confidence * 0.2))

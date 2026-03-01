from __future__ import annotations

import hashlib
from collections import defaultdict
from statistics import median

from floodscout.core.models import AggregatedEvent, ExtractedFact


def aggregate_events(facts: list[ExtractedFact]) -> list[AggregatedEvent]:
    groups: dict[tuple[str, str, str], list[ExtractedFact]] = defaultdict(list)
    for fact in facts:
        groups[(fact.city, fact.event_time.date().isoformat(), fact.event_type)].append(fact)

    events: list[AggregatedEvent] = []
    for (city, day, event_type), items in groups.items():
        depths = [item.water_depth_cm for item in items if item.water_depth_cm is not None]
        event_id_seed = f"{city}|{day}|{event_type}|{len(items)}"
        event_id = hashlib.md5(event_id_seed.encode("utf-8")).hexdigest()[:12]
        conf = sum(i.confidence for i in items) / len(items)
        events.append(
            AggregatedEvent(
                event_id=event_id,
                city=city,
                date=day,
                event_type=event_type,
                evidence_count=len(items),
                median_water_depth_cm=int(median(depths)) if depths else None,
                event_confidence=round(conf, 3),
                post_ids=[i.post_id for i in items],
            )
        )
    return events

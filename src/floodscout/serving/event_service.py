from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from floodscout.utils.jsonl import iter_jsonl


@dataclass(slots=True)
class EventQuery:
    city: str | None = None
    event_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    min_confidence: float = 0.0
    limit: int = 200


class EventStore:
    def __init__(self, events_file: Path) -> None:
        self.events_file = events_file

    def load(self) -> list[dict]:
        return list(iter_jsonl(self.events_file))


def query_events(events: list[dict], query: EventQuery) -> list[dict]:
    result: list[dict] = []

    for event in events:
        if query.city and str(event.get("city")) != query.city:
            continue
        if query.event_type and str(event.get("event_type")) != query.event_type:
            continue

        try:
            event_day = date.fromisoformat(str(event.get("date")))
        except ValueError:
            continue
        if query.start_date and event_day < query.start_date:
            continue
        if query.end_date and event_day > query.end_date:
            continue

        confidence = float(event.get("event_confidence") or 0.0)
        if confidence < query.min_confidence:
            continue

        result.append(event)
        if len(result) >= query.limit:
            break

    return result

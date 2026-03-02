from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from floodscout.utils.jsonl import iter_jsonl


@dataclass(slots=True)
class EventQuery:
    city: str | None = None
    event_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    grid_id: str | None = None
    bbox: tuple[float, float, float, float] | None = None  # min_lng,min_lat,max_lng,max_lat
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
        if query.grid_id and str(event.get("grid_id")) != query.grid_id:
            continue

        try:
            event_day = date.fromisoformat(str(event.get("date")))
        except ValueError:
            continue
        if query.start_date and event_day < query.start_date:
            continue
        if query.end_date and event_day > query.end_date:
            continue
        if query.start_time or query.end_time:
            start_time_raw = str(event.get("start_time") or "")
            end_time_raw = str(event.get("end_time") or "")
            if not start_time_raw or not end_time_raw:
                continue
            try:
                event_start = datetime.fromisoformat(start_time_raw)
                event_end = datetime.fromisoformat(end_time_raw)
            except ValueError:
                continue
            if query.start_time and event_end < query.start_time:
                continue
            if query.end_time and event_start > query.end_time:
                continue

        if query.bbox:
            min_lng, min_lat, max_lng, max_lat = query.bbox
            lng = event.get("center_lng")
            lat = event.get("center_lat")
            if lng is None or lat is None:
                continue
            lng_f, lat_f = float(lng), float(lat)
            if not (min_lng <= lng_f <= max_lng and min_lat <= lat_f <= max_lat):
                continue

        confidence = float(event.get("event_confidence") or 0.0)
        if confidence < query.min_confidence:
            continue

        result.append(event)
        if len(result) >= query.limit:
            break

    return result

from __future__ import annotations

from datetime import datetime, timezone

from floodscout.core.models import ExtractedFact
from floodscout.pipeline.fuse import aggregate_events, build_grid_id, floor_time_30m


def test_floor_time_30m() -> None:
    t = datetime(2026, 3, 1, 10, 47, 9, tzinfo=timezone.utc)
    b = floor_time_30m(t)
    assert b.minute == 30
    assert b.second == 0


def test_build_grid_id_no_geo() -> None:
    assert build_grid_id(None, None) == "NO_GEO"


def test_aggregate_events_with_grid_bucket() -> None:
    facts = [
        ExtractedFact(
            post_id="p1",
            city="广州",
            event_type="flood_fact",
            confidence=0.8,
            label="flood_fact",
            event_time=datetime(2026, 3, 1, 10, 10, tzinfo=timezone.utc),
            lng=113.2582,
            lat=23.1267,
            geo_confidence=0.9,
        ),
        ExtractedFact(
            post_id="p2",
            city="广州",
            event_type="flood_fact",
            confidence=0.7,
            label="help_request",
            event_time=datetime(2026, 3, 1, 10, 20, tzinfo=timezone.utc),
            lng=113.2586,
            lat=23.1269,
            geo_confidence=0.85,
        ),
    ]
    events = aggregate_events(facts)
    assert len(events) == 1
    event = events[0]
    assert event.grid_id != "NO_GEO"
    assert event.help_request_count == 1
    assert event.start_time.endswith("10:00:00+00:00")


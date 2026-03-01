from datetime import date

from floodscout.serving.event_service import EventQuery, query_events


def test_query_events_filters() -> None:
    events = [
        {
            "event_id": "e1",
            "city": "广州",
            "date": "2020-01-01",
            "event_type": "flood_fact",
            "event_confidence": 0.9,
        },
        {
            "event_id": "e2",
            "city": "深圳",
            "date": "2020-02-01",
            "event_type": "traffic_impact",
            "event_confidence": 0.6,
        },
    ]

    result = query_events(
        events,
        EventQuery(
            city="广州",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 31),
            min_confidence=0.8,
            limit=20,
        ),
    )

    assert len(result) == 1
    assert result[0]["event_id"] == "e1"

from __future__ import annotations

from datetime import datetime, timezone

from floodscout.core.models import ExtractedFact
from floodscout.pipeline.geocode import (
    GeocodeResult,
    extract_location_candidates,
    gcj02_to_wgs84,
    geocode_facts,
)


class _DummyGeocoder:
    def geocode(self, city: str, location_text: str) -> GeocodeResult | None:
        if city != "广州":
            return None
        return GeocodeResult(
            location_text=location_text,
            gcj_lng=113.2644,
            gcj_lat=23.1291,
            wgs84_lng=113.2582,
            wgs84_lat=23.1267,
            confidence=0.9,
        )


def test_extract_location_candidates() -> None:
    text = "广州天河路口积水严重，体育西地铁站附近拥堵。"
    candidates = extract_location_candidates(text)
    assert "天河路口" in candidates
    assert "体育西地铁站" in candidates


def test_geocode_facts_enriches_coordinates() -> None:
    facts = [
        ExtractedFact(
            post_id="p1",
            city="广州",
            event_type="flood_fact",
            confidence=0.8,
            label="flood_fact",
            event_time=datetime(2026, 3, 1, 10, 15, tzinfo=timezone.utc),
            location_text="天河路口",
        )
    ]
    out = geocode_facts(facts, geocoder=_DummyGeocoder())
    assert out[0].lng is not None
    assert out[0].lat is not None
    assert out[0].geo_confidence > 0


def test_gcj_to_wgs_outside_china_no_change() -> None:
    lng, lat = gcj02_to_wgs84(-74.006, 40.7128)
    assert lng == -74.006
    assert lat == 40.7128


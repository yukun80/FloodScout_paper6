from __future__ import annotations

import json
from pathlib import Path

from floodscout.serving.geojson_export import export_events_geojson


def test_export_events_geojson(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    output_file = tmp_path / "events.geojson"
    events_file.write_text(
        '{"event_id":"e1","city":"广州","center_lng":113.2582,"center_lat":23.1267}\n'
        '{"event_id":"e2","city":"广州"}\n',
        encoding="utf-8",
    )

    count = export_events_geojson(events_file, output_file)
    assert count == 1
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 1


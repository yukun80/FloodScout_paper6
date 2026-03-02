from __future__ import annotations

import json
from pathlib import Path

from floodscout.utils.jsonl import iter_jsonl


def export_events_geojson(events_file: Path, output_file: Path) -> int:
    features: list[dict] = []
    for event in iter_jsonl(events_file):
        lng = event.get("center_lng")
        lat = event.get("center_lat")
        if lng is None or lat is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
                "properties": {
                    k: v
                    for k, v in event.items()
                    if k not in {"center_lng", "center_lat"}
                },
            }
        )
    geojson = {"type": "FeatureCollection", "features": features}
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    return len(features)


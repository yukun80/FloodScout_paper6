from __future__ import annotations

import json
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from floodscout.serving.event_service import EventQuery, EventStore, query_events


def run_event_api(host: str, port: int, events_file: str) -> None:
    store = EventStore(events_file=Path(events_file))
    events_cache = store.load()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._json_response(200, {"status": "ok"})
                return

            if parsed.path == "/events":
                try:
                    query = _build_query(parse_qs(parsed.query))
                except ValueError as exc:
                    self._json_response(400, {"error": str(exc)})
                    return

                items = query_events(events_cache, query)
                self._json_response(200, {"total": len(items), "items": items})
                return

            self._json_response(404, {"error": "not found"})

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def _json_response(self, status_code: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Event API listening on http://{host}:{port}")
    print("Endpoints: /health, /events")
    server.serve_forever()


def _build_query(params: dict[str, list[str]]) -> EventQuery:
    city = _single(params, "city")
    event_type = _single(params, "event_type")

    start = _single(params, "start_date")
    end = _single(params, "end_date")
    min_conf = _single(params, "min_confidence")
    limit = _single(params, "limit")

    return EventQuery(
        city=city,
        event_type=event_type,
        start_date=date.fromisoformat(start) if start else None,
        end_date=date.fromisoformat(end) if end else None,
        min_confidence=float(min_conf) if min_conf else 0.0,
        limit=max(1, min(int(limit), 2000)) if limit else 200,
    )


def _single(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    return values[0].strip() or None

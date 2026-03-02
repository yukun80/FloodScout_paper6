from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import quote_plus
from urllib.request import urlopen

from floodscout.core.models import ExtractedFact

_LOCATION_RE = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9]{2,24}(?:路口|大道|路|街|小区|地铁站|车库|隧道|桥|广场))")


@dataclass(slots=True)
class GeocodeResult:
    location_text: str
    gcj_lng: float
    gcj_lat: float
    wgs84_lng: float
    wgs84_lat: float
    confidence: float


class GeoCoder(Protocol):
    def geocode(self, city: str, location_text: str) -> GeocodeResult | None:
        """Geocode location in one city."""


def extract_location_candidates(text: str) -> list[str]:
    if not text:
        return []
    locations: list[str] = []
    for raw in _LOCATION_RE.findall(text):
        item = raw
        if len(item) > 2 and item.endswith(("路口", "大道", "路", "街", "小区", "地铁站", "车库", "隧道", "桥", "广场")):
            # Trim common city prefixes (e.g. "广州天河路口" -> "天河路口")
            if item.startswith(("北京", "上海", "广州", "深圳", "天津", "重庆")) and len(item) > 4:
                item = item[2:]
        locations.append(item)
    return list(dict.fromkeys(locations))


class GeocodeCache:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS geocode_cache (
                    cache_key TEXT PRIMARY KEY,
                    city TEXT NOT NULL,
                    location_text TEXT NOT NULL,
                    gcj_lng REAL NOT NULL,
                    gcj_lat REAL NOT NULL,
                    wgs84_lng REAL NOT NULL,
                    wgs84_lat REAL NOT NULL,
                    confidence REAL NOT NULL
                )
                """
            )

    def get(self, cache_key: str) -> GeocodeResult | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM geocode_cache WHERE cache_key=?",
                (cache_key,),
            ).fetchone()
        if row is None:
            return None
        return GeocodeResult(
            location_text=row["location_text"],
            gcj_lng=float(row["gcj_lng"]),
            gcj_lat=float(row["gcj_lat"]),
            wgs84_lng=float(row["wgs84_lng"]),
            wgs84_lat=float(row["wgs84_lat"]),
            confidence=float(row["confidence"]),
        )

    def set(self, cache_key: str, city: str, result: GeocodeResult) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO geocode_cache(
                    cache_key, city, location_text,
                    gcj_lng, gcj_lat, wgs84_lng, wgs84_lat, confidence
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    city=excluded.city,
                    location_text=excluded.location_text,
                    gcj_lng=excluded.gcj_lng,
                    gcj_lat=excluded.gcj_lat,
                    wgs84_lng=excluded.wgs84_lng,
                    wgs84_lat=excluded.wgs84_lat,
                    confidence=excluded.confidence
                """,
                (
                    cache_key,
                    city,
                    result.location_text,
                    result.gcj_lng,
                    result.gcj_lat,
                    result.wgs84_lng,
                    result.wgs84_lat,
                    result.confidence,
                ),
            )


class GaodeGeocoder:
    def __init__(self, api_key: str, timeout_seconds: float = 8.0, cache: GeocodeCache | None = None) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.cache = cache

    def geocode(self, city: str, location_text: str) -> GeocodeResult | None:
        cache_key = f"{city}|{location_text}".strip().lower()
        if self.cache:
            hit = self.cache.get(cache_key)
            if hit:
                return hit

        encoded_address = quote_plus(location_text)
        encoded_city = quote_plus(city)
        url = (
            "https://restapi.amap.com/v3/geocode/geo"
            f"?key={self.api_key}&address={encoded_address}&city={encoded_city}"
        )
        with urlopen(url, timeout=self.timeout_seconds) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))

        if str(payload.get("status")) != "1":
            return None
        geocodes = payload.get("geocodes") or []
        if not geocodes:
            return None

        first = geocodes[0]
        loc = str(first.get("location") or "")
        if "," not in loc:
            return None
        lng_s, lat_s = loc.split(",", 1)
        gcj_lng, gcj_lat = float(lng_s), float(lat_s)
        wgs_lng, wgs_lat = gcj02_to_wgs84(gcj_lng, gcj_lat)
        confidence = 0.8 if str(first.get("level") or "") else 0.65
        result = GeocodeResult(
            location_text=location_text,
            gcj_lng=gcj_lng,
            gcj_lat=gcj_lat,
            wgs84_lng=wgs_lng,
            wgs84_lat=wgs_lat,
            confidence=confidence,
        )
        if self.cache:
            self.cache.set(cache_key, city, result)
        return result


def geocode_facts(facts: list[ExtractedFact], geocoder: GeoCoder | None) -> list[ExtractedFact]:
    if geocoder is None:
        return facts

    output: list[ExtractedFact] = []
    for fact in facts:
        if fact.location_text:
            location = fact.location_text
        else:
            location = ""
        if not location:
            output.append(fact)
            continue
        try:
            result = geocoder.geocode(fact.city, location)
        except Exception:  # noqa: BLE001
            result = None
        if result is None:
            output.append(fact)
            continue
        output.append(
            fact.model_copy(
                update={
                    "geo_confidence": result.confidence,
                    "lng": result.wgs84_lng,
                    "lat": result.wgs84_lat,
                    "gcj_lng": result.gcj_lng,
                    "gcj_lat": result.gcj_lat,
                }
            )
        )
    return output


def out_of_china(lng: float, lat: float) -> bool:
    return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)


def gcj02_to_wgs84(lng: float, lat: float) -> tuple[float, float]:
    if out_of_china(lng, lat):
        return lng, lat
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - 0.00669342162296594323 * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((6335552.717000426 * (1 - 0.00669342162296594323)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (6378245.0 / sqrtmagic * math.cos(radlat) * math.pi)
    mglat = lat + dlat
    mglng = lng + dlng
    return lng * 2 - mglng, lat * 2 - mglat


def _transform_lat(lng: float, lat: float) -> float:
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(lng: float, lat: float) -> float:
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * math.pi) + 40.0 * math.sin(lng / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * math.pi) + 300.0 * math.sin(lng / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

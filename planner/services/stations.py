from __future__ import annotations

import csv
import math
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db import transaction

from planner.constants import (
    CORRIDOR_MILES,
    GRID_CELL_DEGREES,
    HIGHWAY_MATCH_MILES,
    ROUTE_SAMPLE_MILES,
    US_STATE_CODES,
    US_STATE_NAMES,
)
from planner.models import FuelStation
from planner.services.geo import haversine_miles, highways_from_text, normalize_city
from planner.services.geocoding import geocode_city_state
from planner.services.optimizer import CandidateStation


@dataclass(frozen=True)
class StationRecord:
    opis_id: str
    name: str
    address: str
    city: str
    state: str
    price: float
    lat: float
    lng: float
    highways: frozenset[str]


class StationIndex:
    def __init__(self, stations: list[StationRecord]):
        self.stations = stations
        self.grid: dict[tuple[int, int], list[StationRecord]] = defaultdict(list)
        self.by_highway: dict[str, list[StationRecord]] = defaultdict(list)
        for station in stations:
            self.grid[_cell(station.lat, station.lng)].append(station)
            for highway in station.highways:
                self.by_highway[highway].append(station)

    def nearby(self, lat: float, lng: float, cells: int = 3) -> list[StationRecord]:
        ci, cj = _cell(lat, lng)
        found: list[StationRecord] = []
        for di in range(-cells, cells + 1):
            for dj in range(-cells, cells + 1):
                found.extend(self.grid.get((ci + di, cj + dj), []))
        return found


_index: StationIndex | None = None
_index_lock = threading.Lock()


def _cell(lat: float, lng: float) -> tuple[int, int]:
    return (
        math.floor(lat / GRID_CELL_DEGREES),
        math.floor(lng / GRID_CELL_DEGREES),
    )


def parse_fuel_csv(path: Path | None = None) -> list[dict]:
    csv_path = Path(path or settings.FUEL_CSV_PATH)
    by_id: dict[str, dict] = {}
    with csv_path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            state = (row.get("State") or "").strip().upper()
            if state not in US_STATE_CODES:
                continue
            opis_id = (row.get("OPIS Truckstop ID") or "").strip()
            if not opis_id:
                continue
            try:
                price = float(row["Retail Price"])
            except (KeyError, TypeError, ValueError):
                continue
            record = {
                "opis_id": opis_id,
                "name": (row.get("Truckstop Name") or "").strip(),
                "address": (row.get("Address") or "").strip(),
                "city": normalize_city(row.get("City") or "").title(),
                "state": state,
                "price": price,
            }
            existing = by_id.get(opis_id)
            if existing is None or price < existing["price"]:
                by_id[opis_id] = record
    return list(by_id.values())


def geocode_records(records: list[dict]) -> tuple[list[dict], int]:
    geocoded = []
    missed = 0
    for record in records:
        coords = geocode_city_state(record["city"], record["state"])
        if coords is None:
            missed += 1
            continue
        lat, lng = coords
        geocoded.append({**record, "lat": lat, "lng": lng})
    return geocoded, missed


def ingest_stations(path: Path | None = None) -> dict:
    records = parse_fuel_csv(path)
    geocoded, missed = geocode_records(records)
    objects = [FuelStation(**row) for row in geocoded]
    with transaction.atomic():
        FuelStation.objects.all().delete()
        FuelStation.objects.bulk_create(objects, batch_size=500)
    reset_index()
    return {
        "loaded": len(objects),
        "csv_us_unique": len(records),
        "unmatched_cities": missed,
    }


def _records_from_db() -> list[StationRecord]:
    return [
        StationRecord(
            opis_id=row.opis_id,
            name=row.name,
            address=row.address,
            city=row.city,
            state=row.state,
            price=row.price,
            lat=row.lat,
            lng=row.lng,
            highways=frozenset(highways_from_text(row.address)),
        )
        for row in FuelStation.objects.all()
    ]


def places_payload() -> dict:
    get_index()
    grouped: dict[str, set[str]] = defaultdict(set)
    for city, state in FuelStation.objects.values_list("city", "state"):
        if city and state:
            grouped[state].add(city)
    states = []
    for code in sorted(grouped, key=lambda item: US_STATE_NAMES.get(item, item)):
        states.append(
            {
                "code": code,
                "name": US_STATE_NAMES.get(code, code),
                "cities": sorted(grouped[code]),
            }
        )
    return {"states": states}


def get_index() -> StationIndex:
    global _index
    if _index is not None:
        return _index
    with _index_lock:
        if _index is not None:
            return _index
        if FuelStation.objects.count() == 0:
            if getattr(settings, "AUTO_INGEST_STATIONS", True):
                ingest_stations()
            else:
                _index = StationIndex([])
                return _index
        _index = StationIndex(_records_from_db())
        return _index


def reset_index() -> None:
    global _index
    with _index_lock:
        _index = None


def _downsample_route(
    latlngs: list[tuple[float, float]], sample_miles: float
) -> tuple[list[tuple[float, float]], list[float]]:
    if not latlngs:
        return [], []
    points = [latlngs[0]]
    miles = [0.0]
    total = 0.0
    since_keep = 0.0
    previous = latlngs[0]
    for point in latlngs[1:]:
        step = haversine_miles(previous[0], previous[1], point[0], point[1])
        total += step
        since_keep += step
        previous = point
        if since_keep >= sample_miles:
            points.append(point)
            miles.append(total)
            since_keep = 0.0
    if points[-1] != latlngs[-1]:
        points.append(latlngs[-1])
        miles.append(total)
    return points, miles


def _nearest_sample(
    lat: float,
    lng: float,
    samples: list[tuple[float, float]],
    sample_miles: list[float],
) -> tuple[float, float, tuple[float, float]]:
    best_distance = float("inf")
    best_mile = 0.0
    best_point = samples[0]
    for point, mile in zip(samples, sample_miles):
        distance = haversine_miles(lat, lng, point[0], point[1])
        if distance < best_distance:
            best_distance = distance
            best_mile = mile
            best_point = point
    return best_distance, best_mile, best_point


def _remember(
    best: dict[str, tuple[float, float, tuple[float, float], StationRecord]],
    station: StationRecord,
    distance: float,
    mile: float,
    point: tuple[float, float],
) -> None:
    previous = best.get(station.opis_id)
    if previous is None or distance < previous[0]:
        best[station.opis_id] = (distance, mile, point, station)


def stations_along_route(
    coordinates: list[list[float]],
    dest_miles: float,
    corridor_miles: float = CORRIDOR_MILES,
    highways: set[str] | None = None,
) -> list[CandidateStation]:
    latlngs = [(lat, lng) for lng, lat in coordinates]
    samples, sample_miles = _downsample_route(latlngs, ROUTE_SAMPLE_MILES)
    if dest_miles > 0 and sample_miles and sample_miles[-1] > 0:
        scale = dest_miles / sample_miles[-1]
        sample_miles = [mile * scale for mile in sample_miles]
    index = get_index()
    best: dict[str, tuple[float, float, tuple[float, float], StationRecord]] = {}
    for (lat, lng), mile in zip(samples, sample_miles):
        if mile > dest_miles + corridor_miles:
            break
        for station in index.nearby(lat, lng):
            distance = haversine_miles(lat, lng, station.lat, station.lng)
            if distance > corridor_miles:
                continue
            _remember(best, station, distance, mile, (lat, lng))

    for highway in highways or []:
        for station in index.by_highway.get(highway, []):
            if station.opis_id in best:
                continue
            distance, mile, point = _nearest_sample(
                station.lat, station.lng, samples, sample_miles
            )
            if distance > HIGHWAY_MATCH_MILES:
                continue
            if mile < -0.5 or mile > dest_miles + 0.5:
                continue
            _remember(best, station, distance, mile, point)

    candidates = []
    for _distance, mile, point, station in best.values():
        if mile < -0.5 or mile > dest_miles + 0.5:
            continue
        candidates.append(
            CandidateStation(
                opis_id=station.opis_id,
                name=station.name,
                address=station.address,
                city=station.city,
                state=station.state,
                price=station.price,
                lat=point[0],
                lng=point[1],
                distance_from_start_miles=round(max(0.0, mile), 2),
            )
        )
    candidates.sort(key=lambda item: (item.distance_from_start_miles, item.price))
    return candidates

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

import httpx
from django.conf import settings

from planner.constants import US_STATE_CODES
from planner.exceptions import GeocodeError, NonUSLocationError
from planner.services.geo import (
    city_lookup_keys,
    in_usa,
    normalize_city,
    parse_city_state,
    parse_coordinates,
)


@lru_cache(maxsize=1)
def load_gazetteer(path: str | None = None) -> dict[tuple[str, str], tuple[float, float]]:
    gazetteer_path = Path(path or settings.GAZETTEER_PATH)
    sums: dict[tuple[str, str], list[float]] = {}
    preferred: dict[tuple[str, str], tuple[float, float]] = {}
    with gazetteer_path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            state = (row.get("STATE_CODE") or "").strip().upper()
            if state not in US_STATE_CODES:
                continue
            try:
                lat = float(row["LATITUDE"])
                lng = float(row["LONGITUDE"])
            except (KeyError, TypeError, ValueError):
                continue
            city = row.get("CITY") or ""
            county = (row.get("COUNTY") or "").strip()
            for key in city_lookup_keys(city):
                slot = (key, state)
                bucket = sums.setdefault(slot, [0.0, 0.0, 0.0])
                bucket[0] += lat
                bucket[1] += lng
                bucket[2] += 1.0
                if county and normalize_city(county) == key:
                    preferred[slot] = (lat, lng)
    index: dict[tuple[str, str], tuple[float, float]] = {}
    for slot, (lat_sum, lng_sum, count) in sums.items():
        chosen = preferred.get(slot, (lat_sum / count, lng_sum / count))
        index[slot] = (round(chosen[0], 6), round(chosen[1], 6))
    return index


def geocode_city_state(city: str, state: str) -> tuple[float, float] | None:
    gazetteer = load_gazetteer()
    state = state.upper()
    for key in city_lookup_keys(city):
        found = gazetteer.get((key, state))
        if found:
            return found
    return None


def _photon_geocode(query: str) -> tuple[float, float, str]:
    url = f"{settings.PHOTON_BASE_URL.rstrip('/')}/api/"
    try:
        response = httpx.get(
            url,
            params={"q": query, "limit": 1, "lang": "en"},
            headers={"User-Agent": settings.HTTP_USER_AGENT},
            timeout=8.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GeocodeError(f"Could not geocode '{query}'.") from exc

    features = payload.get("features") or []
    if not features:
        raise GeocodeError(f"No match for '{query}'.")

    feature = features[0]
    coords = feature.get("geometry", {}).get("coordinates") or []
    if len(coords) < 2:
        raise GeocodeError(f"No match for '{query}'.")
    lng, lat = float(coords[0]), float(coords[1])
    props = feature.get("properties") or {}
    country = (props.get("countrycode") or props.get("country") or "").upper()
    state = (props.get("statecode") or props.get("state") or "").upper()
    if len(state) > 2:
        state = ""
    label_parts = [
        props.get("name") or query,
        props.get("state") or state,
        props.get("country") or country,
    ]
    label = ", ".join(part for part in label_parts if part)
    if country and country not in {"US", "USA", "UNITED STATES"}:
        raise NonUSLocationError(f"'{query}' is outside the USA.")
    if not in_usa(lat, lng, state or None):
        raise NonUSLocationError(f"'{query}' is outside the USA.")
    return lat, lng, label


def geocode_location(text: str) -> dict:
    query = (text or "").strip()
    if not query:
        raise GeocodeError("Start and finish locations are required.")

    coords = parse_coordinates(query)
    if coords:
        lat, lng = coords
        if not in_usa(lat, lng):
            raise NonUSLocationError("Coordinates must be inside the USA.")
        return {"label": f"{lat:.5f}, {lng:.5f}", "lat": lat, "lng": lng}

    city_state = parse_city_state(query)
    if city_state:
        city, state = city_state
        found = geocode_city_state(city, state)
        if found:
            lat, lng = found
            return {"label": f"{city.title()}, {state}", "lat": lat, "lng": lng}

    lat, lng, label = _photon_geocode(query)
    return {"label": label, "lat": lat, "lng": lng}

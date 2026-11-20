from __future__ import annotations

from functools import lru_cache

import httpx
from django.conf import settings

from planner.constants import OSRM_CACHE_DECIMALS
from planner.exceptions import RoutingError
from planner.services.geo import highways_from_text, meters_to_miles


def _cache_key(lat: float, lng: float) -> tuple[float, float]:
    return (round(lat, OSRM_CACHE_DECIMALS), round(lng, OSRM_CACHE_DECIMALS))


@lru_cache(maxsize=256)
def _fetch_route(
    start_lat: float,
    start_lng: float,
    finish_lat: float,
    finish_lng: float,
    base_url: str,
) -> dict:
    url = (
        f"{base_url.rstrip('/')}/route/v1/driving/"
        f"{start_lng},{start_lat};{finish_lng},{finish_lat}"
    )
    try:
        response = httpx.get(
            url,
            params={"overview": "full", "geometries": "geojson", "steps": "true"},
            headers={"User-Agent": settings.HTTP_USER_AGENT},
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RoutingError("Routing service is unavailable. Try again shortly.") from exc

    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoutingError("No driving route found between those locations.")

    route = payload["routes"][0]
    geometry = route.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    if len(coordinates) < 2:
        raise RoutingError("Routing service returned an empty path.")

    highways: set[str] = set()
    for leg in route.get("legs") or []:
        for step in leg.get("steps") or []:
            highways |= highways_from_text(step.get("ref") or "")
            highways |= highways_from_text(step.get("name") or "")

    return {
        "distance_miles": meters_to_miles(float(route["distance"])),
        "duration_seconds": float(route.get("duration") or 0),
        "coordinates": coordinates,
        "highways": highways,
        "geojson": {"type": "LineString", "coordinates": coordinates},
    }


def get_route(start: dict, finish: dict) -> dict:
    start_key = _cache_key(start["lat"], start["lng"])
    finish_key = _cache_key(finish["lat"], finish["lng"])
    return _fetch_route(
        start_key[0],
        start_key[1],
        finish_key[0],
        finish_key[1],
        settings.OSRM_BASE_URL,
    )

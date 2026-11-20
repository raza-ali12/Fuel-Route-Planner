from __future__ import annotations

import math
import re

from planner.constants import US_STATE_CODES

_EARTH_RADIUS_MILES = 3958.7613

_COORD_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$"
)
_CITY_STATE_RE = re.compile(
    r"^\s*(.+?)\s*,\s*([A-Za-z]{2})\s*$"
)
_HIGHWAY_RE = re.compile(r"\b(I|US)-?\s*(\d+[A-Z]?)\b", re.IGNORECASE)


def highways_from_text(text: str) -> set[str]:
    found = set()
    for kind, number in _HIGHWAY_RE.findall(text or ""):
        found.add(f"{kind.upper()}-{number.upper()}")
    return found


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_MILES * math.asin(min(1.0, math.sqrt(a)))


def normalize_city(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name.strip().upper().replace(".", ""))
    return cleaned


def city_lookup_keys(name: str) -> set[str]:
    base = normalize_city(name)
    keys = {base}
    replacements = (
        ("ST ", "SAINT "),
        ("SAINT ", "ST "),
        ("FT ", "FORT "),
        ("FORT ", "FT "),
        ("MT ", "MOUNT "),
        ("MOUNT ", "MT "),
    )
    for src, dst in replacements:
        if base.startswith(src):
            keys.add(dst + base[len(src) :])
    return keys


def parse_coordinates(text: str) -> tuple[float, float] | None:
    match = _COORD_RE.match(text)
    if not match:
        return None
    first, second = float(match.group(1)), float(match.group(2))
    if abs(first) <= 90 and abs(second) <= 180:
        return first, second
    return None


def parse_city_state(text: str) -> tuple[str, str] | None:
    match = _CITY_STATE_RE.match(text)
    if not match:
        return None
    state = match.group(2).upper()
    if state not in US_STATE_CODES:
        return None
    if parse_coordinates(text):
        return None
    return match.group(1).strip(), state


def in_usa(lat: float, lng: float, state: str | None = None) -> bool:
    if state and state.upper() in US_STATE_CODES:
        return True
    if 24.3 <= lat <= 49.5 and -124.9 <= lng <= -66.0:
        return True
    if 51.0 <= lat <= 72.0 and -180.0 <= lng <= -129.0:
        return True
    if 18.5 <= lat <= 22.5 and -160.6 <= lng <= -154.4:
        return True
    return False


def meters_to_miles(meters: float) -> float:
    return meters / 1609.344

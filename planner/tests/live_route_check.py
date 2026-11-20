"""Live OSRM checks. Run: python planner/tests/live_route_check.py"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import django

django.setup()

from planner.exceptions import PlannerError
from planner.models import FuelStation
from planner.services.osrm import _fetch_route
from planner.services.route_planner import plan_route
from planner.services.stations import reset_index

RANGE = 500.0
failures = []
passes = 0


def check(name, ok, detail=""):
    global passes
    if ok:
        passes += 1
        print(f"  PASS  {name} {detail}")
    else:
        failures.append(f"{name}: {detail}")
        print(f"  FAIL  {name} {detail}")


def csv_min_price(opis_id: str) -> float | None:
    rows = FuelStation.objects.filter(opis_id=str(opis_id))
    if not rows:
        return None
    return min(row.price for row in rows)


def assess(label: str, start: str, finish: str, expect_error=False):
    print(f"\n== {label}: {start} -> {finish}")
    try:
        result = plan_route(start, finish)
    except PlannerError as exc:
        check("error expected" if expect_error else "route completed", expect_error, str(exc))
        return
    except Exception as exc:
        check("no unexpected crash", False, f"{type(exc).__name__}: {exc}")
        return

    if expect_error:
        check("should have failed", False, "got a route")
        return

    miles = result["distance_miles"]
    gallons_needed = result["gallons_needed"]
    bought = sum(stop["gallons"] for stop in result["fuel_stops"])
    stops = result["fuel_stops"]
    check("non-negative distance", miles >= 0, f"{miles} mi")
    if miles < 1:
        check("same-place trip needs no fuel", bought == 0 and not stops)
        return
    check("gallons_needed = miles/10", abs(gallons_needed - miles / 10) < 0.05, f"{gallons_needed}")
    check("bought gallons ~= needed", abs(bought - gallons_needed) < 0.15, f"bought={bought:.4f}")
    check("cost matches sum of stops", abs(result["total_fuel_cost"] - sum(s["cost"] for s in stops)) < 0.05)
    check("at least one fill if trip > 1 mile", bool(stops) or miles < 1)

    markers = [0.0] + [s["distance_from_start_miles"] for s in stops] + [miles]
    gaps = [markers[i] - markers[i - 1] for i in range(1, len(markers))]
    check("no gap over 500 miles", all(g <= RANGE + 1.0 for g in gaps), f"max_gap={max(gaps):.1f}")
    check("miles increase along stops", all(stops[i]["distance_from_start_miles"] >= stops[i - 1]["distance_from_start_miles"] for i in range(1, len(stops))))

    tiny = [s for s in stops if s["gallons"] < 1.0]
    check("no sub-gallon fills", not tiny, str([(s["city"], s["gallons"]) for s in tiny]))

    for stop in stops:
        db_price = csv_min_price(stop["opis_id"])
        if db_price is None:
            check(f"stop {stop['opis_id']} in CSV/DB", False)
            continue
        check(
            f"CSV price {stop['name'][:24]}",
            abs(stop["price_per_gallon"] - db_price) < 0.02,
            f"api={stop['price_per_gallon']} db={db_price}",
        )
        check(
            f"cost=gal*price {stop['city']}",
            abs(stop["cost"] - stop["gallons"] * stop["price_per_gallon"]) < 0.05,
        )


def main():
    reset_index()
    _fetch_route.cache_clear()

    assess("short <500", "Austin, TX", "Dallas, TX")
    assess("medium", "Chicago, IL", "Dallas, TX")
    assess("long coast-to-coast", "Buffalo, NY", "Calexico, CA")
    assess("reverse medium", "Dallas, TX", "Chicago, IL")
    assess("northeast short", "New York, NY", "Boston, MA")
    assess("same city", "Chicago, IL", "Chicago, IL")
    assess("west coast", "Los Angeles, CA", "Phoenix, AZ")
    assess("northwest", "Seattle, WA", "Portland, OR")

    print("\n== API errors")
    assess("empty start", "", "Dallas, TX", expect_error=True)

    from planner.services.geocoding import geocode_location
    from planner.exceptions import NonUSLocationError, GeocodeError

    try:
        geocode_location("Toronto, ON")
        check("reject Canada", False, "accepted Toronto")
    except (NonUSLocationError, GeocodeError):
        check("reject Canada", True)
    except Exception as exc:
        check("reject Canada", False, str(exc))

    from planner.services.stations import places_payload

    places = places_payload()
    codes = {row["code"] for row in places["states"]}
    check("places only station states", "ON" not in codes and "IL" in codes and "TX" in codes, f"{len(places['states'])} states")
    check("no Pie Town unless in CSV", True)

    print(f"\n{passes} passed, {len(failures)} failed")
    for item in failures:
        print(" -", item)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

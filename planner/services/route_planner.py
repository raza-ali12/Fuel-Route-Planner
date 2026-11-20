from __future__ import annotations

from planner.constants import ASSUMPTIONS, CORRIDOR_MILES, MPG, RANGE_MILES
from planner.services.geocoding import geocode_location
from planner.services.optimizer import optimize_fuel
from planner.services.osrm import get_route
from planner.services.stations import stations_along_route


def plan_route(start_text: str, finish_text: str) -> dict:
    start = geocode_location(start_text)
    finish = geocode_location(finish_text)
    route = get_route(start, finish)
    distance_miles = round(route["distance_miles"], 2)
    candidates = stations_along_route(
        route["coordinates"],
        distance_miles,
        highways=route.get("highways") or set(),
    )
    result = optimize_fuel(candidates, distance_miles)
    gallons_needed = round(distance_miles / MPG, 4)

    fuel_stops = [
        {
            "opis_id": purchase.station.opis_id,
            "name": purchase.station.name,
            "address": purchase.station.address,
            "city": purchase.station.city,
            "state": purchase.station.state,
            "price_per_gallon": round(purchase.station.price, 4),
            "gallons": purchase.gallons,
            "cost": purchase.cost,
            "distance_from_start_miles": purchase.station.distance_from_start_miles,
            "lat": purchase.station.lat,
            "lng": purchase.station.lng,
        }
        for purchase in result.stops
    ]

    nearby_stations = [
        {
            "opis_id": station.opis_id,
            "name": station.name,
            "city": station.city,
            "state": station.state,
            "price_per_gallon": round(station.price, 4),
            "distance_from_start_miles": station.distance_from_start_miles,
            "lat": station.lat,
            "lng": station.lng,
        }
        for station in candidates
    ]

    return {
        "start": start,
        "finish": finish,
        "distance_miles": distance_miles,
        "mpg": MPG,
        "range_miles": RANGE_MILES,
        "gallons_needed": gallons_needed,
        "total_fuel_cost": result.total_cost,
        "assumptions": ASSUMPTIONS,
        "fuel_stops": fuel_stops,
        "nearby_stations": nearby_stations,
        "route": route["geojson"],
        "stations_considered": len(candidates),
        "corridor_miles": CORRIDOR_MILES,
    }

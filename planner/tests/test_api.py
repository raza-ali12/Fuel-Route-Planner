import pytest
from django.urls import reverse

from planner.models import FuelStation
from planner.services.optimizer import CandidateStation
from planner.services.stations import reset_index


@pytest.fixture
def station(db):
    row = FuelStation.objects.create(
        opis_id="44",
        name="Test Stop",
        address="I-35",
        city="Jarrell",
        state="TX",
        price=2.919,
        lat=30.82,
        lng=-97.61,
    )
    reset_index()
    return row


@pytest.fixture
def osrm_payload():
    return {
        "distance_miles": 100.0,
        "duration_seconds": 7200,
        "coordinates": [[-87.65, 41.85], [-96.80, 32.78]],
        "geojson": {
            "type": "LineString",
            "coordinates": [[-87.65, 41.85], [-96.80, 32.78]],
        },
    }


def test_route_api_returns_cost_and_stops(client, station, osrm_payload, monkeypatch):
    monkeypatch.setattr(
        "planner.services.route_planner.geocode_location",
        lambda text: (
            {"label": "Chicago, IL", "lat": 41.85, "lng": -87.65}
            if "Chicago" in text
            else {"label": "Dallas, TX", "lat": 32.78, "lng": -96.80}
        ),
    )
    monkeypatch.setattr(
        "planner.services.route_planner.get_route",
        lambda start, finish: osrm_payload,
    )
    monkeypatch.setattr(
        "planner.services.route_planner.stations_along_route",
        lambda coords, miles, **kwargs: [
            CandidateStation(
                opis_id=station.opis_id,
                name=station.name,
                address=station.address,
                city=station.city,
                state=station.state,
                price=station.price,
                lat=station.lat,
                lng=station.lng,
                distance_from_start_miles=5.0,
            )
        ],
    )

    response = client.get(reverse("api-route"), {"start": "Chicago, IL", "finish": "Dallas, TX"})
    assert response.status_code == 200
    body = response.json()
    assert body["distance_miles"] == 100.0
    assert body["gallons_needed"] == 10.0
    assert body["fuel_stops"]
    assert body["fuel_stops"][0]["name"] == "Test Stop"
    assert body["total_fuel_cost"] == pytest.approx(29.19)
    assert body["route"]["type"] == "LineString"


def test_route_api_requires_locations(client):
    response = client.post("/api/route", {}, content_type="application/json")
    assert response.status_code == 400


def test_map_page_renders(client):
    response = client.get("/map/?start=Chicago,%20IL&finish=Dallas,%20TX")
    assert response.status_code == 200
    assert b"Fuel Route Planner" in response.content
    assert b"leaflet" in response.content
    assert b"start-state" in response.content


def test_places_api_lists_only_station_cities(client, station):
    response = client.get("/api/places")
    assert response.status_code == 200
    body = response.json()
    assert body["states"] == [
        {"code": "TX", "name": "Texas", "cities": ["Jarrell"]}
    ]

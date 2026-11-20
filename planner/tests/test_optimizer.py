import pytest

from planner.exceptions import CannotRefuelError
from planner.services.optimizer import CandidateStation, optimize_fuel


def station(mile: float, price: float, name: str = "Stop") -> CandidateStation:
    return CandidateStation(
        opis_id=str(mile),
        name=name,
        address="I-80",
        city=name,
        state="TX",
        price=price,
        lat=32.0,
        lng=-96.0,
        distance_from_start_miles=mile,
    )


def test_short_trip_fills_just_enough_at_first_station():
    result = optimize_fuel([station(5, 3.0, "A")], dest_miles=100)
    assert len(result.stops) == 1
    assert result.stops[0].gallons == pytest.approx(10.0)
    assert result.total_cost == pytest.approx(30.0)


def test_buys_just_enough_to_reach_cheaper_station_ahead():
    result = optimize_fuel(
        [station(0, 4.0, "A"), station(400, 3.0, "B")],
        dest_miles=800,
    )
    assert [stop.station.name for stop in result.stops] == ["A", "B"]
    assert result.stops[0].gallons == pytest.approx(40.0)
    assert result.stops[1].gallons == pytest.approx(40.0)
    assert result.total_cost == pytest.approx(280.0)
    assert result.gallons_purchased == pytest.approx(80.0)


def test_fills_tank_when_current_station_is_cheapest_in_range():
    result = optimize_fuel(
        [station(0, 2.0, "A"), station(400, 5.0, "B")],
        dest_miles=800,
    )
    assert result.stops[0].gallons == pytest.approx(50.0)
    assert result.stops[1].gallons == pytest.approx(30.0)
    assert result.total_cost == pytest.approx(250.0)


def test_starts_at_cheapest_station_near_origin():
    result = optimize_fuel(
        [station(0, 4.0, "A"), station(20, 3.0, "B")],
        dest_miles=100,
    )
    assert len(result.stops) == 1
    assert result.stops[0].station.name == "B"
    assert result.stops[0].gallons == pytest.approx(10.0)


def test_burns_cheap_fuel_to_the_farthest_reachable_station():
    result = optimize_fuel(
        [station(0, 2.0, "A"), station(100, 3.0, "B"), station(480, 4.0, "C")],
        dest_miles=800,
    )
    assert [stop.station.name for stop in result.stops] == ["A", "C"]
    assert result.stops[0].gallons == pytest.approx(50.0)


def test_next_fill_picks_cheapest_station_in_the_far_half_of_range():
    result = optimize_fuel(
        [station(0, 2.0, "A"), station(400, 3.0, "B"), station(490, 5.0, "C")],
        dest_miles=800,
    )
    assert [stop.station.name for stop in result.stops] == ["A", "B"]


def test_skips_cheaper_station_that_is_only_a_few_miles_ahead():
    result = optimize_fuel(
        [station(0, 4.0, "A"), station(400, 3.0, "B"), station(406, 2.9, "C")],
        dest_miles=800,
    )
    assert "C" not in [stop.station.name for stop in result.stops]


def test_impossible_gap_over_500_miles_raises():
    with pytest.raises(CannotRefuelError):
        optimize_fuel([station(0, 3.0, "A"), station(600, 3.0, "B")], dest_miles=700)


def test_no_stations_raises():
    with pytest.raises(CannotRefuelError):
        optimize_fuel([], dest_miles=120)

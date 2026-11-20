from __future__ import annotations

from dataclasses import dataclass

from planner.constants import (
    CHEAP_FILL_LOOKAHEAD_MILES,
    MIN_HOP_MILES,
    MPG,
    ORIGIN_WINDOW_MILES,
    RANGE_MILES,
    TANK_GALLONS,
)
from planner.exceptions import CannotRefuelError


@dataclass(frozen=True)
class CandidateStation:
    opis_id: str
    name: str
    address: str
    city: str
    state: str
    price: float
    lat: float
    lng: float
    distance_from_start_miles: float


@dataclass(frozen=True)
class FuelPurchase:
    station: CandidateStation
    gallons: float
    cost: float


@dataclass(frozen=True)
class OptimizeResult:
    stops: list[FuelPurchase]
    total_cost: float
    gallons_purchased: float


def _select_stops(
    nodes: list[CandidateStation], dest_miles: float
) -> list[CandidateStation]:
    if nodes[0].distance_from_start_miles > RANGE_MILES:
        raise CannotRefuelError("No fuel station within 500 miles of the start.")

    origin = [
        node
        for node in nodes
        if node.distance_from_start_miles <= ORIGIN_WINDOW_MILES
    ]
    selected = [
        min(origin or [nodes[0]], key=lambda node: (node.price, node.distance_from_start_miles))
    ]
    while True:
        current = selected[-1]
        pos = current.distance_from_start_miles
        if dest_miles - pos <= RANGE_MILES + 1e-6:
            break
        limit = pos + RANGE_MILES
        window = [
            node
            for node in nodes
            if pos < node.distance_from_start_miles <= limit + 1e-6
        ]
        if not window:
            raise CannotRefuelError(
                f"No fuel station within 500 miles after {current.city}, {current.state}."
            )
        cheaper = next(
            (
                node
                for node in window
                if node.price < current.price - 1e-12
                and node.distance_from_start_miles - pos >= MIN_HOP_MILES
            ),
            None,
        )
        if cheaper is not None:
            selected.append(cheaper)
            continue
        far_after = pos + CHEAP_FILL_LOOKAHEAD_MILES
        far_window = [
            node for node in window if node.distance_from_start_miles >= far_after - 1e-6
        ]
        selected.append(
            min(
                far_window or window,
                key=lambda node: (node.price, -node.distance_from_start_miles),
            )
        )
    return selected


def _purchases(
    selected: list[CandidateStation], dest_miles: float
) -> list[FuelPurchase]:
    fills: list[FuelPurchase] = []
    fuel = 0.0

    for index, station in enumerate(selected):
        math_pos = 0.0 if index == 0 else station.distance_from_start_miles
        next_mile = (
            selected[index + 1].distance_from_start_miles
            if index + 1 < len(selected)
            else dest_miles
        )
        later_cheaper = any(
            later.price < station.price - 1e-12 for later in selected[index + 1 :]
        )
        need_to_next = max(0.0, (next_mile - math_pos) / MPG)
        remaining_trip = max(0.0, (dest_miles - math_pos) / MPG)

        if later_cheaper:
            buy = max(0.0, need_to_next - fuel)
        else:
            buy = min(TANK_GALLONS - fuel, max(0.0, remaining_trip - fuel))
            buy = max(buy, max(0.0, need_to_next - fuel))
            buy = min(buy, TANK_GALLONS - fuel)

        if fuel + buy + 1e-6 < need_to_next:
            raise CannotRefuelError(
                f"Cannot carry enough fuel to continue past {station.city}, {station.state}."
            )
        if buy > 1e-9:
            fuel += buy
            fills.append(
                FuelPurchase(
                    station=station,
                    gallons=round(buy, 4),
                    cost=round(buy * station.price, 4),
                )
            )
        fuel -= need_to_next
        if fuel < -1e-6:
            raise CannotRefuelError("Vehicle would run out of fuel on this route.")
        if fuel < 0:
            fuel = 0.0

    return fills


def optimize_fuel(
    stations: list[CandidateStation], dest_miles: float
) -> OptimizeResult:
    if dest_miles <= 1e-6:
        return OptimizeResult(stops=[], total_cost=0.0, gallons_purchased=0.0)

    nodes = sorted(
        [
            station
            for station in stations
            if 0 <= station.distance_from_start_miles <= dest_miles + 0.5
        ],
        key=lambda station: (station.distance_from_start_miles, station.price),
    )
    if not nodes:
        raise CannotRefuelError("No fuel stations found along this route.")

    selected = _select_stops(nodes, dest_miles)
    fills = _purchases(selected, dest_miles)
    gallons = round(sum(item.gallons for item in fills), 4)
    cost = round(sum(item.cost for item in fills), 2)
    return OptimizeResult(stops=fills, total_cost=cost, gallons_purchased=gallons)

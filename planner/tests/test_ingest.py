import csv
from pathlib import Path

import pytest

from planner.services.geocoding import load_gazetteer
from planner.services.stations import geocode_records, parse_fuel_csv


@pytest.fixture
def fuel_csv(tmp_path: Path) -> Path:
    path = tmp_path / "fuel.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["OPIS Truckstop ID", "Truckstop Name", "Address", "City", "State", "Rack ID", "Retail Price"]
        )
        writer.writerow(["1", "Cheap Stop", "I-80 EXIT 1", "Chicago", "IL", "1", "3.50"])
        writer.writerow(["1", "Cheap Stop", "I-80 EXIT 1", "Chicago", "IL", "1", "3.10"])
        writer.writerow(["2", "Canada Stop", "Hwy 1", "Toronto", "ON", "2", "2.00"])
        writer.writerow(["3", "Dallas Stop", "I-35", "Dallas", "TX", "3", "2.90"])
    return path


def test_parse_fuel_csv_filters_and_keeps_min_price(fuel_csv: Path):
    rows = parse_fuel_csv(fuel_csv)
    by_id = {row["opis_id"]: row for row in rows}
    assert "2" not in by_id
    assert by_id["1"]["price"] == 3.10
    assert set(by_id) == {"1", "3"}


def test_geocode_records_uses_gazetteer(settings, fuel_csv: Path, tmp_path: Path):
    gazetteer = tmp_path / "places.csv"
    gazetteer.write_text(
        "ID,STATE_CODE,STATE_NAME,CITY,COUNTY,LATITUDE,LONGITUDE\n"
        "1,IL,Illinois,Chicago,Cook,41.85,-87.65\n"
        "2,TX,Texas,Dallas,Dallas,32.78,-96.80\n",
        encoding="utf-8",
    )
    settings.GAZETTEER_PATH = gazetteer
    load_gazetteer.cache_clear()
    geocoded, missed = geocode_records(parse_fuel_csv(fuel_csv))
    load_gazetteer.cache_clear()
    assert missed == 0
    assert len(geocoded) == 2
    chicago = next(row for row in geocoded if row["city"] == "Chicago")
    assert chicago["lat"] == pytest.approx(41.85)

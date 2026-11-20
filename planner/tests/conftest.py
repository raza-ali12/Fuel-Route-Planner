import pytest

from planner.services.stations import reset_index


@pytest.fixture(autouse=True)
def _isolate_stations(settings):
    settings.AUTO_INGEST_STATIONS = False
    reset_index()
    yield
    reset_index()

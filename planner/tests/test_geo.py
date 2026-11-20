from planner.services.geo import highways_from_text
from planner.services.stations import _downsample_route


def test_highways_from_truckstop_address():
    assert "I-80" in highways_from_text("I-80, EXIT 3")
    assert "I-94" in highways_from_text("I-94, EXIT 143 & US-12 & SR-21")
    assert "US-12" in highways_from_text("I-94, EXIT 143 & US-12 & SR-21")
    assert highways_from_text("Main Street") == set()


def test_downsample_uses_consecutive_segment_miles():
    # 3 points, 3 miles apart along a line. Keep every 2 miles.
    points = [(0.0, 0.0), (0.0, 0.0435), (0.0, 0.087)]
    samples, miles = _downsample_route(points, 2.0)
    assert miles[0] == 0.0
    assert miles[-1] < 8.0
    assert samples[-1] == points[-1]

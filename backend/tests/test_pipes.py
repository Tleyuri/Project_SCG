import math

import ezdxf
import pytest

from app.core import pipes


def _msp():
    doc = ezdxf.new()
    return doc, doc.modelspace()


def test_line_length():
    doc, msp = _msp()
    e = msp.add_line((0, 0), (3, 4))
    assert pipes.entity_length(e) == pytest.approx(5.0)


def test_arc_length_quarter_circle():
    doc, msp = _msp()
    e = msp.add_arc(center=(0, 0), radius=10, start_angle=0, end_angle=90)
    assert pipes.entity_length(e) == pytest.approx(10 * math.pi / 2)


def test_arc_length_wraps_around_360():
    doc, msp = _msp()
    e = msp.add_arc(center=(0, 0), radius=1, start_angle=350, end_angle=10)
    # sweep ของส่วนโค้งคือ 20 องศา
    assert pipes.entity_length(e) == pytest.approx(2 * math.pi * (20 / 360))


def test_lwpolyline_with_bulge_semicircle():
    doc, msp = _msp()
    # bulge = 1 หมายถึงครึ่งวงกลม (sweep 180 องศา) ระหว่างจุด (0,0) และ (2,0)
    pl = msp.add_lwpolyline([(0, 0, 0, 0, 1.0), (2, 0, 0, 0, 0)], format="xyseb")
    radius = 1.0
    expected = radius * math.pi  # ครึ่งวงกลม รัศมี 1 = ระยะ 2 / (2*sin(90))
    assert pipes.entity_length(pl) == pytest.approx(expected)


def test_total_length_sums_entities():
    doc, msp = _msp()
    e1 = msp.add_line((0, 0), (4, 0))
    e2 = msp.add_arc(center=(10, 0), radius=2, start_angle=0, end_angle=180)
    expected = 4 + (2 * math.pi)
    assert pipes.total_length([e1, e2]) == pytest.approx(expected)


@pytest.mark.parametrize(
    "length,segment,expected",
    [
        (16.0, 4.0, 4),
        (16.1, 4.0, 5),
        (0.0, 4.0, 0),
        (3.999, 4.0, 1),
    ],
)
def test_pipe_count(length, segment, expected):
    assert pipes.pipe_count(length, segment) == expected


def test_riser_count_example_from_spec():
    # 650 หัว -> (650*0.5)/4 = 81.25 -> 82 ท่อน
    assert pipes.riser_count(650, riser_height=0.5, segment_length=4.0) == 82


def test_split_length_by_road():
    doc, msp = _msp()
    pipe = msp.add_line((0, -5), (0, 5))  # ท่อแนวตั้งผ่าน y=-5..5
    road = msp.add_line((-5, 0), (5, 0))  # ถนนแนวนอนผ่าน x=-5..5 ตัดกันที่ (0,0)

    normal, road_crossing = pipes.split_length_by_road([pipe], [road])
    assert normal == pytest.approx(0.0)
    assert road_crossing == pytest.approx(10.0)


def test_split_length_by_road_no_crossing():
    doc, msp = _msp()
    pipe = msp.add_line((0, 0), (10, 0))
    road = msp.add_line((0, 100), (10, 100))

    normal, road_crossing = pipes.split_length_by_road([pipe], [road])
    assert normal == pytest.approx(10.0)
    assert road_crossing == pytest.approx(0.0)

"""คำนวณความยาวท่อ, จำนวนท่อน, ท่อตั้ง และการตัด class ตามแนวถนน

รองรับ entity ชนิด LINE, LWPOLYLINE (รวม arc segment จาก bulge), ARC, SPLINE
"""
from __future__ import annotations

import math
from typing import Iterable

DXFTYPE_HANDLERS = {}


def _register(dxftype):
    def deco(fn):
        DXFTYPE_HANDLERS[dxftype] = fn
        return fn

    return deco


@_register("LINE")
def _line_length(entity) -> float:
    start = entity.dxf.start
    end = entity.dxf.end
    return math.hypot(end.x - start.x, end.y - start.y)


def _bulge_arc_length(p1, p2, bulge: float) -> float:
    """ความยาวส่วนโค้งของ polyline segment ที่มี bulge"""
    chord = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    if bulge == 0 or chord == 0:
        return chord
    angle = 4 * math.atan(abs(bulge))
    if angle == 0:
        return chord
    radius = chord / (2 * math.sin(angle / 2))
    return radius * angle


@_register("LWPOLYLINE")
def _lwpolyline_length(entity) -> float:
    points = list(entity.get_points("xyseb"))  # x, y, start_width, end_width, bulge
    if len(points) < 2:
        return 0.0

    total = 0.0
    closed = bool(entity.closed)
    n = len(points)
    pairs = n if closed else n - 1
    for i in range(pairs):
        p1 = points[i]
        p2 = points[(i + 1) % n]
        bulge = p1[4]
        total += _bulge_arc_length((p1[0], p1[1]), (p2[0], p2[1]), bulge)
    return total


@_register("POLYLINE")
def _polyline_length(entity) -> float:
    vertices = list(entity.vertices)
    if len(vertices) < 2:
        return 0.0
    total = 0.0
    closed = bool(entity.is_closed)
    n = len(vertices)
    pairs = n if closed else n - 1
    for i in range(pairs):
        v1 = vertices[i]
        v2 = vertices[(i + 1) % n]
        bulge = getattr(v1.dxf, "bulge", 0.0) or 0.0
        p1 = (v1.dxf.location.x, v1.dxf.location.y)
        p2 = (v2.dxf.location.x, v2.dxf.location.y)
        total += _bulge_arc_length(p1, p2, bulge)
    return total


@_register("ARC")
def _arc_length(entity) -> float:
    radius = entity.dxf.radius
    start_angle = math.radians(entity.dxf.start_angle)
    end_angle = math.radians(entity.dxf.end_angle)
    sweep = end_angle - start_angle
    if sweep <= 0:
        sweep += 2 * math.pi
    return radius * sweep


@_register("SPLINE")
def _spline_length(entity) -> float:
    bspline = entity.construction_tool()
    return bspline.approximate_length(segments=200)


@_register("CIRCLE")
def _circle_length(entity) -> float:
    return 2 * math.pi * entity.dxf.radius


def entity_length(entity) -> float:
    """คืนความยาวของ entity เดียว (0 ถ้าไม่ใช่ entity เชิงเส้นที่รองรับ)"""
    handler = DXFTYPE_HANDLERS.get(entity.dxftype())
    if handler is None:
        return 0.0
    return handler(entity)


def total_length(entities: Iterable) -> float:
    """รวมความยาวของ entity หลายตัว"""
    return sum(entity_length(e) for e in entities)


def pipe_count(total_length_value: float, segment_length: float = 4.0) -> int:
    """จำนวนท่อน = ceil(ความยาวรวม / ความยาวต่อท่อน)"""
    if total_length_value <= 0:
        return 0
    return math.ceil(total_length_value / segment_length)


def riser_count(sprinkler_count: int, riser_height: float = 0.5, segment_length: float = 4.0) -> int:
    """จำนวนท่อนของท่อตั้ง = ceil((จำนวนหัว * ความสูงท่อตั้ง) / ความยาวต่อท่อน)"""
    if sprinkler_count <= 0:
        return 0
    return math.ceil((sprinkler_count * riser_height) / segment_length)


# ---------------------------------------------------------------------------
# การตัด class ตามแนวถนน (4.2)
# ---------------------------------------------------------------------------

Point = tuple[float, float]


def entity_segments(entity) -> list[tuple[Point, Point]]:
    """แปลง entity เป็นรายการ segment เส้นตรง (p1, p2) สำหรับตรวจจุดตัด

    ส่วนโค้ง (bulge/ARC) จะถูกประมาณเป็นเส้นตรงระหว่างจุดปลาย เพียงพอสำหรับ
    การตรวจว่า "ท่อผ่านถนนหรือไม่"
    """
    dxftype = entity.dxftype()
    if dxftype == "LINE":
        start = entity.dxf.start
        end = entity.dxf.end
        return [((start.x, start.y), (end.x, end.y))]

    if dxftype == "LWPOLYLINE":
        points = [(p[0], p[1]) for p in entity.get_points("xy")]
        if len(points) < 2:
            return []
        n = len(points)
        pairs = n if entity.closed else n - 1
        return [(points[i], points[(i + 1) % n]) for i in range(pairs)]

    if dxftype == "ARC":
        center = entity.dxf.center
        radius = entity.dxf.radius
        start_angle = math.radians(entity.dxf.start_angle)
        end_angle = math.radians(entity.dxf.end_angle)
        p1 = (center.x + radius * math.cos(start_angle), center.y + radius * math.sin(start_angle))
        p2 = (center.x + radius * math.cos(end_angle), center.y + radius * math.sin(end_angle))
        return [(p1, p2)]

    return []


def _segments_intersect(a1: Point, a2: Point, b1: Point, b2: Point) -> bool:
    """True ถ้า segment a และ segment b ตัดกัน (รวมจุดปลาย)"""

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    d1 = cross(b1, b2, a1)
    d2 = cross(b1, b2, a2)
    d3 = cross(a1, a2, b1)
    d4 = cross(a1, a2, b2)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    ):
        return True

    def on_segment(p, q, r):
        return min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and min(p[1], r[1]) <= q[1] <= max(
            p[1], r[1]
        )

    if d1 == 0 and on_segment(b1, a1, b2):
        return True
    if d2 == 0 and on_segment(b1, a2, b2):
        return True
    if d3 == 0 and on_segment(a1, b1, a2):
        return True
    if d4 == 0 and on_segment(a1, b2, a2):
        return True
    return False


def split_length_by_road(
    pipe_entities: Iterable, road_entities: Iterable
) -> tuple[float, float]:
    """แยกความยาวท่อเป็น (ความยาวปกติ, ความยาวช่วงที่ตัดผ่านถนน)

    ตรวจทีละ segment ของท่อ: ถ้า segment ใดตัดกับ segment ของถนน
    ความยาวทั้ง segment นั้นจะถูกนับเป็นช่วงผ่านถนน (class 13.5)
    """
    road_segments: list[tuple[Point, Point]] = []
    for road in road_entities:
        road_segments.extend(entity_segments(road))

    normal_length = 0.0
    road_crossing_length = 0.0

    for pipe in pipe_entities:
        segments = entity_segments(pipe)
        if not segments:
            # entity ที่ไม่มี segment ตรง (เช่น SPLINE) ใช้ความยาวรวมเป็นปกติทั้งหมด
            normal_length += entity_length(pipe)
            continue

        for p1, p2 in segments:
            seg_length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            crosses = any(_segments_intersect(p1, p2, r1, r2) for r1, r2 in road_segments)
            if crosses:
                road_crossing_length += seg_length
            else:
                normal_length += seg_length

    return normal_length, road_crossing_length

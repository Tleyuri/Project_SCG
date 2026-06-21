"""ถอดชุดวาล์ว (layer "วาร์ล") - 4.6

สัญลักษณ์ 1 ชุดวาล์ว = LWPOLYLINE รูปนาฬิกาทราย (bowtie, self-intersecting)
จุดที่นาฬิกาทรายอยู่ใกล้กัน (< valve_cluster_distance) ถือเป็นจุดเดียวกัน:
- 1 นาฬิกาทราย ในจุดนั้น = วาล์วเดี่ยว
- 2 นาฬิกาทรายติดกัน = วาล์วคู่
"""
from __future__ import annotations

import math
from typing import Iterable

from app.core.pipes import entity_segments


def _polyline_points(entity) -> list[tuple[float, float]]:
    if entity.dxftype() != "LWPOLYLINE":
        return []
    return [(p[0], p[1]) for p in entity.get_points("xy")]


def _segments_cross(p: list[tuple[float, float]]) -> bool:
    """True ถ้ารูปสี่เหลี่ยมที่มีจุดยอด p (4 จุด) มีด้านตัดกัน (เป็นรูปนาฬิกาทราย)"""

    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

    def intersect(a, b, c, d):
        return (ccw(a, c, d) * ccw(b, c, d) < 0) and (ccw(a, b, c) * ccw(a, b, d) < 0)

    a, b, c, d = p[0], p[1], p[2], p[3]
    # เส้นทแยงมุมตรงข้าม: (a-b) กับ (c-d) หรือ (b-c) กับ (d-a)
    return intersect(a, b, c, d) or intersect(b, c, d, a)


def is_bowtie(entity, vertex_count: int = 4) -> bool:
    """True ถ้า entity เป็น LWPOLYLINE ปิด มีจำนวนจุดยอดตรงตามที่กำหนด และด้านตัดกันเอง"""
    if entity.dxftype() != "LWPOLYLINE":
        return False
    points = _polyline_points(entity)
    if len(points) != vertex_count:
        return False
    if not entity.closed:
        return False
    return _segments_cross(points)


def bowtie_centroid(entity) -> tuple[float, float]:
    points = _polyline_points(entity)
    x = sum(p[0] for p in points) / len(points)
    y = sum(p[1] for p in points) / len(points)
    return (x, y)


def find_bowties(entities: Iterable, vertex_count: int = 4) -> list[tuple[object, tuple[float, float]]]:
    """คืนรายการ (entity, centroid) ของนาฬิกาทรายทั้งหมดใน layer วาร์ล"""
    result = []
    for e in entities:
        if is_bowtie(e, vertex_count=vertex_count):
            result.append((e, bowtie_centroid(e)))
    return result


def cluster_points(points: list[tuple[float, float]], max_dist: float) -> list[list[int]]:
    """จัดกลุ่มจุดที่อยู่ใกล้กัน (ระยะ < max_dist) ด้วย union-find แบบง่าย

    คืนรายการ cluster แต่ละ cluster เป็นรายการ index ของจุดที่อยู่ใน points
    """
    n = len(points)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            d = math.hypot(points[i][0] - points[j][0], points[i][1] - points[j][1])
            if d < max_dist:
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        clusters.setdefault(root, []).append(i)
    return list(clusters.values())


def classify_valve_clusters(
    bowties: list[tuple[object, tuple[float, float]]], max_dist: float
) -> list[dict]:
    """จัดกลุ่ม bowtie แล้วจำแนกเป็นวาล์วเดี่ยว/วาล์วคู่ พร้อมจุดศูนย์กลาง"""
    points = [c for _, c in bowties]
    clusters = cluster_points(points, max_dist)

    results = []
    for cluster_idx in clusters:
        size = len(cluster_idx)
        cx = sum(points[i][0] for i in cluster_idx) / size
        cy = sum(points[i][1] for i in cluster_idx) / size
        if size == 1:
            valve_type = "single"
        elif size == 2:
            valve_type = "double"
        else:
            valve_type = "unknown"
        results.append({"type": valve_type, "count": size, "center": (cx, cy)})
    return results


def _point_to_segment_distance(p, a, b) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def classify_poly_centroid_clusters(polys: list, max_dist: float) -> list[dict]:
    """จัดกลุ่ม LWPOLYLINE ด้วย centroid clustering (fallback สำหรับ valve symbol ที่ไม่ใช่ bowtie เช่น แอร์วาว)

    ใช้เมื่อ find_bowties() ไม่พบนาฬิกาทรายเลย แต่มี LWPOLYLINE อื่นใน layer วาล์ว
    """
    centroids = []
    for poly in polys:
        pts = _polyline_points(poly)
        if not pts:
            continue
        x = sum(p[0] for p in pts) / len(pts)
        y = sum(p[1] for p in pts) / len(pts)
        centroids.append((x, y))
    if not centroids:
        return []
    clusters = cluster_points(centroids, max_dist)
    results = []
    for cluster_idx in clusters:
        size = len(cluster_idx)
        cx = sum(centroids[i][0] for i in cluster_idx) / size
        cy = sum(centroids[i][1] for i in cluster_idx) / size
        valve_type = "single" if size == 1 else "double" if size == 2 else "unknown"
        results.append({"type": valve_type, "count": size, "center": (cx, cy)})
    return results


def classify_circle_clusters(circles: list, cluster_tolerance: float = 15.0) -> list[dict]:
    """จัดกลุ่ม CIRCLE entities เพื่อนับชุดวาล์ว (fallback เมื่อไม่มี layer วาล์วในไฟล์)

    ใช้กับ CIRCLE ใน layer 0 ที่ช่างวาดแทน valve symbol:
    - 1 วง = วาล์วเดี่ยว
    - 2 วงใกล้กัน (< cluster_tolerance) = วาล์วคู่
    """
    centers = []
    for c in circles:
        pt = c.dxf.center
        centers.append((pt.x, pt.y))
    if not centers:
        return []
    clusters = cluster_points(centers, cluster_tolerance)
    results = []
    for cluster_idx in clusters:
        size = len(cluster_idx)
        cx = sum(centers[i][0] for i in cluster_idx) / size
        cy = sum(centers[i][1] for i in cluster_idx) / size
        valve_type = "single" if size == 1 else "double" if size >= 2 else "unknown"
        results.append({"type": valve_type, "count": size, "center": (cx, cy)})
    return results


def nearest_pipe_role(
    center: tuple[float, float], pipe_entities_by_role: dict[str, list]
) -> str | None:
    """หาว่าจุดวาล์วอยู่ใกล้ท่อ role ไหนที่สุด (สำหรับกำหนดขนาดบอลวาล์ว/ข้องอ45)

    คืนชื่อ role (เช่น "main", "submain", "lateral") ที่ใกล้ที่สุด หรือ None ถ้าไม่มีท่อเลย
    """
    best_role = None
    best_dist = math.inf
    for role, entities in pipe_entities_by_role.items():
        for entity in entities:
            for p1, p2 in entity_segments(entity):
                d = _point_to_segment_distance(center, p1, p2)
                if d < best_dist:
                    best_dist = d
                    best_role = role
    return best_role

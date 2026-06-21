"""ตัด legend (คำอธิบายสัญลักษณ์) ออกก่อนถอดวัสดุ - ใช้กับทุก layer

วิธีการ: หา bounding box ของข้อความ layer "Dim" (ซึ่งเป็นป้ายชื่อใน legend)
แล้วขยายกรอบไปทางซ้าย (เผื่อ symbol ตัวอย่างที่วาดอยู่ซ้ายมือของข้อความ)
และขยายรอบด้านด้วย margin ผู้ใช้ปรับกรอบนี้เองได้จากหน้าเว็บ
"""
from __future__ import annotations

from typing import Iterable

from app.core.dxf_reader import entities_bbox, entity_bbox, entity_centroid

BBox = tuple[float, float, float, float]

_INF = 1e12


def detect_legend_cutoff_by_gap(
    doc,
    gap_threshold: float = 30.0,
    legend_fraction: float = 0.05,
) -> BBox | None:
    """ตรวจจับขอบ legend จาก gap ใน x-positions ของ CIRCLE entities ทุก layer

    วิธี:
    1. รวม x-coordinates ของ CIRCLE ทุกตัวใน modelspace
    2. เรียงจากน้อยไปมาก หา gap ที่ใหญ่ที่สุด
    3. ถ้า gap > gap_threshold และ circles ทางขวาของ gap < legend_fraction ของทั้งหมด
       → cutoff อยู่กลาง gap นั้น และ legend_bbox = (cutoff, -∞, +∞, +∞)
    4. คืน None ถ้าหา gap ที่เหมาะไม่ได้

    ใช้กับไฟล์ที่ layer Dim กระจายทั่วแบบ (ไม่ได้อยู่แค่ใน legend)
    """
    xs: list[float] = []
    for e in doc.modelspace():
        if e.dxftype() == "CIRCLE":
            try:
                xs.append(e.dxf.center.x)
            except Exception:
                pass

    if len(xs) < 2:
        return None

    xs.sort()
    n = len(xs)

    best_gap = 0.0
    best_idx = -1
    for i in range(n - 1):
        gap = xs[i + 1] - xs[i]
        if gap > best_gap:
            best_gap = gap
            best_idx = i

    if best_gap < gap_threshold:
        return None

    n_after = n - best_idx - 1
    if n_after / n > legend_fraction:
        return None

    # cutoff = midpoint ของ gap (ป้องกัน entity ที่อยู่ขอบถูกตัดผิด)
    cutoff = (xs[best_idx] + xs[best_idx + 1]) / 2.0
    return (cutoff, -_INF, _INF, _INF)


def compute_legend_bbox(
    dim_entities: Iterable, margin: float = 5.0, left_extent: float = 60.0
) -> BBox | None:
    """ประมาณ bounding box ของ legend จาก entity ใน layer Dim

    คืน None ถ้าไม่มีข้อความ Dim เลย (ไม่มี legend ให้ตัด)
    """
    dim_entities = list(dim_entities)
    if not dim_entities:
        return None

    box = entities_bbox(dim_entities)
    if box is None:
        return None

    xmin, ymin, xmax, ymax = box
    return (xmin - left_extent - margin, ymin - margin, xmax + margin, ymax + margin)


def is_in_legend(entity, legend_bbox: BBox | None) -> bool:
    """True ถ้าจุดกึ่งกลางของ entity อยู่ในกรอบ legend"""
    if legend_bbox is None:
        return False
    centroid = entity_centroid(entity)
    if centroid is None:
        return False
    x, y = centroid
    xmin, ymin, xmax, ymax = legend_bbox
    return xmin <= x <= xmax and ymin <= y <= ymax


def filter_legend(entities: Iterable, legend_bbox: BBox | None) -> tuple[list, list]:
    """แยก entity ออกเป็น (kept, excluded_as_legend)"""
    kept, excluded = [], []
    for e in entities:
        if is_in_legend(e, legend_bbox):
            excluded.append(e)
        else:
            kept.append(e)
    return kept, excluded

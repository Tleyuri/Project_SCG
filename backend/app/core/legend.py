"""ตัด legend (คำอธิบายสัญลักษณ์) ออกก่อนถอดวัสดุ - ใช้กับทุก layer

วิธีการ: หา bounding box ของข้อความ layer "Dim" (ซึ่งเป็นป้ายชื่อใน legend)
แล้วขยายกรอบไปทางซ้าย (เผื่อ symbol ตัวอย่างที่วาดอยู่ซ้ายมือของข้อความ)
และขยายรอบด้านด้วย margin ผู้ใช้ปรับกรอบนี้เองได้จากหน้าเว็บ
"""
from __future__ import annotations

from typing import Iterable

from app.core.dxf_reader import entities_bbox, entity_bbox, entity_centroid

BBox = tuple[float, float, float, float]


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

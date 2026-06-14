"""ตรวจจับขนาดท่อ (เมน/ย่อย/แยก) จากข้อความ (TEXT/MTEXT) ใน layer Dim

วิธีการ: หาข้อความที่มีรูปแบบขนาดท่อ (เช่น 6", 3/4", 2 1/2") แล้วเลือกข้อความ
ที่อยู่ใกล้เส้นท่อของ role นั้นมากที่สุด ใช้เป็นค่าเริ่มต้นก่อนค่าที่ผู้ใช้กำหนดเอง
"""
from __future__ import annotations

import re
from typing import Iterable

from app.core.dxf_reader import entity_centroid

SIZE_PATTERN = re.compile(r"(\d+(?:\s+\d+/\d+)?|\d+/\d+)\s*(?:\"|นิ้ว|in)")


def _text_content(entity) -> str:
    dxftype = entity.dxftype()
    if dxftype == "MTEXT":
        return entity.text or ""
    if dxftype == "TEXT":
        return entity.dxf.text or ""
    return ""


def extract_size_label(text: str) -> str | None:
    """ดึงข้อความขนาดท่อ (เช่น 6", 3/4", 2 1/2") จากข้อความ ถ้าไม่พบคืน None"""
    m = SIZE_PATTERN.search(text)
    if not m:
        return None
    return f'{m.group(1)}"'


def _distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def detect_size_for_pipe(dim_entities: Iterable, pipe_entities: Iterable) -> str | None:
    """หาข้อความขนาดท่อใน layer Dim ที่อยู่ใกล้เส้นท่อ (pipe_entities) มากที่สุด

    คืน None ถ้าไม่มีข้อความขนาดท่อ หรือไม่มีเส้นท่อให้เทียบระยะ
    """
    pipe_points = [p for p in (entity_centroid(e) for e in pipe_entities) if p is not None]
    if not pipe_points:
        return None

    best_label: str | None = None
    best_dist: float | None = None
    for e in dim_entities:
        label = extract_size_label(_text_content(e))
        if label is None:
            continue
        centroid = entity_centroid(e)
        if centroid is None:
            continue
        dist = min(_distance(centroid, p) for p in pipe_points)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_label = label

    return best_label

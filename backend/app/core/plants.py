"""นับจำนวนต้นไม้ - 4.7

- group  -> 1 group = 1 ต้น
- INSERT -> นับจำนวน INSERT
- CIRCLE -> นับจำนวน CIRCLE

ทุกกรณีต้องตัด legend ออกก่อนนับเสมอ (4.0)
"""
from __future__ import annotations

from app.core.legend import is_in_legend


def count_plant_group(layer_name: str, groups: dict[str, list], legend_bbox) -> tuple[int, int]:
    """นับจำนวน group ที่มี entity บน layer_name และไม่อยู่ใน legend

    คืน (จำนวนที่นับได้, จำนวนที่ตัดออกเพราะอยู่ใน legend)
    """
    counted = 0
    excluded = 0
    for members in groups.values():
        layer_members = [e for e in members if e.dxf.layer == layer_name]
        if not layer_members:
            continue
        if all(is_in_legend(e, legend_bbox) for e in layer_members):
            excluded += 1
        else:
            counted += 1
    return counted, excluded


def count_plant_by_dxftype(entities: list, legend_bbox, dxftype: str) -> tuple[int, int]:
    """นับจำนวน entity ชนิด dxftype (INSERT/CIRCLE) ที่ไม่อยู่ใน legend

    คืน (จำนวนที่นับได้, จำนวนที่ตัดออกเพราะอยู่ใน legend)
    """
    counted = 0
    excluded = 0
    for e in entities:
        if e.dxftype() != dxftype:
            continue
        if is_in_legend(e, legend_bbox):
            excluded += 1
        else:
            counted += 1
    return counted, excluded


def sanity_check(counts: dict[str, int], tolerance: float = 0.2) -> list[dict]:
    """เปรียบเทียบจำนวนต้นไม้แต่ละชนิด - เตือนถ้าต่างกันเกิน tolerance (สัดส่วน)

    เช่น ทุเรียน กับ โคก ในแปลงเดียวกันควรมีจำนวนใกล้เคียงกัน
    """
    warnings = []
    items = [(name, count) for name, count in counts.items() if count > 0]
    if len(items) < 2:
        return warnings

    max_name, max_count = max(items, key=lambda x: x[1])
    for name, count in items:
        if name == max_name:
            continue
        if max_count == 0:
            continue
        diff_ratio = abs(max_count - count) / max_count
        if diff_ratio > tolerance:
            warnings.append(
                {
                    "message": (
                        f"จำนวน '{name}' ({count}) กับ '{max_name}' ({max_count}) "
                        f"ต่างกันเกิน {tolerance:.0%} ในแปลงเดียวกันมักมีจำนวนใกล้เคียงกัน "
                        "ตรวจสอบว่าตัด legend หรือนับครบหรือไม่"
                    ),
                    "items": {name: count, max_name: max_count},
                }
            )
    return warnings

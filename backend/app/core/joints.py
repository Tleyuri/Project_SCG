"""นับข้อต่อ - รองรับ 3 รูปแบบที่ผู้ออกแบบวาด (4.5)

(ก) INSERT (block)  -> นับจำนวน INSERT ตรงๆ แม่นยำ
(ข) Group           -> นับจำนวน group ที่ entity หลักอยู่ใน layer นั้น แม่นยำ
(ค) เส้นดิบ (LINE/LWPOLYLINE) -> นับไม่ได้แม่น ต้องแจ้งเตือนผู้ใช้แทนการเดา
"""
from __future__ import annotations

from typing import Iterable


def count_inserts(entities: Iterable) -> int:
    """(ก) นับจำนวน INSERT (block reference)"""
    return sum(1 for e in entities if e.dxftype() == "INSERT")


def count_groups_for_layer(groups: dict[str, list], layer_name: str) -> int:
    """(ข) นับจำนวน group ที่มี entity อย่างน้อยหนึ่งตัวอยู่ใน layer ที่ระบุ"""
    count = 0
    for members in groups.values():
        if any(e.dxf.layer == layer_name for e in members):
            count += 1
    return count


def raw_line_warning(layer_name: str, entities: Iterable, label: str | None = None) -> dict:
    """(ค) สร้างคำเตือนสำหรับ layer ข้อต่อที่วาดเป็นเส้นดิบ - ห้ามเดาจำนวน

    คืน dict สำหรับแสดงผลในหน้าเว็บ พร้อมข้อเสนอแนะให้ผู้ใช้แก้ไข
    """
    entities = list(entities)
    return {
        "layer": layer_name,
        "label": label or layer_name,
        "entity_count": len(entities),
        "countable": False,
        "message": (
            f"layer '{label or layer_name}' วาดด้วยเส้นดิบ (LINE/LWPOLYLINE) "
            f"จำนวน {len(entities)} เส้น ระบบไม่สามารถนับจำนวนข้อต่อได้แม่นยำ "
            "(การ cluster ตามระยะให้ผลไม่นิ่ง) "
            "กรุณาวาดใหม่เป็น block (INSERT) หรือ group แล้วระบบจะนับให้อัตโนมัติ "
            "หรือกรอกจำนวนข้อต่อด้วยตนเอง"
        ),
        "suggested_action": "redraw_as_block_or_group_or_manual_count",
        "manual_count": None,
    }

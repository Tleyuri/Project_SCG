"""อ่านไฟล์ DXF: layer, entity, group และ bounding box ของ entity"""
from __future__ import annotations

from typing import Iterable

import ezdxf
from ezdxf import bbox as ezbbox
from ezdxf.document import Drawing


def load_dxf(path_or_stream) -> Drawing:
    """โหลดไฟล์ DXF จาก path หรือ file-like object"""
    return ezdxf.readfile(path_or_stream)


def list_layers(doc: Drawing) -> list[dict]:
    """คืนรายชื่อ layer ทั้งหมดพร้อมจำนวน entity ใน modelspace"""
    msp = doc.modelspace()
    counts: dict[str, int] = {}
    for e in msp:
        layer = e.dxf.layer
        counts[layer] = counts.get(layer, 0) + 1

    layers = []
    for layer in doc.layers:
        name = layer.dxf.name
        layers.append({"name": name, "entity_count": counts.get(name, 0)})

    # layer ที่มี entity แต่ไม่ได้ประกาศไว้ใน layer table (พบได้ในไฟล์จริง)
    declared = {l["name"] for l in layers}
    for name, count in counts.items():
        if name not in declared:
            layers.append({"name": name, "entity_count": count})

    return layers


def entities_by_layer(doc: Drawing, layer_name: str) -> list:
    """คืน entity ทั้งหมดใน modelspace ของ layer ที่ระบุ"""
    msp = doc.modelspace()
    return [e for e in msp if e.dxf.layer == layer_name]


def get_groups(doc: Drawing) -> dict[str, list]:
    """คืน dict ของ group name -> list ของ entity ในกลุ่มนั้น"""
    result: dict[str, list] = {}
    if doc.groups is None:
        return result
    for name, group in doc.groups:
        result[name] = list(group)
    return result


def entity_bbox(entity) -> tuple[float, float, float, float] | None:
    """คืน bounding box (xmin, ymin, xmax, ymax) ของ entity เดียว หรือ None ถ้าไม่มี geometry"""
    box = ezbbox.extents([entity], fast=True)
    if box is None or not box.has_data:
        return None
    return (box.extmin.x, box.extmin.y, box.extmax.x, box.extmax.y)


def entities_bbox(entities: Iterable) -> tuple[float, float, float, float] | None:
    """คืน bounding box รวมของ entity หลายตัว"""
    box = ezbbox.extents(entities, fast=True)
    if box is None or not box.has_data:
        return None
    return (box.extmin.x, box.extmin.y, box.extmax.x, box.extmax.y)


def entity_centroid(entity) -> tuple[float, float] | None:
    """คืนจุดกึ่งกลาง bounding box ของ entity"""
    box = entity_bbox(entity)
    if box is None:
        return None
    xmin, ymin, xmax, ymax = box
    return ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0)

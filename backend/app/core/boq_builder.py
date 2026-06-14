"""ประกอบผลการถอดวัสดุทั้งหมดเป็น BOQ ต่อพืช ตามกฎในข้อ 4

โมดูลนี้เป็นตัวเชื่อม core modules อื่นๆ (legend, pipes, joints, valves, plants)
เข้ากับ config (layer_mapping, pipe_sizes, price_table, settings)
"""
from __future__ import annotations

import logging
from typing import Any

from app.core import dxf_reader, joints, legend, pipe_size_detect, pipes, plants, valves

# role -> ชื่อ settings key สำหรับขนาดท่อที่ผู้ใช้กำหนดเอง (override การตรวจจับจาก Dim)
PIPE_SIZE_SETTING_KEYS = {
    "main": "pipe_size_main",
    "submain": "pipe_size_submain",
    "lateral": "pipe_size_lateral",
}

logger = logging.getLogger("boq_builder")


def _normalize_size(size: str | None) -> str | None:
    """ทำให้ขนาดท่อที่ผู้ใช้กรอกอยู่ในรูปแบบเดียวกับ price_table.json (ลงท้ายด้วย ")

    เช่น "6", "6 \"", " 2 1/2" -> '6"', '6"', '2 1/2"'
    """
    if size is None:
        return None
    s = size.strip()
    if not s:
        return None
    s = s.rstrip('"').strip()
    return f'{s}"'


def _find_price_item(price_table: dict, material_type: str, size: str | None = None, klass: str | None = None) -> dict:
    items = price_table.get("items", [])
    norm_size = _normalize_size(size)
    for it in items:
        if it["material_type"] == material_type and (norm_size is None or it["size"] == norm_size) and (
            klass is None or it["class"] == klass
        ):
            return it
    for it in items:
        if it["material_type"] == material_type and (norm_size is None or it["size"] == norm_size):
            return it
    return {
        "material_type": material_type,
        "size": norm_size or size or "-",
        "class": klass or "-",
        "name": f"{material_type} {norm_size or size or ''}".strip(),
        "unit": "ชิ้น",
        "price": 0,
        "mat_code": "",
        "needs_review": True,
    }


def _make_row(price_item: dict, qty: float, note: str = "") -> dict:
    price = price_item.get("price", 0) or 0
    return {
        "mat_code": price_item.get("mat_code", ""),
        "name": price_item.get("name", ""),
        "qty": qty,
        "unit": price_item.get("unit", ""),
        "note": note or ("ต้องตรวจสอบ/อัปเดตราคา" if price_item.get("needs_review") else ""),
        "unit_price": price,
        "total": round(qty * price, 2),
    }


def _entities_filtered(doc, layer_name: str, legend_bbox) -> tuple[list, int]:
    entities = dxf_reader.entities_by_layer(doc, layer_name)
    kept, excluded = legend.filter_legend(entities, legend_bbox)
    return kept, len(excluded)


def build_boq(
    doc,
    layer_mapping: dict,
    pipe_sizes: dict,
    price_table: dict,
    settings: dict,
    legend_bbox_override: tuple[float, float, float, float] | None = None,
) -> dict[str, Any]:
    """ถอดวัสดุทั้งหมดจาก doc และคืน BOQ + warnings ต่อพืช"""

    unit_scale = settings.get("drawing_unit_to_meter", 1.0)
    segment_length = settings.get("pipe_segment_length_m", 4.0)
    riser_height = settings.get("riser_height_m", 0.5)
    riser_size = settings.get("riser_pipe_size", '1/2"')
    valve_cluster_distance = settings.get("valve_cluster_distance", 8.0)
    legend_margin = settings.get("legend_margin", 5.0)
    legend_left_extent = settings.get("legend_left_extent", 60.0)

    warnings: list[dict] = []
    debug_log: list[str] = []

    # --- legend bbox -----------------------------------------------------
    dim_layer = layer_mapping.get("dim_layer", "Dim")
    dim_entities = dxf_reader.entities_by_layer(doc, dim_layer)

    if legend_bbox_override is not None:
        legend_bbox = legend_bbox_override
    else:
        legend_bbox = legend.compute_legend_bbox(
            dim_entities, margin=legend_margin, left_extent=legend_left_extent
        )
    debug_log.append(f"legend_bbox = {legend_bbox}")

    # ข้อความ Dim ที่อยู่นอก legend - ใช้ตรวจจับขนาดท่อ (เมน/ย่อย/แยก) เป็นค่าเริ่มต้น
    dim_kept, _ = legend.filter_legend(dim_entities, legend_bbox)

    groups = dxf_reader.get_groups(doc)

    # --- ถนน (สำหรับตรวจ class 13.5) -------------------------------------
    road_entities: list = []
    for road_layer in layer_mapping.get("road_layers", []):
        kept, _ = _entities_filtered(doc, road_layer, legend_bbox)
        road_entities.extend(kept)

    # --- จัดกลุ่ม pipe layer ตาม (plant, role) ----------------------------
    pipe_layers_by_plant: dict[str, dict[str, str]] = {}
    for layer_name, info in layer_mapping.get("pipe_layers", {}).items():
        plant = info["plant"]
        role = info["role"]
        pipe_layers_by_plant.setdefault(plant, {})[role] = layer_name

    plants_set = set(pipe_layers_by_plant.keys())
    for info in layer_mapping.get("sprinkler_layers", {}).values():
        plants_set.add(info["plant"])
    for info in layer_mapping.get("plant_layers", {}).values():
        plants_set.add(info["plant"])

    result_plants: dict[str, Any] = {}

    for plant_name in plants_set:
        rows: list[dict] = []
        plant_pipe_sizes = pipe_sizes.get(plant_name, {})
        pipe_layers = pipe_layers_by_plant.get(plant_name, {})

        # entities per role - เก็บไว้ใช้หา nearest pipe สำหรับชุดวาล์วด้วย
        pipe_entities_by_role: dict[str, list] = {}

        for role, layer_name in pipe_layers.items():
            kept, excluded_count = _entities_filtered(doc, layer_name, legend_bbox)
            pipe_entities_by_role[role] = kept
            debug_log.append(
                f"[{plant_name}] layer '{layer_name}' (role={role}): "
                f"{len(kept)} entities (ตัด legend ออก {excluded_count})"
            )

            size_class = plant_pipe_sizes.get(role, {})
            size = size_class.get("size", "-")
            klass = size_class.get("class", "8.5")

            # ขนาดท่อเมน/ย่อย/แยก: ใช้ค่าที่ผู้ใช้กำหนดเอง > ตรวจจับจาก layer Dim > ค่าใน pipe_sizes.json
            setting_key = PIPE_SIZE_SETTING_KEYS.get(role)
            if setting_key:
                user_size = (settings.get(setting_key) or "").strip()
                if user_size:
                    size = _normalize_size(user_size)
                else:
                    detected = pipe_size_detect.detect_size_for_pipe(dim_kept, kept)
                    if detected:
                        size = detected
                        debug_log.append(
                            f"[{plant_name}] role={role}: ตรวจจับขนาดท่อจาก layer Dim = {detected}"
                        )

            if role == "main" and road_entities:
                normal_len, road_len = pipes.split_length_by_road(kept, road_entities)
                normal_len *= unit_scale
                road_len *= unit_scale
                if normal_len > 0:
                    cnt = pipes.pipe_count(normal_len, segment_length)
                    item = _find_price_item(price_table, "ท่อประปา", size, klass)
                    rows.append(
                        _make_row(item, cnt, note=f"ขนาด {size} ชั้น {klass} รวมยาว {normal_len:.2f} ม.")
                    )
                if road_len > 0:
                    cnt = pipes.pipe_count(road_len, segment_length)
                    item = _find_price_item(price_table, "ท่อประปา", size, "13.5")
                    rows.append(
                        _make_row(
                            item, cnt,
                            note=f"ขนาด {size} ชั้น 13.5 ช่วงผ่านถนน รวมยาว {road_len:.2f} ม.",
                        )
                    )
            else:
                total_len = pipes.total_length(kept) * unit_scale
                if total_len <= 0:
                    continue
                cnt = pipes.pipe_count(total_len, segment_length)
                material_type = "ท่อประปา" if klass == "8.5" else "ท่อเกษตร"
                item = _find_price_item(price_table, material_type, size, klass)
                rows.append(
                    _make_row(item, cnt, note=f"ขนาด {size} ชั้น {klass} รวมยาว {total_len:.2f} ม.")
                )

        # --- สปริงเกอร์ + อุปกรณ์ต่อหัว (4.4) + ท่อตั้ง (4.3) -------------
        sprinkler_count = 0
        for layer_name, info in layer_mapping.get("sprinkler_layers", {}).items():
            if info["plant"] != plant_name:
                continue
            kept, excluded_count = _entities_filtered(doc, layer_name, legend_bbox)
            cnt, _ = plants.count_plant_by_dxftype(kept, None, "CIRCLE")
            sprinkler_count += cnt
            debug_log.append(
                f"[{plant_name}] layer '{layer_name}' (สปริงเกอร์): {cnt} หัว "
                f"(ตัด legend ออก {excluded_count})"
            )

        if sprinkler_count > 0:
            rows.append(_make_row(_find_price_item(price_table, "หัวสปริงเกอร์"), sprinkler_count))
            rows.append(
                _make_row(_find_price_item(price_table, "ข้องอ90ลด", '3/4x1/2"'), sprinkler_count)
            )
            rows.append(
                _make_row(
                    _find_price_item(price_table, "วาล์วหรี่เกลียวนอก", '1/2"'), sprinkler_count
                )
            )

            riser_cnt = pipes.riser_count(sprinkler_count, riser_height, segment_length)
            riser_item = _find_price_item(price_table, "ท่อประปา", riser_size, "8.5")
            rows.append(
                _make_row(
                    riser_item,
                    riser_cnt,
                    note=f"ท่อตั้ง {sprinkler_count} หัว x {riser_height} ม.",
                )
            )

        # --- ข้อต่อแบบ INSERT (4.5 ก) ------------------------------------
        for layer_name, info in layer_mapping.get("joint_insert_layers", {}).items():
            if info.get("plant") != plant_name:
                continue
            entities = dxf_reader.entities_by_layer(doc, layer_name)
            if not entities:
                continue
            kept, excluded_count = legend.filter_legend(entities, legend_bbox)
            cnt = joints.count_inserts(kept)
            if cnt == 0:
                # อาจวาดเป็น group แทน
                cnt = joints.count_groups_for_layer(groups, layer_name)
            if cnt == 0:
                continue
            label = info.get("name_th", layer_name)
            item = _find_price_item(price_table, label)
            rows.append(_make_row(item, cnt, note=f"layer '{layer_name}'"))
            debug_log.append(f"[{plant_name}] layer '{layer_name}': {cnt} ตัว (INSERT/group)")

        # --- ข้อต่อแบบเส้นดิบ (4.5 ค) - แจ้งเตือนเท่านั้น ------------------
        for layer_name, info in layer_mapping.get("joint_raw_layers", {}).items():
            if info.get("plant") != plant_name:
                continue
            entities = dxf_reader.entities_by_layer(doc, layer_name)
            if not entities:
                continue
            kept, _ = legend.filter_legend(entities, legend_bbox)
            if not kept:
                continue
            warnings.append(joints.raw_line_warning(layer_name, kept, info.get("name_th")))

        # --- ชุดวาล์ว (4.6) ------------------------------------------------
        for layer_name, info in layer_mapping.get("valve_layers", {}).items():
            if info["plant"] != plant_name:
                continue
            entities = dxf_reader.entities_by_layer(doc, layer_name)
            kept, _ = legend.filter_legend(entities, legend_bbox)
            bowties = valves.find_bowties(kept, vertex_count=settings.get("bowtie_vertex_count", 4))
            clusters = valves.classify_valve_clusters(bowties, valve_cluster_distance)

            single_count = sum(1 for c in clusters if c["type"] == "single")
            double_count = sum(1 for c in clusters if c["type"] == "double")
            if clusters:
                debug_log.append(
                    f"[{plant_name}] layer '{layer_name}': ชุดวาล์ว {len(clusters)} จุด "
                    f"(เดี่ยว {single_count}, คู่ {double_count})"
                )

            # รวมจำนวนอุปกรณ์ตามขนาดท่อที่จุดวาล์วตั้งอยู่
            elbow45_by_size: dict[str, int] = {}
            ballvalve_by_size: dict[str, int] = {}
            saddle_by_size: dict[str, int] = {}
            airvalve_by_size: dict[str, int] = {}
            quad_cap_count = 0

            for cluster in clusters:
                if cluster["type"] == "unknown":
                    warnings.append(
                        {
                            "layer": layer_name,
                            "label": "วาล์ว",
                            "message": (
                                f"พบกลุ่มนาฬิกาทรายซ้อนกัน {cluster['count']} อันที่ตำแหน่ง "
                                f"{cluster['center']} (คาดว่าเป็นวาล์วเดี่ยวหรือคู่เท่านั้น) "
                                "กรุณาตรวจสอบด้วยตนเอง"
                            ),
                            "countable": False,
                        }
                    )
                    continue

                role = valves.nearest_pipe_role(cluster["center"], pipe_entities_by_role)
                size = plant_pipe_sizes.get(role, {}).get("size", "-") if role else "-"

                multiplier = 1 if cluster["type"] == "single" else 2
                elbow45_by_size[size] = elbow45_by_size.get(size, 0) + 4
                ballvalve_by_size[size] = ballvalve_by_size.get(size, 0) + multiplier
                saddle_by_size[size] = saddle_by_size.get(size, 0) + multiplier
                airvalve_by_size[size] = airvalve_by_size.get(size, 0) + multiplier
                if cluster["type"] == "double":
                    quad_cap_count += 1

            for size, qty in elbow45_by_size.items():
                rows.append(_make_row(_find_price_item(price_table, "ข้องอ45", size), qty))
            for size, qty in ballvalve_by_size.items():
                rows.append(_make_row(_find_price_item(price_table, "บอลวาล์ว", size), qty))
            for size, qty in saddle_by_size.items():
                rows.append(_make_row(_find_price_item(price_table, "รัดแยก", size), qty))
            for size, qty in airvalve_by_size.items():
                rows.append(_make_row(_find_price_item(price_table, "แอร์วาล์ว", size), qty))
            if quad_cap_count > 0:
                rows.append(
                    _make_row(_find_price_item(price_table, "สี่ทางฝาครอบ", "2\""), quad_cap_count)
                )

        # --- พืช (4.7) -----------------------------------------------------
        plant_counts: dict[str, dict] = {}
        for layer_name, info in layer_mapping.get("plant_layers", {}).items():
            if info["plant"] != plant_name:
                continue
            method = info.get("method")
            entities = dxf_reader.entities_by_layer(doc, layer_name)

            if method == "group":
                counted, excluded = plants.count_plant_group(layer_name, groups, legend_bbox)
            elif method == "insert":
                kept, _ = legend.filter_legend(entities, legend_bbox)
                counted, excluded = plants.count_plant_by_dxftype(kept, legend_bbox, "INSERT")
            elif method == "circle":
                kept, _ = legend.filter_legend(entities, legend_bbox)
                counted, excluded = plants.count_plant_by_dxftype(kept, legend_bbox, "CIRCLE")
            else:
                counted, excluded = 0, 0

            plant_counts[layer_name] = {"count": counted, "excluded_legend": excluded}
            debug_log.append(
                f"[{plant_name}] layer '{layer_name}' (พืช, method={method}): "
                f"{counted} ต้น (ตัด legend ออก {excluded})"
            )

        if plant_counts:
            sanity = plants.sanity_check({k: v["count"] for k, v in plant_counts.items()})
            warnings.extend(sanity)

        if not rows and not plant_counts:
            continue

        result_plants[plant_name] = {"rows": rows, "plant_counts": plant_counts}

    return {
        "plants": result_plants,
        "warnings": warnings,
        "legend_bbox": legend_bbox,
        "debug_log": debug_log,
    }

from app import config_loader
from app.core import boq_builder, excel_export


def _configs():
    return (
        config_loader.load_layer_mapping(),
        config_loader.load_pipe_sizes(),
        config_loader.load_price_table(),
        config_loader.load_settings(),
    )


def test_build_boq_durian_count_excludes_legend(sample_doc):
    layer_mapping, pipe_sizes, price_table, settings = _configs()
    result = boq_builder.build_boq(sample_doc, layer_mapping, pipe_sizes, price_table, settings)

    durian = result["plants"]["ทุเรียน"]
    # จุดที่ต้อง assert: ทุเรียน = 133 (ไม่ใช่ 134) -> พิสูจน์ว่าตัด legend ของพืชถูกต้อง
    assert durian["plant_counts"]["ทุเรียน"]["count"] == 133
    assert durian["plant_counts"]["ทุเรียน"]["excluded_legend"] == 1


def test_build_boq_main_pipe_includes_arc_length(sample_doc):
    layer_mapping, pipe_sizes, price_table, settings = _configs()
    result = boq_builder.build_boq(sample_doc, layer_mapping, pipe_sizes, price_table, settings)

    rows = result["plants"]["ทุเรียน"]["rows"]
    main_pipe_row = next(r for r in rows if "ขนาด 6 นิ้ว" in r["name"] and "13.5" not in r["name"])

    # ความยาวรวม = 40 (LINE) + 10*pi/2 (ARC) ~= 55.71 -> ceil(55.71/4) = 14 ท่อน
    assert main_pipe_row["qty"] == 14
    assert "55.7" in main_pipe_row["note"]


def test_build_boq_raw_line_joint_warning(sample_doc):
    layer_mapping, pipe_sizes, price_table, settings = _configs()
    result = boq_builder.build_boq(sample_doc, layer_mapping, pipe_sizes, price_table, settings)

    raw_warnings = [w for w in result["warnings"] if w.get("layer") == "สามทางฝา"]
    assert len(raw_warnings) == 1
    assert raw_warnings[0]["countable"] is False
    assert raw_warnings[0]["entity_count"] == 2


def test_build_boq_sprinkler_and_riser(sample_doc):
    layer_mapping, pipe_sizes, price_table, settings = _configs()
    result = boq_builder.build_boq(sample_doc, layer_mapping, pipe_sizes, price_table, settings)

    rows = result["plants"]["ทุเรียน"]["rows"]
    sprinkler_row = next(r for r in rows if r["name"] == "หัวสปริงเกอร์มินิ")
    assert sprinkler_row["qty"] == 5

    riser_row = next(r for r in rows if "1/2 นิ้ว" in r["name"] and r["unit_price"] == 50.50)
    # riser_count(5, 0.5, 4) = ceil(2.5/4) = 1
    assert riser_row["qty"] == 1


def test_build_boq_valve_clusters(sample_doc):
    layer_mapping, pipe_sizes, price_table, settings = _configs()
    result = boq_builder.build_boq(sample_doc, layer_mapping, pipe_sizes, price_table, settings)

    rows = result["plants"]["ทุเรียน"]["rows"]
    elbow45 = next(r for r in rows if "ข้องอ 45" in r["name"])
    ballvalve = next(r for r in rows if "บอลวาล์ว" in r["name"])
    quad_cap = next(r for r in rows if "สี่ทางฝาครอบ" in r["name"])

    # 1 เดี่ยว (x4) + 1 คู่ (x4) = 8
    assert elbow45["qty"] == 8
    # 1 เดี่ยว (x1) + 1 คู่ (x2) = 3
    assert ballvalve["qty"] == 3
    assert quad_cap["qty"] == 1


def test_build_boq_no_duplicate_joints_across_plants(sample_doc):
    layer_mapping, pipe_sizes, price_table, settings = _configs()
    result = boq_builder.build_boq(sample_doc, layer_mapping, pipe_sizes, price_table, settings)

    elbow_rows_total = 0
    for plant_data in result["plants"].values():
        elbow_rows_total += sum(
            1 for r in plant_data["rows"] if r["name"] == "ข้องอ 90° ลด-หนา ฟ้า 3/4x1/2 นิ้ว" and r["qty"] == 3
        )
    assert elbow_rows_total == 1


def test_excel_export_builds_workbook(sample_doc):
    layer_mapping, pipe_sizes, price_table, settings = _configs()
    result = boq_builder.build_boq(sample_doc, layer_mapping, pipe_sizes, price_table, settings)

    xlsx_bytes = excel_export.build_workbook(result["plants"], garden_location="เชียงใหม่", garden_phone="08x")
    assert xlsx_bytes[:2] == b"PK"  # xlsx เป็น zip archive
    assert len(xlsx_bytes) > 1000

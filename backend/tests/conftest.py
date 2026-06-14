import ezdxf
import pytest


def _add_bowtie(msp, ox, oy, layer):
    points = [(ox, oy), (ox + 1, oy + 1), (ox + 1, oy), (ox, oy + 1)]
    pl = msp.add_lwpolyline(points, format="xy", dxfattribs={"layer": layer})
    pl.closed = True
    return pl


@pytest.fixture()
def sample_doc():
    """สร้างไฟล์ DXF จำลองครอบคลุม:
    - ท่อเมน (LINE + ARC) บน layer "ท่อ"
    - legend ฝั่งขวา (x สูง) อ้างอิงจาก layer "Dim"
    - ทุเรียน 133 ต้น (group) ในแปลง + 1 ต้นใน legend (ต้องตัดออก)
    - โคก 133 ต้น (circle) ในแปลง + 1 ต้นใน legend
    - สปิงเกลอร์ 5 หัว
    - งอ90 ลด (INSERT) 3 ตัวในแปลง + 1 ตัวใน legend
    - สามทางฝา (เส้นดิบ) 2 เส้น -> ต้องแจ้งเตือน
    - วาร์ล: 1 วาล์วเดี่ยว + 1 วาล์วคู่ (bowtie clusters)
    """
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    # --- legend marker: Dim text ทางขวาของแบบ ---
    for i, y in enumerate(range(0, 50, 10)):
        msp.add_text(f"LABEL{i}", dxfattribs={"layer": "Dim", "insert": (200, y)}).set_placement(
            (200, y)
        )
    msp.add_text("LABEL_END", dxfattribs={"layer": "Dim"}).set_placement((220, 45))

    # --- ท่อเมน: LINE + ARC (รวม ARC ต้องถูกนับ) ---
    msp.add_line((0, 0), (40, 0), dxfattribs={"layer": "ท่อ"})
    msp.add_arc(center=(50, 0), radius=10, start_angle=0, end_angle=90, dxfattribs={"layer": "ท่อ"})
    # legend example (สั้น, อยู่ในกรอบ legend) -> ต้องตัดออก
    msp.add_line((190, 10), (192, 10), dxfattribs={"layer": "ท่อ"})

    # --- ทุเรียน: 133 ต้นในแปลง (group) + 1 ต้นใน legend ---
    for i in range(133):
        x = (i % 20) * 4
        y = (i // 20) * 4
        c = msp.add_circle((x, y), 0.3, dxfattribs={"layer": "ทุเรียน"})
        g = doc.groups.new(name=f"DURIAN_{i}")
        g.extend([c])

    legend_durian = msp.add_circle((180, 20), 0.3, dxfattribs={"layer": "ทุเรียน"})
    g = doc.groups.new(name="DURIAN_LEGEND")
    g.extend([legend_durian])

    # --- โคก: 133 ต้นในแปลง (circle) + 1 ใน legend ---
    for i in range(133):
        x = (i % 20) * 4 + 1
        y = (i // 20) * 4 + 1
        msp.add_circle((x, y), 0.2, dxfattribs={"layer": "โคก"})
    msp.add_circle((185, 25), 0.2, dxfattribs={"layer": "โคก"})

    # --- สปิงเกลอร์: 5 หัว ---
    for i in range(5):
        msp.add_circle((i * 5, 5), 0.1, dxfattribs={"layer": "สปิงเกลอร์"})

    # --- งอ90 ลด: INSERT 3 ตัวในแปลง + 1 ใน legend ---
    block = doc.blocks.new(name="ELBOW90")
    block.add_circle((0, 0), 0.2)
    for i in range(3):
        msp.add_blockref("ELBOW90", (i * 3, 20), dxfattribs={"layer": "งอ90 ลด"})
    msp.add_blockref("ELBOW90", (190, 15), dxfattribs={"layer": "งอ90 ลด"})

    # --- สามทางฝา: เส้นดิบ 2 เส้น -> ต้องแจ้งเตือน ---
    msp.add_line((0, 30), (1, 30), dxfattribs={"layer": "สามทางฝา"})
    msp.add_line((1, 30), (1, 31), dxfattribs={"layer": "สามทางฝา"})

    # --- วาร์ล: 1 เดี่ยว + 1 คู่ (ใกล้ท่อเมนเพื่อให้ได้ size "main") ---
    _add_bowtie(msp, 10, 50, "วาร์ล")  # single
    _add_bowtie(msp, 30, 60, "วาร์ล")  # double - point 1
    _add_bowtie(msp, 30, 61, "วาร์ล")  # double - point 2 (ใกล้กัน < 8 หน่วย)

    return doc

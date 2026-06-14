import ezdxf

from app.core.pipe_size_detect import detect_size_for_pipe, extract_size_label


def test_extract_size_label_variants():
    assert extract_size_label('ท่อเมน 6" ชั้น 8.5') == '6"'
    assert extract_size_label("ท่อย่อย 2 1/2 นิ้ว") == '2 1/2"'
    assert extract_size_label("ท่อแยก 3/4in") == '3/4"'
    assert extract_size_label("ไม่มีขนาด") is None


def test_detect_size_for_pipe_picks_nearest_text():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    main_pipe = msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "ท่อ"})
    sub_pipe = msp.add_line((0, 100), (10, 100), dxfattribs={"layer": "ท่อย่อย"})

    msp.add_text('6"', dxfattribs={"layer": "Dim", "insert": (5, 1)})
    msp.add_text('4"', dxfattribs={"layer": "Dim", "insert": (5, 101)})

    dim_entities = list(msp.query('TEXT[layer=="Dim"]'))

    assert detect_size_for_pipe(dim_entities, [main_pipe]) == '6"'
    assert detect_size_for_pipe(dim_entities, [sub_pipe]) == '4"'


def test_detect_size_for_pipe_returns_none_without_match():
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    main_pipe = msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "ท่อ"})

    assert detect_size_for_pipe([], [main_pipe]) is None

from app.core import dxf_reader, legend


def test_compute_legend_bbox_and_filter(sample_doc):
    dim_entities = dxf_reader.entities_by_layer(sample_doc, "Dim")
    bbox = legend.compute_legend_bbox(dim_entities, margin=5.0, left_extent=60.0)
    assert bbox is not None

    durian_entities = dxf_reader.entities_by_layer(sample_doc, "ทุเรียน")
    kept, excluded = legend.filter_legend(durian_entities, bbox)

    assert len(excluded) == 1  # legend symbol ที่ (180, 20)
    assert len(kept) == 133


def test_no_legend_when_dim_layer_empty(sample_doc):
    bbox = legend.compute_legend_bbox([], margin=5.0, left_extent=60.0)
    assert bbox is None

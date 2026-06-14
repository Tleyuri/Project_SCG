from app.core import dxf_reader, valves


def test_find_bowties_and_classify(sample_doc):
    entities = dxf_reader.entities_by_layer(sample_doc, "วาร์ล")
    bowties = valves.find_bowties(entities, vertex_count=4)
    assert len(bowties) == 3  # 1 เดี่ยว + 2 ของวาล์วคู่

    clusters = valves.classify_valve_clusters(bowties, max_dist=8.0)
    types = sorted(c["type"] for c in clusters)
    assert types == ["double", "single"]

    single = next(c for c in clusters if c["type"] == "single")
    double = next(c for c in clusters if c["type"] == "double")
    assert single["count"] == 1
    assert double["count"] == 2


def test_nearest_pipe_role(sample_doc):
    main_entities = dxf_reader.entities_by_layer(sample_doc, "ท่อ")
    pipe_entities_by_role = {"main": main_entities, "submain": [], "lateral": [], "feeder": []}

    role = valves.nearest_pipe_role((10, 50), pipe_entities_by_role)
    assert role == "main"


def test_cluster_points_distance_threshold():
    points = [(0, 0), (1, 0), (100, 100)]
    clusters = valves.cluster_points(points, max_dist=8.0)
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [1, 2]

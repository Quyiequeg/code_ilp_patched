from src.ordering import native_order

def test_native_order(sample_graph):
    nodes = list(sample_graph.nodes(data="subset"))
    result = native_order(nodes)
    assert isinstance(result, list)
    assert len(result) == 3
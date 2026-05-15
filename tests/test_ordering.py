from src.ordering import cyclic_ordering

def test_cyclic_ordering(sample_graph):
    nodes = list(sample_graph.nodes(data="subset"))
    result = cyclic_ordering(nodes)
    assert isinstance(result, list)
    assert len(result) == 3
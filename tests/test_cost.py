from src.cost import cost_function_whole

def test_cost_function_whole_default_ordering(sample_graph):
    from src.ordering import native_order, node_groups
    nodes = list(sample_graph.nodes(data="subset"))
    edges = list(sample_graph.edges())
    node_grps = node_groups(nodes)
    ordering_default = native_order(nodes)
    cost_default = cost_function_whole(ordering_default, node_grps, edges)
    assert isinstance(cost_default, int)
    assert cost_default == 300

def test_cost_function_whole_phantom_axis(sample_graph):
    from src.ordering import node_groups
    nodes = list(sample_graph.nodes(data="subset"))
    edges = list(sample_graph.edges())
    node_grps = node_groups(nodes)
    ordering_shuffled_plus_phantom = [2, 0, 1, 4]
    cost_shuffled = cost_function_whole(ordering_shuffled_plus_phantom, node_grps, edges)
    assert isinstance(cost_shuffled, int)
    assert cost_shuffled == 400
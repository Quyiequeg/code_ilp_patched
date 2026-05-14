def cyclic_ordering(nodes): # phi, zyklische achsenanordnung
    """Bekommt einen NodeView übergeben und wandelt diese über ein Set in eine Liste um, die alle Subsetnumnern enthält. Diese Subsets spiegeln die Achsen wieder. Die Liste spiegelt also die zyklische Achsenanordnung wieder.

    Args:
        nodes (NodeDataView): siehe networkx.graph.nodes

    Returns:
        list: zyklische Achsenanordnung mit Achsennummern
    """
    ordered_set = set(t[1] for t in nodes) # zweites tupel-element ist subset
    ordered_list = list(ordered_set)
    return ordered_list

def node_groups(nodes): # alpha, Mapping von Knoten zu Achsengruppen
    """Erzeugt ein Dict wobei jeder Key ein Subset ist dem eine Liste aus zughörigen Knoten zugeordnet wird.


    Args:
        nodes (NodeView): Liste aus Tupeln (KnotenID, Subset)

    Returns:
        dict: key: int, value: list
        {0: [0, 1, 2, 3...], ...} 
    """
    node_groups: dict[int, list[int]] = {}
    for node, subset in nodes:
        if subset not in node_groups:
            node_groups[subset] = []
        node_groups[subset].append(node)
    return node_groups

def node_to_axis(node, node_grps): # alpha(u)
    """Gibt an auf welcher Achse sich ein Knoten befindet.

    Args:
        node (int): Knoten ID
        node_grps (dict): key: subset, value: list

    Raises:
        ValueError: Der Knoten kann keiner Achse zugeordnet werden.

    Returns:
        int: Achsen ID
    """
    axis = None
    for subset, nds in node_grps.items():
        if node in nds:
            axis = subset
            break
    if axis is None:
        raise ValueError(f"Knoten {node} keiner Achse zugeordnet.")
    else:
        return axis
    
if __name__ == "__main__":
    # Aufbau der Testdaten
    from src.graphs import sample_graph
    G = sample_graph()
    nodes = list(G.nodes(data="subset"))
    edges = list(G.edges())
    phi = cyclic_ordering(nodes)
    node_grps = node_groups(nodes)
    print("##########################################")
    print("nodes:", nodes)
    print("phi:", phi)
    print("node_grps:", node_grps)
    print("##########################################")
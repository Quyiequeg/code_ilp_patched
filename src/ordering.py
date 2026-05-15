from itertools import permutations

from src.graphs import sample_graph_selfconstructed

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
    
def brute_force_ordering(ordering: list[int], node_grps: dict, edges: list) -> tuple[int, tuple[int, ...]]:
    from src.cost import cost_function_whole
    permutations_ordering = list(permutations(ordering))
    minimized_cost = float('inf') # init
    optimal_perm = None # init
    for perm in permutations_ordering:
        cost = cost_function_whole(perm, node_grps, edges)
        print(f"Permutation: {perm}, Kosten: {cost}") # debugging
        if cost < minimized_cost:
            minimized_cost = cost
            optimal_perm = perm
    return minimized_cost, optimal_perm

if __name__ == "__main__":
    # Aufbau der Testdaten
    from src.graphs import sample_graph_multipartite, sample_graph_caveman, sample_graph_selfconstructed
    from src.partitioning import clauset_newman_moore_communities, louvain_community_detection
    G = sample_graph_multipartite()
    CG = sample_graph_caveman(4, 10)
    SC = sample_graph_selfconstructed()
    pipeline_test = 1
    if pipeline_test == 1:
        edges = list(SC.edges())
        nodes = list(SC.nodes(data="subset"))
        phi = cyclic_ordering(nodes)
        node_grps = node_groups(nodes)
        print("##########################################")
        print(">>>> Pipeline Test")
        print("nodes:", nodes)
        print("phi:", phi)
        print("node_grps:", node_grps)
        print("##########################################")
        print(brute_force_ordering(phi, node_grps, edges))
        print("##########################################")        
        # edges = list(SC.edges())
        # comm_graph_cnm = clauset_newman_moore_communities(SC)
        # first_phi = []
        # for i in range(len(comm_graph_cnm)):
        #     first_phi.append(i)
        # print(first_phi)
        # # comm_graph_louvain = louvain_community_detection(CG)
        # print(brute_force_ordering(first_phi, comm_graph_cnm, edges))
        # # print("Communities (Louvain):", comm_graph_louvain)     
        # print("##########################################")

    else:
        nodes = list(G.nodes(data="subset"))
        edges = list(G.edges())
        phi = cyclic_ordering(nodes)
        node_grps = node_groups(nodes)
        print("##########################################")
        print("nodes:", nodes)
        print("phi:", phi)
        print("node_grps:", node_grps)
        print("##########################################")
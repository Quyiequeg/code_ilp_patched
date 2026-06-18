from itertools import permutations
from graphs import sample_graph_selfconstructed
from hiveplot import HivePlotLayout

def native_order(nodes):
    """Bekommt einen NodeView übergeben und wandelt diese über ein Set in eine Liste um, die alle Subsetnumnern enthält. Diese Subsets spiegeln die Achsen wieder. Die Liste dient als Initialisierung zur Berechnung von Phi. Es handelt sich als o

    Args:
        nodes (NodeDataView): siehe networkx.graph.nodes

    Returns:
        list: zyklische Achsenanordnung mit Achsen-IDs
    """
    ordered_set = set(t[1] for t in nodes) # zweites tupel-element ist subset
    ordered_list = list(ordered_set)
    return ordered_list

def node_groups(nodes: list[tuple[int, int]], ): # alpha, Mapping von Knoten zu Achsengruppen
    """Erzeugt ein Dict wobei jeder Key ein Subset ist dem eine Liste aus zughörigen Knoten zugeordnet wird. Es handelt sich hierbei um die Funktion alpha.


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

def node_to_axis_maps(layout: HivePlotLayout, fused_node_groups: dict[int, list[int | str]]) -> tuple[dict[int | str, int],  dict[int | str, int]]: # alpha(u)
    """Die Funktion berechnet zwei Maps um für einen gegeben Knoten sehr schnell 1. alpha(Knoten) und 2. phi[alpha(Knoten)] zu bestimmen.

    Args:
        layout (HivePlotLayout): Das Hiveplotlayout
        fused_node_groups (dict[int, list[int  |  str]]): Achse: Knotenliste (virtuell und real)

    Returns:
        tuple[dict[int | str, int],  dict[int | str, int]]: Knoten: Achse & Knoten: Achsenposition in Phi
    """
    phi = layout.axis_order
    axis_index_map = {}
    node_axis_map = {}
    node_position_map = {}
    index = 0
    for axis in phi:
        axis_index_map[axis] = index
        index += 1
    for key in fused_node_groups:
        for node in fused_node_groups[key]:
            node_position_map[node] = axis_index_map[key]
            node_axis_map[node] = key
    return node_position_map, node_axis_map

def node_to_axis(node, node_grps, position = False): # alpha(u)
    """Gibt an auf welcher Achse sich ein Knoten befindet. Funktion wird nur zum Initialisieren verwendet. Für Iterationen in der Pipeline ist sie nicht performant. Dafür werden Mappings benutzt (z.B. siehe ordering.node_to_axis_maps)

    Args:
        node (int): Knoten ID
        node_grps (dict): key: Achse, value: Knoten
        position (bool): Rückgabe der Achse, true Rückgabe der Position der Achse in der Achsenordnung (phi). False ist default.        

    Raises:
        ValueError: Der Knoten kann keiner Achse zugeordnet werden.

    Returns:
        int: Achsen ID
    """
    axis = None
    for axes, nodes in node_grps.items():
        if node in nodes:
            axis = axes
            break
    if axis is None:
        raise ValueError(f"Knoten {node} keiner Achse zugeordnet.")
    elif position == False:
        return axis
    elif position == True:
        return list(node_grps.keys()).index(axis)

def brute_force_ordering(ordering: list[int], node_grps: dict, edges: list) -> tuple[int, ...]:
    """Für kleine k und zum Entwickeln der Pipeline vermeide ich zuerst die Auseinandersetzung mit dem Solver.
    Diese Funktion dient dem schnellen Berechnen von Pipelineschritt 2: günstigste Achsenanordnung finden. 

    Args:
        ordering (list[int]): aktuelle Achsenordnung (phi)
        node_grps (dict): key: Achse, value: Knoten
        edges (list): Knotenliste

    Returns:
        tuple[int, ...]: _description_
    """
    from cost import cost_function_whole
    permutations_ordering = list(permutations(ordering))
    minimized_cost = float('inf') # init
    optimal_perm = None # init
    for perm in permutations_ordering:
        cost = cost_function_whole(perm, node_grps, edges)
        # print(f"Permutation: {perm}, Kosten: {cost}") # debugging
        if cost < minimized_cost:
            minimized_cost = cost
            optimal_perm = perm
    # print(f"Optimale Permutation: {optimal_perm}, Minimierte Kosten: {minimized_cost}") # debugging
    return optimal_perm

def reordered_node_groups(node_grps: dict[int, list[int]], new_order: tuple[int, ...]) -> dict[int, list[int]]: # ermöglicht schnelles umordnen nach optimierung der achsenordnung
    """Schnelles Umordnen nach Optimierung der Achsenordnung."""
    return {axis: node_grps[axis] for axis in new_order}

def ip_ordering(layout: HivePlotLayout) -> list[int]:
    import pulp as pp
    from cost import (
        edges_between_axes,
        node_or_axes_span,
        cost_function_whole
    )

    def ilp_objective_function(partition_to_axis: dict, y: dict, axes_weights: dict, phi: list, k: int) -> pp.lpSum:
        """Funktion ermittelt die Terme der Zielfunktion und gibt die Zielfunktion zurück."""
        objectives = []
        for i in phi:
            for j in phi:
                if i == j:
                    continue
                for l in range(k):
                    for h in range(k):
                        if l == h:
                            continue
                        objective = y[(i, j, l, h)] * node_or_axes_span(l, h, k) * axes_weights.get((i, j), 0)
                        objectives.append(objective)
        return pp.lpSum(objectives)

    phi = layout.axis_order
    k = layout.num_axes
    node_groups = layout.node_groups
    edges = layout.edges()
    axes_weights = {}
    for i in range(k):
        for j in range(i + 1, k):
            weight = edges_between_axes(node_groups, edges, phi[i], phi[j])
            axes_weights[(phi[i], phi[j])] = weight
            axes_weights[(phi[j], phi[i])] = weight
    # probleminstanz initialisieren
    prob = pp.LpProblem("ILP_AxisOrdering", pp.LpMinimize)
    # Variablen initialisieren
    partition_to_axis = {}
    for axis in phi:
        for j in range(k):
            partition_to_axis[(axis, j)] = pp.LpVariable(f"x_{axis}_{j}", cat="Binary")
    # Hilfsvariablen y[(i,j,l,h)] = x[(i,l)] * x[(j,h)]
    y = {}
    for i in phi:
        for j in phi:
            if i == j:
                continue
            for l in range(k):
                for h in range(k):
                    if l == h:
                        continue
                    y[(i, j, l, h)] = pp.LpVariable(f"y_{i}_{j}_{l}_{h}", cat="Binary")
                    prob += y[(i, j, l, h)] <= partition_to_axis[(i, l)]
                    prob += y[(i, j, l, h)] <= partition_to_axis[(j, h)]
                    prob += y[(i, j, l, h)] >= partition_to_axis[(i, l)] + partition_to_axis[(j, h)] - 1
    # zielfunktion initialisieren
    prob += ilp_objective_function(partition_to_axis, y, axes_weights, phi, k)
    # nebenbedingungen initialisieren
    for i in phi:
        prob += pp.lpSum(partition_to_axis[(i, j)] for j in range(k)) == 1
    for j in range(k):
        prob += pp.lpSum(partition_to_axis[(i, j)] for i in phi) == 1
    # ILP lösen
    prob.solve(pp.PULP_CBC_CMD(msg=False))
    assignment = {}
    for i in phi:
        for j in range(k):
            if round(pp.value(partition_to_axis[(i, j)])) == 1:
                assignment[j] = i
    new_axis_order = []
    for j in range(k):
        new_axis_order.append(assignment[j])
    return new_axis_order
if __name__ == "__main__":
    # Aufbau der Testdaten
    from graphs import sample_graph_multipartite, sample_graph_caveman, sample_graph_selfconstructed
    from partitioning import clauset_newman_moore_communities, louvain_community_detection
    G = sample_graph_multipartite()
    CG = sample_graph_caveman(4, 10)
    SC = sample_graph_selfconstructed()
    pipeline_test = 1
    if pipeline_test == 1:
        edges = list(SC.edges())
        nodes = list(SC.nodes(data="subset"))
        axes = native_order(nodes)
        grps = node_groups(nodes)
        phi = brute_force_ordering(axes, grps, edges)
        node_grps = reordered_node_groups(grps, phi)
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
        phi = native_order(nodes)
        node_grps = node_groups(nodes)
        print("##########################################")
        print("nodes:", nodes)
        print("phi:", phi)
        print("node_grps:", node_grps)
        print("##########################################")
from graphs import sample_graph

def node_or_axes_span(n1, n2, k): #Span von Knoten u,v oder Achsen a_i,a_j
    """Berechnet den Spann zweier Knoten oder Achsen

    Args:
        n1 (int): Achse/Knoten 1
        n2 (int): Achse/Knoten 2
        k (int): Gesamtzahl der Achsen

    Returns:
        int: errechneter Spann
    """
    span = np.minimum(np.mod(n1 - n2, k), np.mod(n2 - n1, k))
    return span

def edges_between_axes(node_grps, edges, a1, a2): #w_i,j !Kommentar: wenn edgelist immer geordnet else korrekt, falls nicht else entfernen PRÜF
    """Ermittelt wieviele Kanten zwischen den gegebenen Achsen bestehen.

    Args:
        node_grps (dict): key: subset, value: list
        edges (list): Kantenliste aus Tupeln
        a1 (int): Achse 1
        a2 (int): Achse 2

    Returns:
        int: Anzahl der Kanten
    """
    edgecount = 0
    for edge in edges:
        start = 0
        end = 1
        if node_to_axis(edge[start], node_grps) == a1 and node_to_axis(edge[end], node_grps) == a2:
            edgecount += 1
        # else:
        #     if node_to_axis(edge[start], node_grps) != a1:
        #         break
    return edgecount

def cost_function_whole(ordering): #cost(phi) etc.
    cost = 0
    # for elem in range(len(ordering)-1):
    for ax in ordering:
        for axis in ordering:
            if ax < axis:
                cost += (edges_between_axes(node_grps, edges, ordering[ax], ordering[axis]) * node_or_axes_span(ordering[ax], ordering[axis], len(ordering)))
    return cost

if __name__ == "__main__":
    # Aufbau der Testdaten
    G = sample_graph()
    nodes = list(G.nodes(data="subset"))
    edges = list(G.edges())
    phi = cyclic_ordering(nodes)
    node_grps = node_groups(nodes)
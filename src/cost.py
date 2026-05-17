from src.ordering import node_to_axis

def node_or_axes_span(n1, n2, k): #Span von Knoten u,v oder Achsen a_i,a_j
    """Berechnet den Spann zweier Knoten oder Achsen

    Args:
        n1 (int): Achse/Knoten 1
        n2 (int): Achse/Knoten 2
        k (int): Gesamtzahl der Achsen

    Returns:
        int: errechneter Spann
    """
    span = min((n1 - n2) % k, (n2 - n1) % k)
    return span

def edges_between_axes(node_grps, edges, a1, a2):
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
        start = node_to_axis(edge[0], node_grps)
        end = node_to_axis(edge[1], node_grps)
        if (start == a1 and end == a2) or (start == a2 and end == a1): # or gewährleistet symmetrie
            edgecount += 1
    return edgecount

def cost_function_whole(ordering: list[int], node_grps: dict, edges: list) -> int:
    """Die Kostenfunktion wird in Schritt zwei der Pipeline (Sec. 3.2) verwendet, um die kostengünstigste Achsenordnung zu ermitteln. 
    Kostengünstig bedeutet hier, dass möglichst viele Achsenpaare mit möglichst geringem Span einfließen sollen. 

    Args:
        ordering (list[int]): Ordnung der Achsen (phi)
        node_grps (dict): key: Achse, value: Knoten auf der Achse
        edges (list): Kantenliste des Graphen

    Returns:
        int: Gesamtkosten der Achsenordnung
    """
    k = len(ordering) # anzahl der achsen
    cost = 0
    for i in range(k):
        for j in range(i + 1, k):
            # print(f"{ordering[i]} -> {ordering[j]}") # debugging
            # print(f"{edges_between_axes(node_grps, edges, ordering[i], ordering[j])* node_or_axes_span(i, j, k)}") # debugging
            cost += (edges_between_axes(node_grps, edges, ordering[i], ordering[j]) * node_or_axes_span(i, j, k))
    return cost

if __name__ == "__main__":
    # Aufbau der Testdaten
    from graphs import sample_graph_multipartite
    from src.ordering import native_order, node_groups
    G = sample_graph_multipartite()
    nodes = list(G.nodes(data="subset"))
    edges = list(G.edges())
    phi_default = native_order(nodes)
    phi_reordered = [2, 0, 1, 4]
    node_grps = node_groups(nodes)
    print("##########################################")
    print("node_grps:", node_grps)
    print("##########################################")
    print("phi generisch:", phi_default)
    print("Cost (default):", cost_function_whole(phi_default, node_grps, edges))
    print("##########################################")
    print("phi umsortiert:", phi_reordered)
    print("Cost (reordered):", cost_function_whole(phi_reordered, node_grps, edges))
    print("##########################################")
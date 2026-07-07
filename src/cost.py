def node_or_axes_span(n1: int, n2: int, k: int) -> int:
    """Berechnet den Span zweier Knoten oder Achsen.

    Args:
        n1 (int): Achse/Knoten 1
        n2 (int): Achse/Knoten 2
        k (int): Gesamtzahl der Achsen

    Returns:
        int: errechneter Spann
    """
    span = min((n1 - n2) % k, (n2 - n1) % k)
    return span

def edges_between_axes(node_grps: dict[int, list[int, str]], edges: list[tuple[int | str, int | str]], a1: int, a2: int) -> int:
    """Ermittelt wieviele Kanten zwischen den gegebenen Achsen bestehen.

    Args:
        node_grps (dict): key: subset, value: list
        edges (list): Kantenliste aus Tupeln
        a1 (int): Achse 1
        a2 (int): Achse 2

    Returns:
        int: Anzahl der Kanten
    """
    from ordering import node_to_axis_maps, node_to_axis
    edgecount = 0
    for edge in edges:
        start = node_to_axis(edge[0], node_grps)
        end = node_to_axis(edge[1], node_grps)
        if (start == a1 and end == a2) or (start == a2 and end == a1):
            edgecount += 1
    return edgecount

def cost_function_whole(ordering: list[int], node_grps: dict[int, list[int, str]], edges: list[tuple[int | str, int | str]]) -> int:
    """Die Kostenfunktion wird in Schritt zwei der Pipeline (Sec. 3.2) verwendet, um die kostengünstigste Achsenordnung zu ermitteln. 
    Kostengünstig bedeutet hier, dass möglichst viele Achsenpaare mit möglichst geringem Span einfließen sollen. 
    ### LEGACY - nur für Brute Force relevant ###
    Args:
        ordering (list[int]): Ordnung der Achsen (phi)
        node_grps (dict): key: Achse, value: Knoten auf der Achse
        edges (list): Kantenliste des Graphen

    Returns:
        int: Gesamtkosten der Achsenordnung
    """
    k = len(ordering)
    cost = 0
    for i in range(k):
        for j in range(i + 1, k):
            cost += (edges_between_axes(node_grps, edges, ordering[i], ordering[j]) * node_or_axes_span(i, j, k))
    return cost

if __name__ == "__main__":
 pass
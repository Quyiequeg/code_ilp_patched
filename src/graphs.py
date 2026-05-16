import networkx as nx

def sample_graph_multipartite(sizes=(10, 10, 10)):
    """Erzeugt einen vollständigen multipartiten Testgraphen. Diese Funktion dient dem Testen und Debugging.
    
    Args:
        sizes: Tuple mit Knotenanzahl pro Partition
    Returns:
        nx.Graph: multipartiter Graph mit subset-Attribut
    """
    return nx.complete_multipartite_graph(*sizes)

def sample_graph_caveman(num_cliques, clique_size):
    """Erzeugt einen Caveman-Graphen. Diese Funktion dient dem Testen und Debugging.

    Args:
        num_cliques: Anzahl der Cliquen
        clique_size: Knotenanzahl jeder Clique

    Returns:
        nx.Graph: Caveman-Graph
    """
    return nx.caveman_graph(num_cliques, clique_size)

def sample_graph_selfconstructed():
    """Erzeugt einen sehr kleinen, selbst konstruierten Graphen. Dient dem Testen und Debugging. Er weist folgende Kennzahlen auf:
    - 8 Knoten
    - 5 Kanten
    - 4 Achsen mit jeweils 2 Knoten -> Phi = (0, 1, 2, 3)  
    - das optimale Gewicht ist 7, bei der Achsenanordnung (0, 1, 3, 2)

    Returns:
        nx.Graph: selbst konstruierter Graph
    """
    G = nx.Graph()
    G.add_nodes_from([0, 1], subset=0)
    G.add_nodes_from([2, 3], subset=1)
    G.add_nodes_from([4, 5], subset=2)
    G.add_nodes_from([6, 7], subset=3)
    G.add_edges_from([(0, 2), (0,5), (1, 3), (2, 4), (2, 7)])
    return G

if __name__ == "__main__":
    G = sample_graph_multipartite()
    C = sample_graph_caveman(4, 10)
    print("##########################################")
    print(f"Multi: Knoten: {G.number_of_nodes()}, Kanten: {G.number_of_edges()}")
    print("##########################################")
    print(f"Caveman: Knoten: {C.number_of_nodes()}, Kanten: {C.number_of_edges()}")
    print("##########################################")
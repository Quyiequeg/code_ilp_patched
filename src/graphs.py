import networkx as nx
import src.hiveplot as hpl

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
    G.add_nodes_from([6, 7,], subset=3)
    G.add_edges_from([(0, 2), (0,5), (1, 3), (2, 4), (2, 7)])
    return G

def sample_graph_selfconstructed_extended(mode: int = 0):
    """Verschiedene Testgraphen für Pipelinetests (Barycenter/ILP). Dient größtenteils für Proof of Concept bei Nichenfällen, deshalb während des Debuggens ständig verändert und erweitert.

    Returns:
        nx.Graph: selbst konstruierter Graph
    """
    G = nx.Graph()
    if mode == 0: # standard
        G.add_nodes_from([0, 1, 2], subset=0)
        G.add_nodes_from([3, 4, 5], subset=1)
        G.add_nodes_from([6, 7, 8], subset=2)

        G.add_edges_from([(0, 5), (1, 3), (2, 4)])
        G.add_edges_from([(3, 6), (1, 7)])
    elif mode == 1: # intra-axis tests
        G.add_nodes_from([0, 1, 2], subset=0)
        G.add_nodes_from([3, 4, 5], subset=1)
        G.add_nodes_from([6, 7, 8], subset=2)
        G.add_nodes_from([9, 10, 11, 12], subset=3) # + isolierter Knoten
        # G.add_nodes_from([13, 14, 15, 16, 17, 18], subset=4) # + isolierte Knoten + intra-axis

        G.add_edges_from([(0, 5), (1, 3), (2, 4)])
        G.add_edges_from([(6, 11), (7, 9), (8, 10)])
        G.add_edges_from([(0, 10), (2, 9)])
        G.add_edges_from([(1, 7), (2, 8), (5, 11), (2, 11), (4, 11)]) # lange kanten
    elif mode == 2: # intra axis tests
        G.add_nodes_from([0, 1, 2], subset=0)
        G.add_nodes_from([3, 4, 5], subset=1)
        G.add_nodes_from([6, 7, 8], subset=2)
        G.add_nodes_from([9, 10, 11, 12], subset=3) # + isolierter Knoten
        G.add_nodes_from([13, 14, 15, 16, 17, 18], subset=4) # + isolierte Knoten + intra-axis

        G.add_edges_from([(0, 5), (1, 3), (2, 4)])
        G.add_edges_from([(6, 11), (7, 9), (8, 10)])
        G.add_edges_from([(0, 10), (2, 9)])
        G.add_edges_from([(1, 7), (2, 8), (5, 11), (2, 11), (4, 11)]) # lange kanten
        G.add_edges_from([(13, 14), (15, 16), (17, 18), (14,15)]) # intra-axis kanten, OSZILLATION BEI (17, 18) -> MÖGLICHER FIX: states hashen
        G.add_edges_from([(9, 16)]) # 13 ist jetzt inter und intra 

        G.add_edges_from([(14, 16)]) # verzweigung der intra axis komponente knoten 14-15-16 bilden jetzt einen kreis
        G.add_nodes_from([19, 20, 21, 22, 23, 24, 25, 26, 27, 28], subset=5) # testfall: langer intra axis pfad
        # G.add_edges_from([(19, 20), (20, 21),  (22, 23)]) # testfall: langer intra axis pfad
        G.add_edges_from([(19, 20), (20, 21), (21, 22), (21, 22), (23, 24)]) # testfall: nur intra lang + kurz
        G.add_edges_from([(19, 21), (24, 25), (5, 18)]) # testfälle: kreis+solo auf einer kante
        G.add_edges_from([(0, 24)]) # testfälle: erweitert vorherigen fall um mixed
        G.add_edges_from([(27, 28)])

    return G

if __name__ == "__main__":
    # G = sample_graph_multipartite()
    # C = sample_graph_caveman(4, 10)
    D = sample_graph_selfconstructed_extended(1)
    print("##########################################")
    # print(f"Multi: Knoten: {G.number_of_nodes()}, Kanten: {G.number_of_edges()}")
    # print(f"Caveman: Knoten: {C.number_of_nodes()}, Kanten: {C.number_of_edges()}")
    print(f"Self-constructed: Knoten: {D.number_of_nodes()}, Kanten: {D.number_of_edges()}")
    print("##########################################")
    print(nx.single_source_shortest_path_length(D, 16))
    print(nx.shortest_path(D, 16))
    print(nx.shortest_path(D, 16).values())
    node_list = list(nx.shortest_path(D, 16).values())
    print(node_list)
    singleton_list = set()
    for elem in node_list:
        for single in elem:
            singleton_list.add(single)
    print(singleton_list)
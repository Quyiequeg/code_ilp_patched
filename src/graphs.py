# src/graphs.py
import networkx as nx

def sample_graph(sizes=(10, 10, 10)):
    """Erzeugt einen vollständigen multipartiten Testgraphen.
    
    Args:
        sizes: Tuple mit Knotenanzahl pro Partition
    Returns:
        nx.Graph: multipartiter Graph mit subset-Attribut
    """
    return nx.complete_multipartite_graph(*sizes)

if __name__ == "__main__":
    G = sample_graph()
    print(f"Knoten: {G.number_of_nodes()}, Kanten: {G.number_of_edges()}")
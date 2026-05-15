import networkx as nx

def clauset_newman_moore_communities(graph):
    """Berechnet die Communities eines Graphen per Clauset-Newman-Moore Algorithmus und wandelt die frozenset Liste in ein dict um.

    Args:
        graph (nx.Graph): Der Eingabegraph für den die Communities berechnet werden sollen.

    Returns:
        dict[int, list[int]]: Ein Dictionary mit den Communities als Werte und ihren IDs als Schlüssel.
    """
    communities = nx.algorithms.community.greedy_modularity_communities(graph) # !prüfen: frozenset -> communities später nicht veränderbar, relevant?
    node_grps = {i: list(community) for i, community in enumerate(communities)}
    return node_grps

def louvain_community_detection(graph):
    """Berechnet die Communities eines Graphen per Louvain Community Detection und wandelt die frozenset Liste in ein dict um.

    Args:
        graph (nx.Graph): Der Eingabegraph, für den die Communities berechnet werden sollen.

    Returns:
        dict[int, list[int]]: Ein Dictionary mit den Communities als Werte und ihren IDs als Schlüssel.
    """
    communities = nx.algorithms.community.louvain_communities(graph) # !prüfen: frozenset -> communities später nicht veränderbar, relevant?
    node_grps = {i: list(community) for i, community in enumerate(communities)}
    return node_grps

if __name__ == "__main__":
    # Aufbau der Testdaten
    from graphs import sample_graph_caveman
    CG = sample_graph_caveman(4, 10)
    c = clauset_newman_moore_communities(CG)
    l = louvain_community_detection(CG)
    print("##########################################")
    for i, comm in enumerate(c):
        print(f"Community {i + 1}: {comm}")
    print("##########################################")
    for i, comm in enumerate(l):
        print(f"Community {i + 1}: {comm}")
    print("##########################################")
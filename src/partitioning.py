import networkx as nx

def clauset_newman_moore_communities(graph, threshold: int = 0) -> dict[int, list[int]]:
    """Berechnet die Communities eines Graphen per Clauset-Newman-Moore Algorithmus und wandelt die frozenset Liste in ein dict um.
    Falls ein Threshold übergeben wird, so wird die Anzahl der Communities auf den Threshold gestaucht. So wird sichergestellt, dass man
    eine Anzahl Communities (Achsen) erhält, die noch einen übersichtlichen Hiveplot erzeugen lassen.

    Args:
        graph (nx.Graph): Der Eingabegraph für den die Communities berechnet werden sollen.
        threshold(int): maximale Anzahl Communities, bei Default (=0) wird die natürliche Anzahl von Communities ermittelt und zurückgegeben
    Returns:
        dict[int, list[int]]: Ein Dictionary mit den Communities als Werte und ihren IDs als Schlüssel.
    """
    communities = nx.algorithms.community.greedy_modularity_communities(graph)
    node_grps = {i: list(community) for i, community in enumerate(communities, start=1)}
    if threshold > 0:
        while  len(node_grps) > threshold:
            node_group_size = {i: len(node_grps[i]) for i in node_grps} # communityid: größe
            node_group_size = dict(sorted(node_group_size.items(), key=lambda x: x[1])) # aufsteigend sortiert
            keys = list(node_group_size)
            node_grps[keys[1]].extend(node_grps[keys[0]]) # zwei kleinsten communities fusionieren
            del node_grps[keys[0]] # kleinste löschen
        node_grps = {i: v for i, v in enumerate(node_grps.values(), start=1)} # achsenids wieder aufsteigend benennen bei 1
    return node_grps

def louvain_community_detection(graph):
    """Berechnet die Communities eines Graphen per Louvain Community Detection und wandelt die frozenset Liste in ein dict um.
    Diese Funktion wird für Vergleichs- und Testzwecke weiterhin bereitgestellt.
    Args:
        graph (nx.Graph): Der Eingabegraph, für den die Communities berechnet werden sollen.

    Returns:
        dict[int, list[int]]: Ein Dictionary mit den Communities als Werte und ihren IDs als Schlüssel.
    """
    communities = nx.algorithms.community.louvain_communities(graph)
    node_grps = {i: list(community) for i, community in enumerate(communities)}
    return node_grps

if __name__ == "__main__":
    pass
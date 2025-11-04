import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from flexitext import flexitext
from hiveplotlib import HivePlot
from hiveplotlib.converters import networkx_to_nodes_edges

def sample_graph():
    """Erstellt einen einfachen Testgraphen mit 30 Knoten, die jeweils schon 3 Subsets zugeordnet sind.

    Returns:
        NetworkX Graph: Multipartiter Graph
    """
    G = nx.complete_multipartite_graph(10, 10, 10)
    return G

def cyclic_ordering(nodes): # phi
    """Bekommt einen NodeView übergeben und wandelt diese über ein Set in eine Liste um, die alle Subsetnumnern enthält. Diese Subsets spiegeln die Achsen wieder. Die Liste spiegelt also die zyklische Achsenanordnung wieder.

    Args:
        nodes (NodeDataView): siehe networkx.graph.nodes 

    Returns:
        list: zyklische Achsenanordnung mit Achsennummern
    """
    ordered_set = set(t[1] for t in nodes) # zweites Tupel-Element ist Subset
    ordered_list = list(ordered_set)
    return ordered_list

def node_span(): #span(a_i, a_j) function
    pass

G = sample_graph()
# nodes = list(G.nodes(data="subset")) # V1 Ausgabe der Knoten mit Attribut "subset"
edges = list(G.edges())
# phi = cyclic_ordering(nodes)

# nodes = list(G.nodes) # V2 nur Knoten aus G
# nodes = list(G.nodes.data()) # V3 Knoten mit allen Attributen
print("edges: ")
print(edges)

# print(phi)
# print(type(phi))
# print(phi[1])
# print(type(phi[1]))

# print("nodes: ")
# print(nodes)
# print(type(nodes))
# print(nodes[1][1]) # Ausgabe des Subset-Werts des Knotens mit ID 1
# print(type(nodes[1][1])) #V1: int, V2: Fehler (nur Knoten), V3: dict {'subset': 0}
# print(Gnodes)
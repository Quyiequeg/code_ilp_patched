import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
# import pandas as pd
# from flexitext import flexitext
# from hiveplotlib import HivePlot
# from hiveplotlib.converters import networkx_to_nodes_edges

def sample_graph():
    """Erstellt einen einfachen Testgraphen mit vordefinierten Subsets und Knotenenzahl.

    Returns:
        NetworkX Graph: Multipartiter Graph
    """
    G = nx.complete_multipartite_graph(5, 10, 5, 8)
    return G





def span_classification():
    pass

def axis_nodelist():
    pass

# generiere testgraph
G = sample_graph()

# extrahiere Knoten, Kanten und wichtige Informationen
nodes = list(G.nodes(data="subset")) # V1 Ausgabe der Knoten mit Attribut "subset"
edges = list(G.edges())
phi = cyclic_ordering(nodes)
node_grps = node_groups(nodes)



################# Ausgaben für Tests #################
# Ausgabe-Steuerung
hg = 1 # HivePlot H(G)
n = 1 # Knoten
e = 1 # Kanten
o = 1 # ordering (phi)
s = 1 # span
c = 1 # cost function
print("--------------------------------------------------------------------------")
if hg != 0:
    print("HivePlot H(G) = (A, alpha, phi, Pi)")
    print("---------------------")
    print("A/Achsen: " +  "{" + str(phi) + "}" + "(|A| = " + str(len(phi)) + ")")
    print("alpha: " + str(node_grps))
    print("phi: " + str(phi))
    print("Pi: ")
    for gruppe, knoten_liste in node_grps.items():
        print(f"pi_{gruppe}: {knoten_liste}")
    print("---------------------")
if n != 0:
    # node ausgaben
    print("->nodes: ")
    print(nodes)
    print(type(nodes))
    # print(nodes[1][1]) # Ausgabe des Subset-Werts des Knotens mit ID 1
    # print(type(nodes[1][1])) #V1: int, V2: Fehler (nur Knoten), V3: dict {'subset': 0}
    print("---------------------")
if e != 0:
    # edge ausgaben
    print("->edges:")
    print(edges)
    print(type(edges))
    # print(edges[1])
    # print(type(edges[1]))
    # print(edges[1][0])
    # print(type(edges[1][0]))
    for ax in phi:
        for axis in phi:
            if ax < axis:
                print(f"Kanten zwischen Achse {ax} und {axis}: {edges_between_axes(node_grps, edges, ax, axis)}")
    print("---------------------")
if o != 0:
# ordering ausgaben
    print("->ordering (phi): ")
    print(phi)
    print(type(phi))
    # print(phi[1])
    print(type(phi[1]))
    print("---------------------")
if s != 0:
    # test hilfsfunktionen
    print("->test hilfsfunktionen:")
    for ax in phi:
        for axis in phi:
            if ax < axis:
                print(f"Span zwischen Achsen {ax} und {axis}: {node_or_axes_span(ax, axis, len(phi))}")

    print("---------------------")
if c != 0:
    # test cost function
    print("->test cost function:")
    cost = cost_function_whole(phi)
    print(f"Gesamtkosten für das Ordering {phi}: {cost}.")
    print("---------------------")
print("--------------------------------------------------------------------------")
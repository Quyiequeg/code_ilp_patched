import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from flexitext import flexitext
from hiveplotlib import HivePlot
from hiveplotlib.converters import networkx_to_nodes_edges

def sample_graph():
    """Erstellt einen einfachen Testgraphen mit vordefinierten Subsets und Knotenenzahl.

    Returns:
        NetworkX Graph: Multipartiter Graph
    """
    G = nx.complete_multipartite_graph(5, 5, 5, 5)
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

def node_groups(nodes): # alpha, Mapping von Knoten zu Achsengruppen
    """Erzeugt ein Dict wobei jeder Key ein Subset ist dem eine Liste aus zughörigen Knoten zugeordnet wird.


    Args:
        nodes (NodeView): Liste aus Tupeln (KnotenID, Subset)

    Returns:
        dict: key: int, value: list
        {0: [0, 1, 2, 3...], ...} 
    """
    node_groups = {}
    for node, subset in nodes:
        if subset not in node_groups:
            node_groups[subset] = []
        node_groups[subset].append(node)
    return node_groups

def node_to_axis(node, node_grps): # alpha(u)
    """Gibt an auf welcher Achse sich ein Knoten befindet.

    Args:
        node (int): Knoten ID
        node_grps (dict): key: subset, value: list

    Raises:
        ValueError: Der Knoten kann keiner Achse zugeordnet werden.

    Returns:
        int: Achsen ID
    """
    axis = None
    for subset, nds in node_grps.items():
        if node in nds:
            axis = subset
            break
    if axis is None:
        raise ValueError(f"Knoten {node} keiner Achse zugeordnet.")
    else:
        return axis

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
hg = 0 # HivePlot H(G)
n = 0 # Knoten
e = 0 # Kanten
o = 0 # ordering (phi)
s = 0 # span
c = 0 # cost function
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
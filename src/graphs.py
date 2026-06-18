import networkx as nx
import hiveplot as hpl
import crossing_minimization as cm
import renderer as rr
import matplotlib.pyplot as plt
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

        G.add_edges_from([(0, 5), (0, 3), (1, 4), (2, 6), (7, 0), (8, 2), (8, 5), (6, 3), (7, 4)])
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
        G.add_nodes_from([1, 2, 3], subset=1)
        G.add_nodes_from([4, 5, 6], subset=2)
        G.add_nodes_from([7, 8, 9], subset=3)
        G.add_nodes_from([10, 11, 12, 13], subset=4)
        G.add_nodes_from([14, 15, 16], subset=5) 

        G.add_edges_from([(1, 6), (2, 4), (3, 5)]) # 1 -> 2
        G.add_edges_from([(5, 8)]) # 2 -> 3
        G.add_edges_from([(7, 11), (7, 10)]) # 3 -> 4
        G.add_edges_from([(10, 14)]) # 4 -> 5
        G.add_edges_from([(2, 8), (6, 13), (3, 12), (1, 13), (4, 14)]) # lange kanten
        # G.add_edges_from([(14, 15), (15, 16)]) # intra
        # G.add_edges_from([(7, 9), (8, 9)]) # intra

    elif mode == 3: # post processing test graph
        G.add_nodes_from([0, 1, 2, 'd_4_11_1', 'd_5_11_1'], subset=0)
        G.add_nodes_from([3, 4, 5, 'd_0_24_1'], subset=1)
        G.add_nodes_from([6, 7, 8, 'd_9_16_1'], subset=2)
        G.add_nodes_from([9, 10, 11, 12, 'd_1_7_1', 'd_2_8_1'], subset=3) # + isolierter Knoten
        G.add_nodes_from([13, 14, 15, 16, 17, 18], subset=4) # + isolierte Knoten + intra-axis
        G.add_nodes_from([19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 'd_5_18_1'], subset=5) # testfall: langer intra axis pfad
        G.add_edges_from([(19, 20), (19, 21), (20, 21), (21, 22), (0, 5), (0, 10), (1, 3), (2, 4), (2, 9), (2, 11), (6, 11), (7, 9), (7, 16), (8, 10), (13, 14), (14, 15), (14, 16), (15, 16), (17, 18), (18, 28), (23, 24), (24, 25), (27, 28), (0, 'd_0_24_1'), ('d_0_24_1', 24), (1, 'd_1_7_1'), ('d_1_7_1', 7), (2, 'd_2_8_1'), ('d_2_8_1', 8), (4, 'd_4_11_1'), ('d_4_11_1', 11), (5, 'd_5_11_1'), ('d_5_11_1', 11), (5, 'd_5_18_1'), ('d_5_18_1', 18), (9, 'd_9_16_1'), ('d_9_16_1', 16)])
    # elif mode == 4: # post processing test graph
        
    #     pass
    return G

if __name__ == "__main__":
        G = nx.Graph()
        edges = [
            (5, 7), (4, 9), (5,10),   # proper
            (1, 6),                    # long edge, Span 2
            (10, 12),                  # mixed, Achse 1
            (11, 13), (13, 15),           # strict-intra lang
            (16, 17), (2, 3)                  # strict-intra kurz
        ]
        for i in range(17):
            G.add_node(i+1)
        G.add_edges_from(edges)

        node_groups = {
            1: [3, 2, 1],
            3: [7, 9], #8
            2: [4, 5, 6],
            4: [12, 11, 10, 13, 15, 17, 16, "d_1_6_1"], #14
        }

        axis_order = [1, 3, 2, 4]
        hply = hpl.HivePlotLayout(
        graph=G,
        num_axes=4,
        axis_order=axis_order,
        node_groups=node_groups,
        node_groups_dummies = {
            1: [],
            3: [],
            2: [],
            4: ["d_1_6_1"],
        },
        dummy_edge_segments = [
            (1, "d_1_6_1"),
            ("d_1_6_1", 6),
        ],
        long_edges = {(1, 6)},
        intra_axis_nodes = {
            1: [2, 3],
            3: [],
            2: [],
            4: [12, 13, 15, 16, 17],
        },
        intra_axis_edges = [
            (2, 3),
            (11, 13),
            (10, 12),
            (13, 15),
            (16, 17),
        ]
        )
        color_map = {
            5:  "#e15759",  # proper
            7:  "#e15759",  # proper
            4:  "#e15759",  # proper
            9:  "#e15759",  # proper
            1:  "#e15759",  # long edge
            6:  "#e15759",  # long edge
            10: "#e15759",  # mixed
            11: "#e15759",  # mixed
            12: "#e15759",  # strict-intra lang
            13: "#e15759",  # strict-intra lang
            15: "#e15759",  # strict-intra lang
            16: "#e15759",  # strict-intra kurz
            17: "#e15759",  # strict-intra kurz
            2:  "#e15759",  # strict-intra kurz
            3:  "#e15759",  # strict-intra kurz
            8:  "#e15759",  # isoliert
            14: "#e15759",  # isoliert
        }
        # G.remove_nodes_from([8, 14])
        # G.add_edges_from([(1, "d_1_6_1"), ("d_1_6_1", 6)])
        # G.remove_edge(1,6)
        # hply.prepare_for_rendering()
        # print(G.edges())
        # colors = [color_map[n] for n in G.nodes()]
        # pos = nx.spring_layout(G, seed=42, k=3.0)  # k erhöhen = mehr Abstand

        # fig, ax = plt.subplots(figsize=(8, 6))

        # nx.draw_networkx_nodes(G, pos, ax=ax,
        #     node_color=colors, node_size=600)

        # nx.draw_networkx_labels(G, pos, ax=ax,
        #     font_color='white', font_weight='bold')

        # nx.draw_networkx_edges(G, pos, ax=ax,
        #     edge_color='gray', width=1.5)

        # ax.axis('off')
        # plt.savefig("kapitel4_beispielgraph_schlicht.pdf", bbox_inches='tight')
        # isolated_nodes = cm.remove_isolated_nodes(hpl.graph, hpl.node_groups)
        # node_position_map, node_axis_map = cm.node_to_axis_maps(hpl, hpl.node_groups)
        # neighborhood_map = hpl.get_proper_neighborhood_map(hpl.edges())
        # cm.subdivide_long_edges(hpl, node_position_map, node_axis_map, neighborhood_map)
        print(hply)
        # rr.hiveplot_renderer("beispiel_vor_3a", hply, mode = "ba", intra=True)
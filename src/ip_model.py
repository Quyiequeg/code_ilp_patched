import src.crossing_minimization as cm
from src import graphs
from src.cost import node_or_axes_span
from src.ordering import brute_force_ordering, native_order, node_groups, node_to_axis_maps, reordered_node_groups
import networkx as nx
import pulp as pp

def onelayer_twosided_optimization(layout: HivePlotLayout, threshold: float = float(10)) -> pp.LpProblem:
    # ähnlich barycenter sweep: cw + ccw = 1 sweep. berechnung von: achsenordnung pi_i variabel, pi^+/pi^- fixiert
    # hiveplot attribute
    node_groups = layout.node_groups
    delta = delta_mapping(node_groups)
    # probleminstanz
    prob = pp.LpProblem("one_layer_two_sided_crossing_minimization_ilp", pp.LpMinimize)
    # variablen
    for key in delta:
        pp.LpVariable(f"{key[0]}_{key[1]}_{key[2]}", cat="Binary")
    # zielfunktion
    prob += (induced_crossings() + induced_crossings()), "1L2S-Kreuzungsminimierung"
    # nebenbedingungen

    # lösen
    prob.solve(pp.PULP_CBC_CMD(msg=True))

    pass
    return prob

def delta_mapping(node_groups: dict[int, list[int]]) -> dict[tuple[int, int, int], None]:
    # tuple(node1, node2, axis) = lpvar
    delta = {}
    for axis, nodes in node_groups.items():
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                delta[(nodes[i], nodes[j], axis)] = None
                delta[(nodes[j], nodes[i], axis)] = None
    return delta

def induced_crossings(pi_i, pi_fix): # C(pi, pi^+/-)
    pass

def ip_model_pipeline(layout: HivePlotLayout, threshold: float = float("inf")) -> None:
    # pipeline 3a <<<<<<<<<<<<
    # 1.
    isolated_nodes = cm.remove_isolated_nodes(layout.graph, layout.node_groups)
    # 2.
    node_position_map, node_axis_map = node_to_axis_maps(layout, layout.node_groups)
    neighborhood_map = layout.get_proper_neighborhood_map(layout.edges()) # initialisieren aus layout.graph
    cm.subdivide_long_edges(layout, node_position_map, node_axis_map, neighborhood_map)
    # 3.
    # fused_edge_list = layout.fuse_edges_with_edge_dummies() # dummykanten einbeziehen
    # fused_node_list = layout.fuse_node_groups_with_dummies() # UPDATE !!!
    # node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list) # UPDATE !!!
    # neighborhood_map = layout.get_proper_neighborhood_map(fused_edge_list)
    # layout.dummy_edge_segments = layout.fuse_edges_with_edge_dummies()
    # 4.
    # _sweep(layout, neighborhood_map, node_axis_map, threshold=threshold, real=True) # nur real
    # _sweep(layout, neighborhood_map, node_axis_map, threshold=threshold, real=False) # nur virtuell (dummies)
    #pipeline 3b <<<<<<<<<<<<
    # 5.
    # intra_axis_handler(layout)
    # 6.
    cm.finish_structured_axis_orders(layout, isolated_nodes)

if __name__ == "__main__":
    print("##########################################")
    printer = 0 # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< PRINTER
    # graph_mode = 0
    # graph_mode = 1
    graph_mode = 2
    from src.graphs import sample_graph_selfconstructed, sample_graph_multipartite, sample_graph_caveman
    from src.hiveplot import HivePlotLayout
    # # from src.partitioning import louvain_community_detection
    from src.debug_renderer import render_debug
    # # logging.basicConfig(level=logging.DEBUG)
    G = graphs.sample_graph_selfconstructed_extended(graph_mode)
    nodes = list(G.nodes(data="subset"))
    axes = native_order(nodes)
    ng = node_groups(nodes)
    delta = delta_mapping(ng)
    print(delta)
    print("Layout ORIGINAL")
    hpl = HivePlotLayout(
        graph=G,
        num_axes=len(axes),
        axis_order=axes,
        node_groups=ng
    )
    print(hpl)
    if printer == 1:
        render_debug(hpl, title="ORIGINAL") 
    hpl.axis_order = brute_force_ordering(axes, ng, list(G.edges()))
    hpl.node_groups = reordered_node_groups(ng, hpl.axis_order)
    if printer == 1:
        render_debug(hpl, title="OHNE PIPELINE - OPTIMIZED")
    print("Pipeline -> Start")
    # barycenter_crossmin_pipeline(hpl, threshold=5)
    ip_model_pipeline(hpl)
    print("Pipeline -> Ende")
    # hpl.node_groups = hpl.fuse_node_groups_with_dummies() # ACHTUNG: FÜR RENDERING NÖTIG, LETZTE AKTUALISIERUNG VOR DER VISUALISIERUNG (Erweiterung der Achs)
    if printer == 1:
        render_debug(hpl, title="PIPELINE ABGESCHLOSSEN")
    print("Layout NACH OPTIMIERUNG")
    print(hpl)
    print(hpl.edges())
    print("##########################################")
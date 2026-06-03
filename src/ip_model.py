import src.crossing_minimization as cm
from src import graphs
from src.cost import node_or_axes_span
from src.ordering import brute_force_ordering, native_order, node_groups, node_to_axis_maps, reordered_node_groups
import networkx as nx
import pulp as pp

def onelayer_twosided_optimization(layout: HivePlotLayout, neighborhood_map, node_axis_map, threshold: int = int(10)) -> None:
    # ähnlich barycenter sweep: cw + ccw = 1 sweep. berechnung von: achsenordnung pi_i variabel, pi^+/pi^- fixiert
    # hiveplot attribute
    def sorted_neighbor_map(neighborhood_map, node_axis_map, pi_var, pi_plus_axis, pi_minus_axis):
        sorted_neighbors = {}
        for node in pi_var:
            plus_list = []
            minus_list = []
            neighbors = neighborhood_map[node]
            for neighbor in neighbors:
                if node_axis_map[neighbor] == pi_minus_axis:
                    minus_list.append(neighbor)
                elif node_axis_map[neighbor] == pi_plus_axis:
                    plus_list.append(neighbor)
            sorted_neighbors[(pi_minus_axis, node)] = minus_list
            sorted_neighbors[(pi_plus_axis, node)] = plus_list
        return sorted_neighbors
    
    node_groups = layout.node_groups
    fused_groups =  layout.fuse_node_groups_with_dummies()
    phi = layout.axis_order
    reversed_phi = list(reversed(phi))
    phi_index_map = {}
    for index, axis in enumerate(phi):
        phi_index_map[axis] = index
    delta = delta_mapping(fused_groups)
    threshold_break = 0
    while threshold_break < threshold:
        threshold_break += 1
        for axis in phi:
            # probleminstanz
            prob = pp.LpProblem(f"1S2L_ILP_clockwise_run_{threshold_break}_axis_{axis}", pp.LpMinimize)
            # variablen: in delta abgelegt
            delta_static = delta.copy() # aktuelle ordnungsmap
            for key in delta:
                if key[2] != axis: # nur zu optimierende Achse
                    continue
                if (isinstance(key[0], int) and isinstance(key[1], int)) or (isinstance(key[0], str) and isinstance(key[1], str)): 
                    delta_static[key] = pp.LpVariable(f"{key[0]}_{key[1]}_{key[2]}", cat="Binary")
                elif isinstance(key[0], int) and isinstance(key[1], str): # real < virtuell =  1
                    delta_static[key] = 1
                elif isinstance(key[0], str) and isinstance(key[1], int): # virtuell < real = 0
                    delta_static[key] = 0
            # zielfunktion
            pi_plus_idx = (phi_index_map[axis]+1) % len(phi) # achsen index in phi
            pi_plus_axis = phi[pi_plus_idx]
            pi_minus_idx = (phi_index_map[axis]-1) % len(phi)
            pi_minus_axis = phi[pi_minus_idx]
            pi_var = fused_groups[axis] # knotenliste von pi
            # pi_var = node_groups[axis] # knotenliste von pi
            sorted_neighbors = sorted_neighbor_map(neighborhood_map, node_axis_map, pi_var, pi_plus_axis, pi_minus_axis)
            prob += (induced_crossings(delta_static, sorted_neighbors, pi_minus_axis, axis, pi_var) + induced_crossings(delta_static, sorted_neighbors, pi_plus_axis, axis, pi_var)), "1L2S-Kreuzungsminimierung"
            # print(f"Zielfunktion: {prob.objective}")
            # print(f"Nachbarn Beispiel: {sorted_neighbors}")
            # nebenbedingungen
            for i in range(len(pi_var)):
                for j in range(i+1, len(pi_var)):
                    for k in range(j+1, len(pi_var)):
                        u, v, w = pi_var[i], pi_var[j], pi_var[k]
                        prob += delta_static[(u,v,axis)] + delta_static[(v,w,axis)] - delta_static[(u,w,axis)] <= 1
                        prob += delta_static[(u,v,axis)] + delta_static[(v,w,axis)] - delta_static[(u,w,axis)] >= 0 # prüfen: binärvariablen zwangsweise nicht negativ, ggf performanceleck
            
            # lösen
            # prob.solve(pp.PULP_CBC_CMD(msg=True))
            prob.solve(pp.PULP_CBC_CMD(msg=False))
            # schreibe problem um nach delta
            # print(f"Achse {axis}: pi_var={pi_var}, variables={[k for k in delta_static if isinstance(delta_static[k], pp.LpVariable)]}")
            for key in delta:
                if key[2] == axis and isinstance(delta_static[key], pp.LpVariable):
                    val = pp.value(delta_static[key])
                    if val is not None:
                        delta[key] = int(val)
    print(f"DELTA >>>>>>> {delta}")
        # for axis in reversed_phi:
        #     # probleminstanz
        #     prob = pp.LpProblem(f"1S2L_ILP_counter_clockwise_run_{threshold_break}_axis_{axis}", pp.LpMinimize)
        #     # variablen: in delta abgelegt
        #     # zielfunktion
        #     # nebenbedingungen
        #     # lösen
        #     prob.solve(pp.PULP_CBC_CMD(msg=True))
        #     # schreibe problem um nach delta

def delta_mapping(fused_groups: dict[int | str, list[int | str]]) -> dict[tuple[int | str, ...], 0 | 1]:
    """Dient der Initialisierung der Ordnungsvariablen (delta^i_u,v) für das 1L2S-ILP. Erzeugt aus der Vereinigung von virtuellen und realen Knoten das Mapping.

    Args:
        layout (HivePlotLayout): das zugrundeliegende Hiveplotlayout

    Returns:
        dict[tuple[int | str, ...], None]: key: (u, v, alpha(u,v)), value: None
    """
    delta = {}
    # node_groups = layout.node_groups
    # node_groups_dummies = layout.node_groups_dummies
    for axis, nodes in fused_groups.items():
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                delta[(nodes[i], nodes[j], axis)] = 1
                # print("----------------------------------")
                # print(f"{nodes[i]}:{isinstance(nodes[i], str)}")
                # print(f"{nodes[j]}:{isinstance(nodes[j], str)}")
                # print(f"{axis}:{isinstance(axis, int)}")
                # print("----------------------------------")
                delta[(nodes[j], nodes[i], axis)] = 0
    return delta

# def natural_order(delta, node_groups) -> dict[tuple[int | str, ...], int]:
#     # delta_native[key] = 0 | 1 (spiegelt die initiale ordnung auf den nodegroups wieder)
#     def key_to_constant(delta_key, order):
#         pass
#     delta_native = {}
#     current_axis = None
#     for key in delta:
#         if key[2] != current_axis:
#             current_axis = key[2]
#             order = node_groups[key[2]]
#         delta_native[key] = key_to_constant(key, order)
#     # return delta_native
#     pass

def induced_crossings(delta_static, sorted_neighbors, pi_fix, pi_var_id, pi_var): # C(pi, pi^+/-), Zielfunktion
    terms = []
    for i in range(len(pi_var)):
        for j in range(i+1, len(pi_var)):
            u = pi_var[i]
            v = pi_var[j]
            del_uv = delta_static[(u, v, pi_var_id)]
            del_vu = delta_static[(v, u, pi_var_id)]
            neigh_u = sorted_neighbors[pi_fix, u]
            neigh_v = sorted_neighbors[pi_fix, v]
            for s in neigh_u:
                for t in neigh_v:
                    if s == t: # nachbarlisten nicht zwangsweise disjunkt
                        continue
                    del_st = delta_static[(s, t, pi_fix)]
                    del_ts = delta_static[(t, s, pi_fix)]
                    terms.append(del_uv * del_ts + del_vu * del_st)
    return pp.lpSum(terms)


        # if key[0] == pi_fix:
        #         u = key[1]
        #         nbr = sorted_neighbors[key]
        #         for n in nbr:
        #             del_uv = delta_static[u, n, pi_var_id]
        #             del_ts = delta_static[u, n, pi_fix]

def ip_model_pipeline(layout: HivePlotLayout, threshold: float = float("inf")) -> None:
    # pipeline 3a <<<<<<<<<<<<
    # 1.
    isolated_nodes = cm.remove_isolated_nodes(layout.graph, layout.node_groups)
    # 2.
    node_position_map, node_axis_map = node_to_axis_maps(layout, layout.node_groups)
    neighborhood_map = layout.get_proper_neighborhood_map(layout.edges()) # initialisieren aus layout.graph
    cm.subdivide_long_edges(layout, node_position_map, node_axis_map, neighborhood_map)
    # print(f"DELTAGROUPS: {delta}")
    # print(f"ISOLATED NODES: {isolated_nodes}")
    # print(f"DUMMIES: {layout.node_groups_dummies}")
    # 3.
    fused_groups = layout.fuse_node_groups_with_dummies()
    # delta = delta_mapping(fused_groups)
    neighborhood_map = layout.get_proper_neighborhood_map(layout.fuse_edges_with_edge_dummies())
    node_position_map, node_axis_map = node_to_axis_maps(layout, fused_groups)
    onelayer_twosided_optimization(layout, neighborhood_map, node_axis_map)
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
    # cm.finish_structured_axis_orders(layout, isolated_nodes)

if __name__ == "__main__":
    print("##########################################")
    printer = 0 # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< PRINTER
    # graph_mode = 0
    # graph_mode = 1
    graph_mode = 2
    from src.graphs import sample_graph_selfconstructed, sample_graph_multipartite, sample_graph_caveman, sample_graph_selfconstructed_extended
    from src.hiveplot import HivePlotLayout
    # # from src.partitioning import louvain_community_detection
    from src.debug_renderer import render_debug
    # # logging.basicConfig(level=logging.DEBUG)
    G = sample_graph_selfconstructed_extended(graph_mode)
    nodes = list(G.nodes(data="subset"))
    axes = native_order(nodes)
    ng = node_groups(nodes)
    # print("Layout ORIGINAL")
    hpl = HivePlotLayout(
        graph=G,
        num_axes=len(axes),
        axis_order=axes,
        node_groups=ng
    )
    # delta = delta_mapping(hpl)
    # print(hpl)
    if printer == 1:
        render_debug(hpl, title="ORIGINAL") 
    # hpl.axis_order = brute_force_ordering(axes, ng, list(G.edges()))
    # hpl.node_groups = reordered_node_groups(ng, hpl.axis_order)
    if printer == 1:
        render_debug(hpl, title="OHNE PIPELINE - OPTIMIZED")
    ip_model_pipeline(hpl, threshold=1)
    # hpl.node_groups = hpl.fuse_node_groups_with_dummies() # ACHTUNG: FÜR RENDERING NÖTIG, LETZTE AKTUALISIERUNG VOR DER VISUALISIERUNG (Erweiterung der Achs)
    if printer == 1:
        render_debug(hpl, title="PIPELINE ABGESCHLOSSEN")
    print("##########################################")
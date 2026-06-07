import src.crossing_minimization as cm
from src import graphs
from src.cost import node_or_axes_span
from src.ordering import brute_force_ordering, native_order, node_groups, node_to_axis_maps, reordered_node_groups
import networkx as nx
import pulp as pp

def onelayer_twosided_optimization(layout: HivePlotLayout, neighborhood_map: dict[str|int, list[int | str]], node_axis_map: dict[str | int, int], threshold: int = int(10), expanded: bool = False) -> None:
    """Enthält die gesamte Logik, um das One Layer Two Sided Integer Linear Program (1L2S ILP) zu definieren und zu berechnen. Die Funktion verändert das HiveplotLayout in-place. Die Pipeline besteht aus Sweeps.
    Ein Sweep umfasst eine clockwise und eine counterclockwise Berechnung über jede Achse des Hiveplots. Folgende Schritte werden in der Funktion durchgeführt:
    1. Initialisierung der Ordnungsvariablen (delta^i_u,v) durch delta_mapping()
    2. Initialisierung der Sweepschleife, Abbruch bei Erreichen eines Thresholds
    3. Danach schließt sich ein Sweep an erst in clockwise dann counterclockwise Richtung, beide habe das gleiche Schema:
        a. Erstellen einer Probleminstanz und einer Kopie für die aktuelle Achse
        b. Initialisierung der Ordnungsvariablen für die aktuelle Achse (virtuelle und reale Knotenordnung werden in einem Schritt berechnet, aber die Achsenordnung real < virtuell muss berücksichtigt werden, da Gaps nicht explizit behandelt werden)
            I: Ordnungsvariablen getrennt für reale und virtuelle Achsenabschnitte
            II: Ordnungsvariablen für real < virtuell = konstant 1
            III: Ordnungsvariablen für virtuell < real = konstant 0
        c. Erstellen der Zielfunktion speziell für die variable Achse
        d. Erstellen der Nebenbedingungen für:
            I: Antisymmetrie (im Paper implizit behandelt)
            II: Transitivität
        e. Lösen des ILP
        f. Synchroniesieren der Lösung mit delta
    4. Aktualisieren des Layouts durch Übersetzung von delta zurück in die Achsenordnung, da die variable Achse auf einem geupdateten Stand ermittelt werden muss, wird dies am Ende eines Sweeps durchgeführt

    Args:
        layout (HivePlotLayout): _description_das zugrundeliegende HivePlotLayout
        neighborhood_map (dict[str | int, list[int  |  str]]): KnotenID: Liste von proper Nachbarn
        node_axis_map (dict[str  | int, int]): KnotenID: Achse
        threshold (int, optional): Anzahl der Sweeps (=1x cw+ 1x ccw), Defaultwert ist 10
        expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)
    """
    def sorted_neighbor_map(neighborhood_map: dict[str |int, list[int | str]], node_axis_map: dict[str |int, int], pi_var: list[int|str], pi_plus_axis: int, pi_minus_axis: int) -> dict[int, list[int | str]]:
        """Erzeugt ein dict, das für jeden Knoten in pi_var die Nachbarn auf der pi^+ und pi^- Achse enthält. Wird für die Zielfunktion benötigt, da hierdurch die Nachbarachsen von pi_var fixiert werden.

        Args:
            neighborhood_map (dict[str  | int, list[int | str]]): KnotenID: Liste von proper Nachbarn
            node_axis_map (dict[str  | int, int]): KnotenID: Achse
            pi_var (list[int | str]): variable Achsenordnung pi_i
            pi_plus_axis (int): fixierte Nachbarachse pi^+
            pi_minus_axis (int): fixierte Nachbarachse pi^-

        Returns:
            dict[int, list[int | str]]: (pi^+/pi^- ID, node aus pi_i): Liste der Nachbarn von node auf der jeweiligen Achse
        """
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
    
    def delta_to_order(delta: dict[tuple[int|str, int|str, int], int], fused_groups: dict[int, list[int|str]]) -> tuple[dict[int, list[int|str]], dict[int, list[int|str]]]:
        """Übersetzt und schreibt am Ende des Sweeps delta wieder zurück in das Layout.

        Args:
            delta (dict[tuple[int | str, int | str, int], int]): delta^i_u,v: 1 | 0
            fused_groups (dict[int, list[int | str]]): AchsenID: Knotenliste

        Returns:
            tuple[dict[int, list[int|str]], dict[int, list[int|str]]]: node_groups, node_groups_dummies 
        """
        new_node_groups = {}
        new_dummy_groups = {}
        for axis, nodes in fused_groups.items():
            positions = {u: sum(delta[(v, u, axis)] for v in nodes if v != u) for u in nodes} # rang = anzahl knoten die vor u kommen
            sorted_nodes = sorted(nodes, key=lambda u: positions[u])
            new_node_groups[axis]  = [n for n in sorted_nodes if isinstance(n, int)]
            new_dummy_groups[axis] = [n for n in sorted_nodes if isinstance(n, str)]
        return new_node_groups, new_dummy_groups

    # node_groups = layout.node_groups
    fused_groups =  layout.fuse_node_groups_with_dummies(expanded=expanded)
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
                    u, v = pi_var[i], pi_var[j]
                    uv = delta_static[(u, v, axis)]
                    vu = delta_static[(v, u, axis)]
                    if isinstance(uv, pp.LpVariable) and isinstance(vu, pp.LpVariable):
                        prob += uv + vu == 1 # antisymmetrie, im paper implizit angenommen
            for i in range(len(pi_var)): # transitivitätsbedingungen
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
        for axis in reversed_phi:
            # probleminstanz
            prob = pp.LpProblem(f"1S2L_ILP_counter_clockwise_run_{threshold_break}_axis_{axis}", pp.LpMinimize)
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
            for i in range(len(pi_var)): # antisymmetrie, im paper 
                for j in range(i+1, len(pi_var)):
                    u, v = pi_var[i], pi_var[j]
                    uv = delta_static[(u, v, axis)]
                    vu = delta_static[(v, u, axis)]
                    if isinstance(uv, pp.LpVariable) and isinstance(vu, pp.LpVariable):
                        prob += uv + vu == 1
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
        if expanded:
            layout.node_groups_expanded, layout.node_groups_dummies = delta_to_order(delta, fused_groups)
        else:
            layout.node_groups, layout.node_groups_dummies = delta_to_order(delta, fused_groups)
        fused_groups = layout.fuse_node_groups_with_dummies(expanded=expanded) # variable achse muss auf geupdatetem stand ermittelt werden
    # print(f"DELTA >>>>>>> {delta}")

def delta_mapping(fused_groups: dict[int|str, list[int|str]]) -> dict[tuple[int|str, ...], 0|1]:
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

def induced_crossings(delta_static: dict[tuple[int|str, int|str, int|str], int], sorted_neighbors: dict[int, list[int|str]], pi_fix: int, pi_var_id: int, pi_var: list[int|str]) -> pp.lpSum: # C(pi, pi^+/-), Zielfunktion
    """Bildet die C(pi_i, pi^+/-) Zielfunktion nach. Die Funktion arbeitet folgendermaßen:
    1. Betrachte paarweise Knoten u, v auf variabler Achse und ermittle die Ordungsvariablen uv und vu
    2. bestimme alle Nachbarn s von u und t von v auf der fixierten Achse und iteriere über alle Paare (s, t) mit s != t
    3. bestimme die Ordnungsvariablen st und ts
    4. Füge den Kreuzungsterm del_uv * del_ts + del_vu * del_st zur Zielfunktion hinzu
    5. Rückgabe der Summe aller Kreuzungsterme als Pulp-Ausdruck

    Args:
        delta_static (dict[tuple[int | str, int | str, int | str], int]): ordnungsvariable: belegung
        sorted_neighbors (dict[int, list[int | str]]): (pi^+/pi^- ID, node aus pi_i): Liste der Nachbarn von node auf der jeweiligen Achse
        pi_fix (int): AchsenID der fixierten Nachbarachse
        pi_var_id (int): AchsenID der variablen Achse
        pi_var (int): Liste der Knoten auf der variablen Achse

    Returns:
        pp.lpSum: Anzahl der induzierten Kreuzungen zwischen pi_var und pi_fix
    """
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

def ip_model_pipeline(layout: HivePlotLayout, threshold: int = int(10), expanded: bool = False) -> None:
    """Die Funktion führt die gesamte Pipeline zur Kreuzungsminimierung durch, inklusive der Berechnung des 1L2S-ILP. Alle Schritte werden in-place am HivePlotLayout durchgeführt. Ablauf:
    1. isolierte Knoten entfernen
    2. lange Kanten unterteilen
    3. 1L2S-ILP berechnen
    4. Behandlung der intra-axis Kreuzungen
    5. Herstellen der Achsenornung und letztes Update der Datenstrukturen um die Visualisierung starten zu können.

    Args:
        layout (HivePlotLayout): das zugrundeliegende Hiveplotlayout
        threshold (int, optional): Anzahl der Sweeps bis zum Abbruch, Defaultwert ist 10.
    """
    if expanded:
        # pipeline 3a <<<<<<<<<<<<
        # 1.
        node_position_map, node_axis_map = node_to_axis_maps(layout, layout.node_groups)
        neighborhood_map = layout.get_proper_neighborhood_map(layout.edges()) # initialisieren aus layout.graph
        layout.expand_axes(node_axis_map)
        # 2.
        isolated_nodes = cm.remove_isolated_nodes(layout.graph, layout.node_groups_expanded)
        node_position_map, node_axis_map = node_to_axis_maps(layout, layout.node_groups_expanded) # UPDATE mit n_g_expanded
        neighborhood_map = layout.get_proper_neighborhood_map(layout.edges(), expanded=expanded) # UPDATE
        cm.subdivide_long_edges(layout, node_position_map, node_axis_map, neighborhood_map)
        # 3.
        fused_edge_list = layout.fuse_edges_with_edge_dummies() # dummykanten einbeziehen
        fused_node_list = layout.fuse_node_groups_with_dummies(expanded=expanded) # UPDATE !!!
        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list) # UPDATE !!!
        neighborhood_map = layout.get_proper_neighborhood_map(fused_edge_list, expanded=expanded)
        onelayer_twosided_optimization(layout, neighborhood_map, node_axis_map, threshold=threshold, expanded=expanded)
        # print(f"REAL: {layout.node_groups}")
        # print(f"DUMMY: {layout.node_groups_dummies}")
        # 5.
        # cm.intra_axis_handler(layout)
        # 6.
        cm.finish_structured_axis_orders(layout, isolated_nodes, expanded=expanded)
    else:
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
        fused_edge_list = layout.fuse_edges_with_edge_dummies() # dummykanten einbeziehen
        fused_node_list = layout.fuse_node_groups_with_dummies(expanded=expanded) # UPDATE !!!
        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list) # UPDATE !!!
        neighborhood_map = layout.get_proper_neighborhood_map(fused_edge_list, expanded=expanded)
        onelayer_twosided_optimization(layout, neighborhood_map, node_axis_map, threshold=threshold)
        # print(f"REAL: {layout.node_groups}")
        # print(f"DUMMY: {layout.node_groups_dummies}")
        # 5.
        # cm.intra_axis_handler(layout)
        # 6.
        cm.finish_structured_axis_orders(layout, isolated_nodes, expanded=expanded)

if __name__ == "__main__":
    print("##########################################")
    printer = 1 # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< PRINTER
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
    hpl.axis_order = brute_force_ordering(axes, ng, list(G.edges()))
    hpl.node_groups = reordered_node_groups(ng, hpl.axis_order)
    if printer == 1:
        render_debug(hpl, title="OHNE PIPELINE - OPTIMIZED")
    ip_model_pipeline(hpl, threshold=1, expanded=True)
    # ip_model_pipeline(hpl, threshold=1)
    if printer == 1:
        render_debug(hpl, title="PIPELINE ABGESCHLOSSEN")
    print(hpl)
    print(hpl.edges())
    print("##########################################")
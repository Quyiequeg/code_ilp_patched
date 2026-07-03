import crossing_minimization as cm
from src import graphs
from cost import node_or_axes_span
from ordering import brute_force_ordering, native_order, node_groups, node_to_axis_maps, reordered_node_groups
import networkx as nx
import pulp as pp
import logging
from logger_setup import log
from hiveplot import HivePlotLayout

def get_delta_value(delta, fixed_delta, u, v, axis):
    key = (u, v, axis)

    if key in fixed_delta:
        return fixed_delta[key]

    if key in delta:
        return delta[key]

    if isinstance(u, int) and isinstance(v, int) and isinstance(axis, int):
        mirrored_key = (-u, -v, -axis)

        if mirrored_key in fixed_delta:
            return fixed_delta[mirrored_key]

        if mirrored_key in delta:
            return delta[mirrored_key]

    raise KeyError(key)

def ilp_name(*parts):
    return "_".join(str(p).replace("-", "m") for p in parts)

def onelayer_twosided_optimization(layout: HivePlotLayout, neighborhood_map: dict[str|int, list[int | str]], node_axis_map: dict[str | int, int], threshold: int = int(10), layout_expanded: bool = False, paper_like: bool = False) -> None:
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
    def sorted_neighbor_map_3a(neighborhood_map: dict[str |int, list[int | str]], node_axis_map: dict[str |int, int], pi_var: list[int|str], pi_plus_axis: int, pi_minus_axis: int) -> dict[int, list[int | str]]:
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

    fused_groups =  layout.fuse_node_groups_with_dummies(layout_expanded=layout_expanded)
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
            sorted_neighbors = sorted_neighbor_map_3a(neighborhood_map, node_axis_map, pi_var, pi_plus_axis, pi_minus_axis)
            prob += (induced_crossings(prob, delta_static, {}, sorted_neighbors, pi_minus_axis, axis, pi_var) + induced_crossings(prob, delta_static, {}, sorted_neighbors, pi_plus_axis, axis, pi_var)), "1L2S-Kreuzungsminimierung"
            # nebenbedingungen
            for i in range(len(pi_var)): 
                for j in range(i+1, len(pi_var)):
                    u, v = pi_var[i], pi_var[j]
                    uv = delta_static[(u, v, axis)]
                    vu = delta_static[(v, u, axis)]
                    if isinstance(uv, pp.LpVariable) and isinstance(vu, pp.LpVariable):
                        prob += uv + vu == 1 # vollständigkeit der totalordnung sicherstellen, im paper implizit angenommen für delta^i_u, v
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
            sorted_neighbors = sorted_neighbor_map_3a(neighborhood_map, node_axis_map, pi_var, pi_plus_axis, pi_minus_axis)
            prob += (induced_crossings(prob, delta_static, {}, sorted_neighbors, pi_minus_axis, axis, pi_var) + induced_crossings(prob, delta_static, {}, sorted_neighbors, pi_plus_axis, axis, pi_var)), "1L2S-Kreuzungsminimierung"
            
            for i in range(len(pi_var)): # antisymmetrie, im paper 
                for j in range(i+1, len(pi_var)):
                    u, v = pi_var[i], pi_var[j]
                    uv = delta_static[(u, v, axis)]
                    vu = delta_static[(v, u, axis)]
                    if isinstance(uv, pp.LpVariable) and isinstance(vu, pp.LpVariable): 
                        prob += uv + vu == 1 # vollständigkeit der totalordnung sicherstellen, im paper implizit angenommen für delta^i_u, v
            for i in range(len(pi_var)):
                for j in range(i+1, len(pi_var)):
                    for k in range(j+1, len(pi_var)):
                        u, v, w = pi_var[i], pi_var[j], pi_var[k]
                        prob += delta_static[(u,v,axis)] + delta_static[(v,w,axis)] - delta_static[(u,w,axis)] <= 1
                        prob += delta_static[(u,v,axis)] + delta_static[(v,w,axis)] - delta_static[(u,w,axis)] >= 0 # prüfen: binärvariablen zwangsweise nicht negativ, ggf performanceleck
            
            # lösen
            # prob.solve(pp.PULP_CBC_CMD(msg=True))
            prob.solve(pp.PULP_CBC_CMD(msg=False))
            if threshold_break == threshold - 1:
                layout.crossings = pp.value(prob.objective)
            # schreibe problem um nach delta
            for key in delta:
                if key[2] == axis and isinstance(delta_static[key], pp.LpVariable):
                    val = pp.value(delta_static[key])
                    if val is not None:
                        delta[key] = int(val)
        if layout_expanded:
            layout.node_groups_expanded, layout.node_groups_dummies = delta_to_order(delta, fused_groups)
        else:
            layout.node_groups, layout.node_groups_dummies = delta_to_order(delta, fused_groups)
        fused_groups = layout.fuse_node_groups_with_dummies(layout_expanded=layout_expanded) # variable achse muss auf geupdatetem stand ermittelt werden

def linearize_product(prob, a, b, name):
    if isinstance(a, int) and isinstance(b, int):
        return a * b

    if isinstance(a, int):
        if a == 0:
            return 0
        return b

    if isinstance(b, int):
        if b == 0:
            return 0
        return a

    z = pp.LpVariable(ilp_name(name), cat="Binary")
    prob += z <= a
    prob += z <= b
    prob += z >= a + b - 1
    # z >= 0 unnötig, da z binär

    return z

def delta_mapping(fused_groups: dict[int|str, list[int|str]]) -> dict[tuple[int|str, ...], 0|1]:
    """Dient der Initialisierung der Ordnungsvariablen (delta^i_u,v) für das 1L2S-ILP. Erzeugt aus der Vereinigung von virtuellen und realen Knoten das Mapping.

    Args:
        layout (HivePlotLayout): das zugrundeliegende Hiveplotlayout

    Returns:
        dict[tuple[int | str, ...], None]: key: (u, v, alpha(u,v)), value: None
    """
    delta = {}
    for axis, nodes in fused_groups.items():
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                delta[(nodes[i], nodes[j], axis)] = 1
                delta[(nodes[j], nodes[i], axis)] = 0
    return delta

def onelayer_twosided_optimization_3b(layout: HivePlotLayout, neighborhood_map: dict[str|int, list[int | str]], node_axis_map: dict[str | int, int], threshold: int = int(10), layout_expanded: bool = False, paper_like: bool =  False) -> None:
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
    def sorted_neighbor_map_3b(neighborhood_map: dict[str |int, list[int | str]], node_axis_map: dict[str |int, int], pi_var: list[int|str], pi_plus_axis: int, pi_minus_axis: int) -> dict[int, list[int | str]]:
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
            if pi_minus_axis == pi_plus_axis:
                sorted_neighbors[(pi_minus_axis, node)] = list(dict.fromkeys(minus_list + plus_list))
            else:
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
        
        fixed_delta = layout.fixed_inter_axis_delta
        if fixed_delta is None:
            fixed_delta = {}

        new_node_groups = {}
        new_dummy_groups = {}
        for axis, nodes in fused_groups.items():
            positions = {}

            for u in nodes:
                position = 0

                for v in nodes:
                    if v != u:
                        position += get_delta_value(delta, fixed_delta, v, u, axis)

                positions[u] = position # rang = anzahl knoten die vor u kommen
            sorted_nodes = sorted(nodes, key=lambda u: positions[u])
            new_node_groups[axis]  = [n for n in sorted_nodes if isinstance(n, int)]
            new_dummy_groups[axis] = [n for n in sorted_nodes if isinstance(n, str)]
        return new_node_groups, new_dummy_groups
    # node_groups = layout.node_groups
    fused_groups =  layout.fuse_node_groups_with_dummies(layout_expanded=layout_expanded)
    phi = layout.axis_order
    reversed_phi = list(reversed(phi))
    phi_index_map = {}
    for index, axis in enumerate(phi):
        phi_index_map[axis] = index
    delta = delta_mapping(fused_groups)
    threshold_break = 0
    fixed_delta = layout.fixed_inter_axis_delta

    if fixed_delta is None:
        fixed_delta = {}
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
                if key in fixed_delta:
                    continue
                if (isinstance(key[0], int) and isinstance(key[1], int) and isinstance(key[2], int)): 
                    mirrored_key = (-key[0], -key[1], -key[2])
                    if mirrored_key in fixed_delta:
                        continue
                if (isinstance(key[0], int) and isinstance(key[1], int)): 
                    pp.LpVariable(ilp_name(key[0], key[1], key[2]), cat="Binary")
                elif isinstance(key[0], int) and isinstance(key[1], str): # real < virtuell =  1
                    delta_static[key] = 1
                elif isinstance(key[0], str) and isinstance(key[1], int): # virtuell < real = 0
                    delta_static[key] = 0
            pi_plus_idx = (phi_index_map[axis]+1) % len(phi) # achsen index in phi
            pi_plus_axis = phi[pi_plus_idx]
            pi_minus_idx = (phi_index_map[axis]-1) % len(phi)
            pi_minus_axis = phi[pi_minus_idx]
            pi_var = fused_groups[axis] # knotenliste von pi
            
            if len(pi_var) == 0:
                continue
            
            mirror_axis = -axis

            sorted_neighbors = sorted_neighbor_map_3b(
                neighborhood_map,
                node_axis_map,
                pi_var,
                mirror_axis,
                mirror_axis,
            )
            # prob += (induced_crossings(prob, delta_static, fixed_delta, sorted_neighbors, pi_minus_axis, axis, pi_var) + induced_crossings(prob, delta_static, fixed_delta, sorted_neighbors, pi_plus_axis, axis, pi_var)), "1L2S-Kreuzungsminimierung"
            prob += induced_crossings(
                prob,
                delta_static,
                fixed_delta,
                sorted_neighbors,
                mirror_axis,
                axis,
                pi_var,
            ), "1L2S-Kreuzungsminimierung"
            
            # print(f"Zielfunktion: {prob.objective}")
            # print(f"Nachbarn Beispiel: {sorted_neighbors}")
            # nebenbedingungen
            for i in range(len(pi_var)): 
                for j in range(i+1, len(pi_var)):
                    u, v = pi_var[i], pi_var[j]
                    uv = get_delta_value(delta_static, fixed_delta, u, v, axis)
                    vu = get_delta_value(delta_static, fixed_delta, v, u, axis)
                    prob += uv + vu == 1 # vollständigkeit der totalordnung sicherstellen, im paper implizit angenommen für delta^i_u, v
            
            for i in range(len(pi_var)):
                for j in range(i + 1, len(pi_var)):
                    for k in range(j + 1, len(pi_var)):
                        u, v, w = pi_var[i], pi_var[j], pi_var[k]
                        uv = get_delta_value(delta_static, fixed_delta, u, v, axis)
                        vw = get_delta_value(delta_static, fixed_delta, v, w, axis)
                        uw = get_delta_value(delta_static, fixed_delta, u, w, axis)
                        prob += uv + vw - uw <= 1
                        prob += uv + vw - uw >= 0 # prüfen: binärvariablen zwangsweise nicht negativ, ggf performanceleck
            
            # lösen
            # prob.solve(pp.PULP_CBC_CMD(msg=True))
            prob.solve(pp.PULP_CBC_CMD(msg=False, timeLimit=30))
            # schreibe problem um nach delta
            # print(f"Achse {axis}: pi_var={pi_var}, variables={[k for k in delta_static if isinstance(delta_static[k], pp.LpVariable)]}")
            for key in delta:
                if key[2] != axis:
                    continue

                if key in fixed_delta:
                    continue

                if (
                    isinstance(key[0], int)
                    and isinstance(key[1], int)
                    and isinstance(key[2], int)
                ):
                    mirrored_key = (-key[0], -key[1], -key[2])

                    if mirrored_key in fixed_delta:
                        continue

                if isinstance(delta_static[key], pp.LpVariable):
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
                if key in fixed_delta:
                    continue
                if (isinstance(key[0], int) and isinstance(key[1], int)): 
                    delta_static[key] = pp.LpVariable(ilp_name(key[0], key[1], key[2]), cat="Binary")
                elif isinstance(key[0], int) and isinstance(key[1], str): # real < virtuell =  1
                    delta_static[key] = 1
                elif isinstance(key[0], str) and isinstance(key[1], int): # virtuell < real = 0
                    delta_static[key] = 0
            pi_plus_idx = (phi_index_map[axis]+1) % len(phi) # achsen index in phi
            pi_plus_axis = phi[pi_plus_idx]
            pi_minus_idx = (phi_index_map[axis]-1) % len(phi)
            pi_minus_axis = phi[pi_minus_idx]
            pi_var = fused_groups[axis] # knotenliste von pi

            if len(pi_var) == 0:
                continue
            mirror_axis = -axis
            
            # sorted_neighbors = sorted_neighbor_map(neighborhood_map, node_axis_map, pi_var, pi_plus_axis, pi_minus_axis)
            sorted_neighbors = sorted_neighbor_map_3b(
                neighborhood_map,
                node_axis_map,
                pi_var,
                mirror_axis,
                mirror_axis,
            )
            # prob += (induced_crossings(prob, delta_static, fixed_delta, sorted_neighbors, pi_minus_axis, axis, pi_var) + induced_crossings(prob, delta_static, fixed_delta, sorted_neighbors, pi_plus_axis, axis, pi_var)), "1L2S-Kreuzungsminimierung"
            prob += induced_crossings(
                prob,
                delta_static,
                fixed_delta,
                sorted_neighbors,
                mirror_axis,
                axis,
                pi_var,
            ), "1L2S-Kreuzungsminimierung"
            
            # nebenbedingungen
            for i in range(len(pi_var)): # antisymmetrie, im paper 
                for j in range(i+1, len(pi_var)):
                    u, v = pi_var[i], pi_var[j]
                    uv = get_delta_value(delta_static, fixed_delta, u, v, axis)
                    vu = get_delta_value(delta_static, fixed_delta, v, u, axis)
                    prob += uv + vu == 1 # vollständigkeit der totalordnung sicherstellen, im paper implizit angenommen für delta^i_u, v
            for i in range(len(pi_var)):
                for j in range(i + 1, len(pi_var)):
                    for k in range(j + 1, len(pi_var)):
                        u, v, w = pi_var[i], pi_var[j], pi_var[k]
                        uv = get_delta_value(delta_static, fixed_delta, u, v, axis)
                        vw = get_delta_value(delta_static, fixed_delta, v, w, axis)
                        uw = get_delta_value(delta_static, fixed_delta, u, w, axis)
                        prob += uv + vw - uw <= 1
                        prob += uv + vw - uw >= 0 # prüfen: binärvariablen zwangsweise nicht negativ, ggf performanceleck
            
            # lösen
            # prob.solve(pp.PULP_CBC_CMD(msg=True))
            prob.solve(pp.PULP_CBC_CMD(msg=False, timeLimit=30))

            # schreibe problem um nach delta
            for key in delta:
                if key[2] != axis:
                    continue

                if key in fixed_delta:
                    continue

                if (
                    isinstance(key[0], int)
                    and isinstance(key[1], int)
                    and isinstance(key[2], int)
                ):
                    mirrored_key = (-key[0], -key[1], -key[2])

                    if mirrored_key in fixed_delta:
                        continue

                if isinstance(delta_static[key], pp.LpVariable):
                    val = pp.value(delta_static[key])

                    if val is not None:
                        delta[key] = int(val)
        if layout_expanded:
            layout.node_groups_expanded, layout.node_groups_dummies = delta_to_order(delta, fused_groups)
        else:
            layout.node_groups, layout.node_groups_dummies = delta_to_order(delta, fused_groups)
        fused_groups = layout.fuse_node_groups_with_dummies(layout_expanded=layout_expanded) # variable achse muss auf geupdatetem stand ermittelt werden

def induced_crossings(prob, delta_static, fixed_delta, sorted_neighbors, pi_fix, pi_var_id, pi_var):
    terms = []
    for i in range(len(pi_var)):
        for j in range(i + 1, len(pi_var)):
            u = pi_var[i]
            v = pi_var[j]
            del_uv = get_delta_value(delta_static, fixed_delta, u, v, pi_var_id)
            del_vu = get_delta_value(delta_static, fixed_delta, v, u, pi_var_id)
            neighbor_u = sorted_neighbors[(pi_fix, u)]
            neighbor_v = sorted_neighbors[(pi_fix, v)]
            for s in neighbor_u:
                for t in neighbor_v:
                    if s == t:
                        continue
                    del_st = get_delta_value(delta_static, fixed_delta, s, t, pi_fix)
                    del_ts = get_delta_value(delta_static, fixed_delta, t, s, pi_fix)
                    # terms.append(del_uv * del_ts + del_vu * del_st)
                    z1 = linearize_product(prob, del_uv, del_ts, f"z_{u}_{v}_{s}_{t}_{pi_var_id}_{pi_fix}_1")
                    z2 = linearize_product(prob, del_vu, del_st, f"z_{v}_{u}_{s}_{t}_{pi_var_id}_{pi_fix}_2")
                    terms.append(z1 + z2)
    return pp.lpSum(terms)

def ip_model_pipeline(layout: HivePlotLayout, logger: logging.Logger, threshold: int = int(10), paper_like: bool = True) -> None:
    """Die Funktion führt die gesamte Pipeline zur Kreuzungsminimierung durch, inklusive der Berechnung des 1L2S-ILP. Alle Schritte werden in-place am HivePlotLayout durchgeführt.
    Ablauf expandiert:
    1. anfängliches Layout expandieren
    2. isolierte Knoten entfernen
    3. lange Kanten unterteilen und Dummyknoten einfügen (virtuelle Knoten)
    4. 1L2S-ILP berechnen
    5. Herstellen der Achsenornung und letztes Update der Datenstrukturen um die Visualisierung starten zu können.

    Ablauf nicht expandiert:
    1. isolierte Knoten entfernen
    2. lange Kanten unterteilen und Dummyknoten einfügen (virtuelle Knoten)
    3. 1L2S-ILP berechnen
    4. Behandlung der intra-axis Kreuzungen
    5. Herstellen der Achsenornung und letztes Update der Datenstrukturen um die Visualisierung starten zu können.

    Args:
        layout (HivePlotLayout): das zugrundeliegende Hiveplotlayout
        threshold (int, optional): Anzahl der Sweeps bis zum Abbruch, Defaultwert ist 10.
        expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)

    """
    if paper_like:
        layout_expanded = False
        isolated_nodes = cm.remove_isolated_nodes(layout.graph, layout.node_groups)

        node_position_map, node_axis_map = node_to_axis_maps(layout, layout.node_groups)
        neighborhood_map = layout.get_proper_neighborhood_map(layout.edges())

        cm.subdivide_long_edges(layout, node_position_map, node_axis_map, neighborhood_map)
        fused_edge_list = layout.fuse_edges_with_edge_dummies()
        fused_node_list = layout.fuse_node_groups_with_dummies(layout_expanded = layout_expanded)

        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list)
        neighborhood_map = layout.get_proper_neighborhood_map(
            fused_edge_list,
            layout_expanded,
        )
                # ---------- Pipeline 3a ----------
        onelayer_twosided_optimization(
            layout,
            neighborhood_map,
            node_axis_map,
            threshold=threshold,
            layout_expanded = layout_expanded,
            paper_like=paper_like
        )
        
        # ---------- Vorbereitung Pipeline 3b ----------
        layout.classify_nodes_for_3b()
        layout.freeze_inter_axis_delta()
        layout.post_processing_expansion(node_axis_map)
        layout_expanded = True

        fused_edge_list = layout.fuse_edges_with_edge_dummies()
        fused_node_list = layout.fuse_node_groups_with_dummies(layout_expanded=layout_expanded)

        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list)
        neighborhood_map = layout.get_proper_neighborhood_map(
            fused_edge_list,
            layout_expanded = layout_expanded,
        )
        # ---------- Pipeline 3b ----------
        onelayer_twosided_optimization_3b(
            layout,
            neighborhood_map,
            node_axis_map,
            threshold=threshold,
            layout_expanded = layout_expanded,
            paper_like=paper_like
        )
        cm.finish_structured_axis_orders(
            layout,
            isolated_nodes,
            layout_expanded = layout_expanded,
        )
    else:
        layout_expanded = False
        isolated_nodes = cm.remove_isolated_nodes(layout.graph, layout.node_groups)

        node_position_map, node_axis_map = node_to_axis_maps(layout, layout.node_groups)
        neighborhood_map = layout.get_proper_neighborhood_map(layout.edges())

        cm.subdivide_long_edges(layout, node_position_map, node_axis_map, neighborhood_map)
        # print("edges sample after subdivide", list(layout.edges())[:10])
        fused_edge_list = layout.fuse_edges_with_edge_dummies()
        fused_node_list = layout.fuse_node_groups_with_dummies(layout_expanded = layout_expanded)

        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list)
        neighborhood_map = layout.get_proper_neighborhood_map(
            fused_edge_list,
            layout_expanded,
        )

        # ---------- Pipeline 3a ----------
        onelayer_twosided_optimization(
            layout,
            neighborhood_map,
            node_axis_map,
            threshold=threshold,
            layout_expanded = layout_expanded,
            paper_like=paper_like
        )
        
        # ---------- Vorbereitung Pipeline 3b ----------
        layout.classify_nodes_for_3b()
        layout.freeze_inter_axis_delta()
        layout.post_processing_expansion(node_axis_map)
        layout_expanded = True

        fused_edge_list = layout.fuse_edges_with_edge_dummies()
        fused_node_list = layout.fuse_node_groups_with_dummies(layout_expanded=layout_expanded)

        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list)
        neighborhood_map = layout.get_proper_neighborhood_map(
            fused_edge_list,
            layout_expanded = layout_expanded,
        )

        # ---------- Pipeline 3b ----------
        onelayer_twosided_optimization_3b(
            layout,
            neighborhood_map,
            node_axis_map,
            threshold=threshold,
            layout_expanded = layout_expanded,
            paper_like=paper_like
        )
        cm.finish_structured_axis_orders(
            layout,
            isolated_nodes,
            layout_expanded = layout_expanded,
        )
     
if __name__ == "__main__":
    pass
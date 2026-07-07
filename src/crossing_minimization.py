from hiveplot import HivePlotLayout
from cost import node_or_axes_span
import networkx as nx
import logging
from logger_setup import log

def subdivide_long_edges(layout: HivePlotLayout, node_position_map: dict[int | str, int], node_axis_map: dict[int | str, int], neighborhood_map: dict[int | str, list[int | str]]) -> None:
    """Funktion dient dem Einfügen von Dummyknoten für lange Kanten (span > 1) auf den Achsen zwischen Start- und Endknoten. Schema: d_[Startknoten]_[Endknoten]_[Sequenznummer]: z.B. d_5_10_2 ist der zweite Dummyknoten auf der zerlegten langen Kante von 5 nach 10. Die lange Kante kann dann folgendermaßen beschrieben werden:
    Startknoten - d_5_10_1 - d_5_10_2 - ... - d_5_10_(span-1) - Endknoten. Außerdem werden die inter axis Knoten (Span = 0) ermittelt und gefiltert, um später die Achsenreihenfolge sauber zu ermitteln und die Pipelineschritte zu Initialisieren. Gefiltert bedeutet hier:
    1. nur intra axis die nicht mixed sind (vgl. nested: is_mixed, werden in 3b behandelt)
    2. mixed (inter + intra, werden nur in 3a nicht aber in 3b berücksichtigt)
    Reine intra-axis Knoten werden aus den regulären node_groups entfernt und ihre Kanten vorübergehend aus dem Graphen gelöscht. Am Ende der Pipeline werden alle Informationen wieder konsistent zusammengesetzt.

    Args:
        layout (HivePlotLayout): Das HivePlotLayout-Objekt, das die Informationen über den Graphen, die Achsen und die Knoten enthält.
        node_position_map (dict[int | str, int]): Knoten-ID: Achsenindex in phi.
        node_axis_map (dict[int | str, int]): Knoten-ID: Achse
        neighborhood_map (neighborhood_map: dict[int | str, list[int | str]]): Knoten-ID: Nachbarknoten (:= proper = Span = 1)

    Return:
        None. Die Funktion arbeitet in-place auf dem übergebenen Layout
    """
    def make_dummy_name(start_node: int, end_node: int, sequence_number: int) -> str:
        """Konstruktor für die Bennenung von Dummyknoten.
        Args:
            start_node (int): Startknoten ursprüngliche Kante
            end_node (int): Endknoten ursprüngliche Kante
            sequence_number (int): Wievielter Dummyknoten zwischen Start und Ende, beginnend bei 1

        Returns:
            str: Der Name des Dummyknotens
        """
        return f"d_{start_node}_{end_node}_{sequence_number}"
    
    def clockwise_count(start_pos: int, start_node: int, end_node: int, span: int) -> None:
        """Fügt Dummy-Knoten für eine Kante im Uhrzeigersinn ein. span: Wieviele Achsen die Kante zwischen Start und Endknoten überspannt. span-1 ist die Anzahl der Dummyknoten. Zusätzlich wird das Feld dummy_edge_segments im Hiveplotlayout mit den Dummy-Kanten gefüllt."""
        dummyposition = (start_pos + 1) % k
        sequence_number = 1
        previous = start_node
        for _ in range(span-1): # achsen zwischen start und ende
            current_dummy = make_dummy_name(start_node, end_node, sequence_number)
            axis = layout.axis_order[dummyposition] # position -> achse
            dummies[axis].append(current_dummy) # name unikal pro achse, achsensegmente leicht rekonstruierbar
            dummy_edges.append((previous, current_dummy)) # dummy edge von vorherigem knoten zum aktuellen dummy
            previous = current_dummy
            dummyposition = (dummyposition + 1) % k
            sequence_number += 1
        long_edges.add((start_node, end_node))
        dummy_edges.append((previous, end_node))

    def counter_clockwise_count(start_pos: int, start_node: int, end_node: int, span: int) -> None:
        """Fügt Dummy-Knoten für eine Kante gegen den Uhrzeigersinn ein. span: Wieviele Achsen die Kante zwischen Start und Endknoten überspannt. span-1 ist die Anzahl der Dummyknoten. Zusätzlich wird das Feld dummy_edge_segments im Hiveplotlayout mit den Dummy-Kanten gefüllt."""
        dummyposition = (start_pos - 1) % k
        sequence_number = 1
        previous = start_node
        for _ in range(span-1): # achsen zwischen start und ende
            current_dummy = make_dummy_name(start_node, end_node, sequence_number)
            axis = layout.axis_order[dummyposition] # position -> achse
            dummies[axis].append(current_dummy) # name unikal pro achse, achsensegmente leicht rekonstruierbar
            dummy_edges.append((previous, current_dummy)) # dummy edge von vorherigem knoten zum aktuellen dummy
            previous = current_dummy
            dummyposition = (dummyposition - 1) % k
            sequence_number += 1
        long_edges.add((start_node, end_node))
        dummy_edges.append((previous, end_node))
    
    def is_mixed(node: int, node_position_map: dict[int | str, int], neighborhood_map: dict[int | str, list[int | str]]) -> bool:
        """Prüft, ob ein Knoten sowohl intra- als auch inter-axis Nachbarn besitzt.

        Ein Knoten ist „mixed“, wenn mindestens ein Nachbar auf einer anderen Achse
        liegt als der Knoten selbst.

        Args:
            node: Zu prüfender Knoten.
            node_position_map: Map von Knoten auf Achsenpositionen in phi.
            neighborhood_map: Map von Knoten auf ihre Nachbarn (real bzw. virtuell).

        Returns:
            bool: True für mixed, False reiner intra axis Knoten
        """
        neighbors = neighborhood_map[node]
        is_mixed = False
        for neighbor in neighbors:
            if node_position_map[node] != node_position_map[neighbor]:
                is_mixed = True
        return is_mixed
    
    # initialisierung
    layout.intra_axis_nodes = {key: [] for key in layout.node_groups}
    k = layout.num_axes
    edges = layout.edges()
    long_edges = layout.long_edges
    dummy_edges = layout.dummy_edge_segments
    dummies = layout.node_groups_dummies
    for axis in layout.axis_order: # initialisiere dummyliste, schreibt explizit in die HivePlotLayout Instanz
        dummies[axis] = []
    intra_candidate_edge_list = layout.intra_axis_edges # alle kandidaten aufnehmen und nach reinen intra axis filtern
    intra_candidate_node_list = [] # alle kandidaten aufnehmen und nach reinen intra axis filtern

    # filtern der knoten und bestimmung des spans
    for edge in edges:
        start_pos = node_position_map[edge[0]] # startpositioon
        end_pos = node_position_map[edge[1]] # endposition
        span = node_or_axes_span(start_pos, end_pos, k)
        if span > 1: # direkte behandlung von langen kanten (dummy knoten erzeugen), proper ignorieren
            if (start_pos - end_pos) % k >= (end_pos - start_pos) % k: # richtung start -> ende
                clockwise_count(start_pos, edge[0], edge[1], span)
            elif (start_pos - end_pos) % k < (end_pos - start_pos) % k: # richtung ende <- start, counter cw
                counter_clockwise_count(start_pos, edge[0], edge[1], span)
        elif span == 0: # intra axis candidaten sammeln und im anschluss nach komponenten ohne mixed knoten filtern
            intra_candidate_edge_list.append(edge) # sammelt span 0 kanten
            for node in edge:
                if node not in intra_candidate_node_list:
                    intra_candidate_node_list.append(node) # sammelt intra axis knoten
    
    # filterung nach strict-intra und mixed
    zero_span_subgraph = nx.Graph() # knoten aus intra axis knoten initialisieren
    zero_span_subgraph.add_edges_from(intra_candidate_edge_list) # kanten automatisch einfügen, kanten aus möglichen kandidaten für intra axis beziehen
    ignore_set = set() # komponenten, die einen mixed knoten haben (sollen nicht angefasst werden)
    for node in intra_candidate_node_list:
        if is_mixed(node, node_axis_map, neighborhood_map) and node not in ignore_set:
                ignore_set.update(nx.node_connected_component(zero_span_subgraph, node))
    for node in ignore_set: # listen nach reinen intra axis knoten filtern
        intra_candidate_node_list.remove(node) # mögliche fehlerquelle, falls elemente anderer achsen in komponenten rutschen, sollte aber ausgeschlossen sein, prüfen!
        edges_copy = intra_candidate_edge_list.copy()
        for edge_candidate in edges_copy:
            if node in edge_candidate:
                intra_candidate_edge_list.remove(edge_candidate)
    for node in intra_candidate_node_list:
        axis = node_axis_map[node]
        layout.intra_axis_nodes[axis].append(node)
 
    # atkualisieren der datenstrukturen
    layout.graph.remove_edges_from(intra_candidate_edge_list)
    layout.graph.remove_edges_from(long_edges)
    layout.graph.add_edges_from(dummy_edges)

def parse_dummy_name(name: str) -> tuple[int, int, int]:
    """Zerlegt den Namen eines Dummyknotens in seine Bestandteile: Startknoten, Endknoten und Sequenznummer. (siehe make_dummy_name Funktion für Namensschema)

    Args:
        name (str): Der zu zerlegende Dummyknoten

    Returns:
        tuple[int, int, int]: Tupel aus int-Werten: (Startknoten, Endknoten, Sequenznummer)
    """
    parts = name.split("_")
    return int(parts[1]), int(parts[2]), int(parts[3])

def remove_isolated_nodes(graph: nx.Graph, node_groups: dict[int, list[int]]) -> dict[int, list[int]]:
    """Die Funktion entfernt alle isolierten Knoten aus der persistenten node_group des HivePlotLayouts.

    Args:
        graph (nx.Graph): Der zugrundeliegende Graph aus dem HivePlotLayout.
        node_groups (dict[str, list[int]]): Die persistente Knotenlisten der Achsen.
    Returns:
        dict[str, list[int]]: Ein dict mit den isolierten Knoten pro Achse, key: Achse, value: Listen mit isolierten Knoten.
    """
    isolated_node_groups = {key: [] for key in node_groups}
    for key in node_groups:
        non_isolated_node_groups = []
        for node in node_groups[key]:
            if nx.is_isolate(graph, node):
                isolated_node_groups[key].append(node)
            else:
                non_isolated_node_groups.append(node)
        node_groups[key] = non_isolated_node_groups
    return isolated_node_groups

def finish_structured_axis_orders(layout: HivePlotLayout, isolated_node_groups: dict[str, list[int]], layout_expanded: bool = False) -> None:
    """Aktualisiert die node_groups am Ende der Pipeline und fügt isolierte Knoten wieder ein."""
    def _attach_isolated_nodes(node_groups, isolated_node_groups):
        for key in node_groups:
            if key in isolated_node_groups:
                node_groups[key].extend(isolated_node_groups[key])

    if layout_expanded:
        _attach_isolated_nodes(layout.node_groups_expanded, isolated_node_groups)
        layout.node_groups_expanded = layout.fuse_node_groups_with_dummies(layout_expanded)
    else:
        _attach_isolated_nodes(layout.node_groups, isolated_node_groups)
        layout.node_groups = layout.fuse_node_groups_with_dummies()

def barycenter_heuristic(layout: HivePlotLayout, neighborhood_map: dict[int | str, list[int | str]], node_axis_map: dict[int | str, int], threshold = float("inf"), real: bool = True, layout_expanded: bool = False, use_fixed_positions: bool = False) -> None:
    """Führt wiederholte Barycenter-Sweeps im und gegen den Uhrzeigersinn über alle Achsen aus. Abhängig vom Parameter real werden entweder die realen Knoten (node_groups)
    oder die Dummy-Knoten (node_groups_dummies) pro Achse entsprechend der Barycenterposition ihrer Nachbarn umsortiert. Der Sweep endet, wenn keine Änderung mehr auftritt oder der threshold an Iterationen erreicht ist. Es kann zu Osszilationen im Sweep kommen, wenn
    z.B. wenn zwei Knoten die gleiche Barycenter Position haben oder in den Sweeps einfach nur ihre Positionen hin- und hertauschen. Dies führt dazu, dass die Schleife nie terminiert. In state_set werden dementsprechend alle erreichten Zustände gehasht und beim Wiederkehren eines zuvor errechneten Zustands kann die Schleife vor einem neuen Durchgang abbrechen.

    Args:
        layout: Aktuelles HivePlotLayout mit Achsenzuordnung und Knotenlisten.
        neighborhood_map: Map von Knoten (real und/oder Dummy, initialisierungsabhängig) auf deren Nachbarn.
        node_axis_map: Map von Knoten auf Achsen in phi.
        threshold: Maximale Anzahl Sweep-Durchläufe, bevor abgebrochen wird.
        real: True, um reale Knoten zu sortieren; False, um Dummy-Knoten zu sortieren.
        layout_expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)
        use_fixed_positions(bool): wird für 3b benötigt, damit fixierte positionen verwendet werden
    """
    # initialiserung von funktionsparameter
    changed = True # 1. abbruchbedingung: keine Änderung nach einem sweep-durchgang mehr festgestellt
    threshold_run = 0 # 2. abbruchbedingung: anzahl durchläufe erreicht
    phi = layout.axis_order
    reversed_phi = list(reversed(phi))
    if layout_expanded and real:
        node_groups = layout.node_groups_expanded
    elif real:
        node_groups = layout.node_groups
    else:
        node_groups = layout.node_groups_dummies
    phi = layout.axis_order
    state_set = set()
    fixed_positions_by_axis = layout.fixed_positions_by_axis or {}

    # abbruchbedingungen
    while threshold_run < threshold and changed:
        # stateauswertung und abbruchbedingung
        state = tuple(tuple(node_groups.get(axis, [])) for axis in phi)
        if state in state_set:
            break
        state_set.add(state)

        # funktionsparameter setzen
        threshold_run += 1
        changed = False

        # cw-weep
        for axis in phi:
            # initialisierung
            bary_axis_order = node_groups.get(axis, [])
            fixed_positions = fixed_positions_by_axis.get(axis, {})
            bary_positions_axis = []

            # berechnung der heuristik
            for i, node in enumerate(bary_axis_order):
                if use_fixed_positions and node in fixed_positions:
                    bary_positions_axis.append(fixed_positions[node])
                else:
                    node_neighbors = neighborhood_map[node]
                    if len(node_neighbors) == 0:
                        bary_positions_axis.append(i / max(1, len(bary_axis_order)))
                    else:
                        bary_positions_axis.append(
                            calculate_barycenter_position(layout, node_neighbors, node_axis_map, layout_expanded)) # barycenterpositionen bestimmen
                        
            # neue ordnung bestimmen und 
            new_order = [node for _, node in sorted(enumerate(bary_axis_order), key=lambda t: (bary_positions_axis[t[0]], t[0]))]
            if node_groups.get(axis, []) != new_order:
                changed = True

            # optimierte achse zurückschreiben
            node_groups[axis] = new_order

        # ccw-sweep, kommentare analog zu cw-sweep
        for axis in reversed_phi:
            bary_axis_order = node_groups.get(axis, [])
            fixed_positions = fixed_positions_by_axis.get(axis, {})
            bary_positions_axis = []

            for i, node in enumerate(bary_axis_order):
                if use_fixed_positions and node in fixed_positions:
                    bary_positions_axis.append(fixed_positions[node])
                else:
                    node_neighbors = neighborhood_map[node]
                    if len(node_neighbors) == 0:
                        bary_positions_axis.append(i / max(1, len(bary_axis_order)))
                    else:
                        bary_positions_axis.append(
                            calculate_barycenter_position(layout, node_neighbors, node_axis_map, layout_expanded))

            new_order = [node for _, node in sorted(enumerate(bary_axis_order), key=lambda t: (bary_positions_axis[t[0]], t[0]))]
            if node_groups.get(axis, []) != new_order:
                changed = True

            node_groups[axis] = new_order

def calculate_barycenter_position(layout: HivePlotLayout, neighbor_group: list[int], node_axis_map, layout_expanded: bool = False) -> float:
    """Berechnet die Barycenterposition eines Knotens über seine ermittelten Nachbarn. Siehe HivePlotLayout.get_proper_neighbors().

    Args:
        layout (HivePlotLayout): das zu berechnende HivePlotLayout
        neighbor_group (list[int]): Liste der Nachbarknoten
        expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)
    Returns:
        float: Barycenterposition
    """
    # funktionsparameter initialisieren
    if layout_expanded:
        real_nodes = layout.node_groups_expanded
    else:
        real_nodes = layout.node_groups
    virtual_nodes = layout.node_groups_dummies

    # divide by zero fallback
    if len(neighbor_group) == 0:
        return 0

    neighbor_sum = 0
    for neighbor in neighbor_group:
        # initialisierung
        node_axis_name = node_axis_map[neighbor]
        real_axis = real_nodes.get(node_axis_name, [])
        virtual_axis = virtual_nodes.get(node_axis_name, [])

        # nenner
        axis_len = len(real_axis) + len(virtual_axis)

        # fallback
        if axis_len == 0:
            continue
        
        # heuristikformel
        if neighbor in real_axis:
            neighbor_sum += real_axis.index(neighbor) / axis_len
        elif neighbor in virtual_axis:
            neighbor_sum += (len(real_axis) + virtual_axis.index(neighbor)) / axis_len

    return neighbor_sum / len(neighbor_group)

def edge_node_cleanup(layout: HivePlotLayout):
    """Nachbereitung der Pipeline, dient als Absicherung, dass Kanten und intra Knoten im Layout korrekt gesetzt sind.
    """
    from ordering import node_to_axis_maps

    fused_edges = [edge for edge in layout.fuse_edges_with_edge_dummies() if edge[0] != edge[1]]
    layout.graph.add_edges_from(fused_edges)
    layout.graph.add_edges_from(fused_edges)
    layout.graph.remove_edges_from(layout.long_edges)
    _, node_axis_map = node_to_axis_maps(layout, layout.fuse_node_groups_with_dummies())
    active_nodes = set()
    for u, v in layout.edges():
        active_nodes.add(u)
        active_nodes.add(v)

    for axis in list(layout.node_groups_dummies):
        layout.node_groups_dummies[axis] = [
            n for n in layout.node_groups_dummies[axis]
            if n in active_nodes
        ]

def barycenter_crossmin_pipeline(layout: HivePlotLayout, logger: logging.Logger, threshold: float = float("inf"), paper_like: bool = True) -> None:
    """Führt die Kreuzungsminimierungs-Pipeline mit der Barycenterheuristik aus (3a/3b).

    Die Pipeline umfasst im paper_like = false:
    1. anfängliches Layout expandieren
    2. Entfernen isolierter Knoten auf den Achsen.
    3. Einfügen von Dummy-Knoten für lange Kanten (Span > 1) und sortieren der inter axis Knoten (Span = 0).
    4. Initialisierung des Sweeps und Updates der Datenstrukturen.
    5. Mehrfache CW/CCW-Sweeps für reale und anschließend virtuelle Knoten, die die Barycenterpositionen ermitteln und die Achsen entsprechend sortieren.
    6. Herstellen der Achsenornung und letztes Update der Datenstrukturen um die Visualisierung starten zu können.

    Die Pipeline umfasst im nicht paper_like = true:
    1. Entfernen isolierter Knoten auf den Achsen.
    2. Einfügen von Dummy-Knoten für lange Kanten (Span > 1) und sortieren der inter axis Knoten (Span = 0).
    3. Initialisierung des Sweeps und Updates der Datenstrukturen.
    4. Mehrfache CW/CCW-Sweeps für reale und anschließend virtuelle Knoten, die die Barycenterpositionen ermitteln und die Achsen entsprechend sortieren.
    5. Barycenter 3b
    6. Herstellen der Achsenornung und letztes Update der Datenstrukturen um die Visualisierung starten zu können.

    Args:
        layout (HivePlotLayout): Das zu optimierende HivePlotLayout.
        threshold(int): Optionaler Abbruchschwellwert für die Anzahl der Sweep-Durchläufe.
        expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)
        paper_like(bool): dient der Unterscheidung zwischen identischer und unterschiedlicher Knotenordnung
    """
    from ordering import node_to_axis_maps
    if paper_like:
        layout_expanded = False

        isolated_nodes = remove_isolated_nodes(layout.graph, layout.node_groups)

        # ---------- Vorverarbeitung ----------
        node_position_map, node_axis_map = node_to_axis_maps(layout, layout.node_groups)
        neighborhood_map = layout.get_proper_neighborhood_map(layout.edges())

        # ---------- Segmentierung ----------
        subdivide_long_edges(layout, node_position_map,node_axis_map, neighborhood_map)

        fused_edge_list = layout.fuse_edges_with_edge_dummies()
        fused_node_list = layout.fuse_node_groups_with_dummies(layout_expanded=layout_expanded)

        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list)
        neighborhood_map = layout.get_proper_neighborhood_map(fused_edge_list, layout_expanded=layout_expanded)

        # ---------- Pipeline 3a ----------
        # reale knoten optimieren
        barycenter_heuristic(
            layout,
            neighborhood_map,
            node_axis_map,
            threshold=threshold,
            real=True,
            layout_expanded=layout_expanded,
        )
        # virtuelle knoten optimieren
        barycenter_heuristic(
            layout,
            neighborhood_map,
            node_axis_map,
            threshold=threshold,
            real=False,
            layout_expanded=layout_expanded,
        )

        finish_structured_axis_orders(layout, isolated_nodes, layout_expanded=layout_expanded)

        # ---------- Vorbereitung Pipeline 3b ----------
        layout.classify_nodes_for_3b()
        layout.freeze_barycenter_positions(layout_expanded=False)

        fused_node_list = layout.fuse_node_groups_with_dummies(layout_expanded=layout_expanded)
        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list)

        # ---------- Expansion ----------
        layout.post_processing_expansion(node_axis_map)
        layout_expanded = True

        # nach expansion alle konkreten achsenordnungen fixieren
        layout.freeze_barycenter_positions(layout_expanded=True)

        fused_edge_list = layout.fuse_edges_with_edge_dummies()
        fused_node_list = layout.fuse_node_groups_with_dummies(layout_expanded=layout_expanded)

        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list)
        neighborhood_map = layout.get_proper_neighborhood_map(fused_edge_list, layout_expanded=layout_expanded)

        # ---------- Pipeline 3b ----------
        # reale knoten optimieren
        barycenter_heuristic(
            layout,
            neighborhood_map,
            node_axis_map,
            threshold=threshold,
            real=True,
            layout_expanded=layout_expanded,
            use_fixed_positions=True)
        
        # virtuelle knoten optimieren
        barycenter_heuristic(
            layout,
            neighborhood_map,
            node_axis_map,
            threshold=threshold,
            real=False,
            layout_expanded=layout_expanded,
            use_fixed_positions=True)

        # ---------- Finish ----------
        finish_structured_axis_orders(layout,isolated_nodes, layout_expanded=layout_expanded)

    else:
        # ---------- Vorverarbeitung ----------
        layout_expanded = False
        isolated_nodes = remove_isolated_nodes(layout.graph, layout.node_groups)

        node_position_map, node_axis_map = node_to_axis_maps(layout, layout.node_groups)
        neighborhood_map = layout.get_proper_neighborhood_map(layout.edges(), layout_expanded=False)

        # ---------- Expansion ----------
        layout.pre_processing_expansion(node_axis_map)
        layout_expanded = True

        # ---------- Zustandsupdate ----------
        fused_node_list = layout.fuse_node_groups_with_dummies(layout_expanded=True)
        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list)
        neighborhood_map = layout.get_proper_neighborhood_map(layout.edges(), layout_expanded=True)

        # ---------- Segmentierung ----------
        subdivide_long_edges(layout, node_position_map, node_axis_map, neighborhood_map)

        # ---------- Zustandsupdate ----------
        fused_edge_list = layout.fuse_edges_with_edge_dummies()
        fused_node_list = layout.fuse_node_groups_with_dummies(layout_expanded=layout_expanded)

        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list)
        neighborhood_map = layout.get_proper_neighborhood_map(fused_edge_list, layout_expanded=layout_expanded)

        # ---------- Optimierung ----------
        # reale knoten optimieren
        barycenter_heuristic(layout, 
            neighborhood_map, 
            node_axis_map, 
            threshold=threshold, 
            real=True, 
            layout_expanded = layout_expanded)
        
        # virtuelle knoten optimieren
        barycenter_heuristic(layout, 
            neighborhood_map, 
            node_axis_map, 
            threshold=threshold, 
            real=False, 
            layout_expanded = layout_expanded)
        
        # ---------- Finish ----------
        finish_structured_axis_orders(layout, isolated_nodes, layout_expanded=layout_expanded)

if __name__ == "__main__":
    pass
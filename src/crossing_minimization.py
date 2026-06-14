# gap handling + barycenter:

# Pipeline grob:

# Initialisierung: subdivide_long_edges()
# 1. CW-Sweep start bei phi[0] ende bei phi[k-1]
# 2. Iteration über phi[i], fest sind nachbarachsen (über ( i-1 mod k) und ( i+1 mod k) ansprechen)
# 2.1 barycenter auf phi[i] berechnen, jede Position jedes knotens, Nachbarn fließen in BC-Formel ein
# 2.2 GAP HANDLING für phi[i]
# 2.3 update phi[i] DANACH GOTO 2.1 mit i+1 oder zu 3. falls i=k-1
# 3. CWC-Sweep start bei k-1 ende bei 0
# -> gleiches Prinzip wie CW sweep bloß in beschriebene Richtung
# ABBRUCH: Treshholdparameter erreicht falls dieser mitgegeben wurde ODER keine Änderung der knotenreihenfolge bei kompletten CW-CCW sweep durchgang

# implementierungsschema/Idee

# Funktionen:
# 1. subdivide_long_edges() -> G.copy() und nicht in-place
# 2. Sweeps: sweep(axes_order, pi, G, g, reverse=False) G -> G.neighbours() + subdivide (Long edges + dummys)
# 3. gap handling
# 5. Pipeline gesamt (nur diese wird ausgeführt und bündelt die einzelnen Bestandteile)
# -> Parameter intuitiv: def barycenter_crossing_min(G, alpha, phi, pi, g=1, threshold=None) | RETURN: PI

from pyvis import node
from src import graphs
from src.cost import node_or_axes_span
from src.ordering import brute_force_ordering, native_order, node_groups, node_to_axis_maps, reordered_node_groups
import networkx as nx
import pickle
# import logging
# logging.basicConfig(
#     level=logging.DEBUG,
#     handlers=[
#         logging.StreamHandler(),          
#         logging.FileHandler("debug.log")
#     ],
#     format="%(asctime)s - %(levelname)s - %(message)s"
# )
# logger = logging.getLogger(__name__)


def subdivide_long_edges(layout: HivePlotLayout, node_position_map: dict[int | str, int], node_axis_map: dict[int | str, int], neighborhood_map: dict[int | str, list[int | str]], expanded: bool = False) -> None:
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
        expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)

    Return:
        None. Die Funktion arbeitet in-place auf dem übergebenen Layout!
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
    
    def clockwise_count(start_pos: int, start_node: int, end_node: int, span: int):
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

    def counter_clockwise_count(start_pos: int, start_node: int, end_node: int, span: int):
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
    
    layout.intra_axis_nodes = {key: [] for key in layout.node_groups}
    k = layout.num_axes
    edges = layout.edges()
    long_edges = layout.long_edges
    dummy_edges = layout.dummy_edge_segments
    dummies = layout.node_groups_dummies
    for axis in layout.axis_order: # initialisiere dummyliste, schreibt explizit in die HivePlotLayout Instanz
        dummies[axis] = []
    # intra_axis_node_set = set()
    intra_candidate_edge_list = layout.intra_axis_edges # alle kandidaten aufnehmen und nach reinen intra axis filtern
    intra_candidate_node_list = [] # alle kandidaten aufnehmen und nach reinen intra axis filtern
    for edge in edges: # 
        start = node_axis_map[edge[0]] # startachse
        end = node_axis_map[edge[1]] # endachse
        start_pos = node_position_map[edge[0]] # startpositioon
        end_pos = node_position_map[edge[1]] # endposition
        span = node_or_axes_span(start_pos, end_pos, k)
        if span > 1: # direkte behandlung von langen kanten (dummy knoten erzeugen), proper ignorieren
            if (start_pos - end_pos) % k > (end_pos - start_pos) % k or (start_pos - end_pos) % k == (end_pos - start_pos) % k: # richtung start -> ende
                clockwise_count(start_pos, edge[0], edge[1], span)
            elif (start_pos - end_pos) % k < (end_pos - start_pos) % k: # richtung ende <- start, counter cw
                counter_clockwise_count(start_pos, edge[0], edge[1], span)
        elif span == 0: # intra axis candidaten sammeln und im anschluss nach komponenten ohne mixed knoten filtern
            intra_candidate_edge_list.append(edge) # sammelt span 0 kanten
            for node in edge:
                if node not in intra_candidate_node_list:
                    intra_candidate_node_list.append(node) # sammelt intra axis knoten
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
        layout.node_groups[axis].remove(node)
    layout.graph.remove_edges_from(intra_candidate_edge_list)

def parse_dummy_name(name: str) -> tuple[int, int, int]:
    """Zerlegt den Namen eines Dummyknotens in seine Bestandteile: Startknoten, Endknoten und Sequenznummer. (siehe make_dummy_name Funktion für Namensschema)

    Args:
        name (str): Der zu zerlegende Dummyknoten

    Returns:
        tuple[int, int, int]: Tupel aus int-Werten: (Startknoten, Endknoten, Sequenznummer)
    """
    parts = name.split("_")
    return int(parts[1]), int(parts[2]), int(parts[3])

def edge_direction(start_pos: int, end_pos: int, k: int) -> int:
    """Ermittelt die Richtung einer Kante in Form der nächsten Achse, die die Kante überquert. Diese spiegelt sowohl die Richtung im Uhrzeigersinn oder gegen den Uhrzeigersinn als auch die Position des ersten Dummyknotens wieder, sollte es sich um eine lange Kante handeln.
    Für Span <=1 wird simpel der Endknoten zurückgegeben. 

    Args:
        start_pos (int): Achsenposition in hpl.node_groups des Startknotens
        end_pos (int): Achsenposition in hpl.node_groups des Endknotens
        k (int): Anzahl der Achsen

    Returns:
        int: Achsenposition in hpl.node_groups in Richtung der langen Kante
    """
    span = node_or_axes_span(start_pos, end_pos, k)
    axe_direction_position = start_pos
    if span > 1:
        if (start_pos - end_pos) % k < (end_pos - start_pos) % k or (start_pos - end_pos) % k == (end_pos - start_pos) % k: # richtung start -> ende, clockwise oder span cw = span ccw
            axe_direction_position = (axe_direction_position + 1) % k
        elif (start_pos - end_pos) % k > (end_pos - start_pos) % k: # richtung ende <- start, counter cw
            axe_direction_position = (axe_direction_position - 1) % k
        return axe_direction_position
    else: # span <= 1
        print(f"Der Span ist kleiner 1. Die Kante endet entweder auf einem Nachbarn oder ist intra-axis.")
        return end_pos

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

def finish_structured_axis_orders(layout: HivePlotLayout, isolated_node_groups: dict[str, list[int]], expanded: bool = False) -> None:
    """Finalisiert die Achsenordnungen nach der Barycenter-Pipeline.

    Die Funktion fügt zunächst intra-axis Knoten und verbleibende Knoten pro Achse zusammen, hängt danach die zuvor entfernten isolierten Knoten wieder an und stellt sicher, dass intra-axis Kanten im Graphen rekonstruiert werden.
    Die engültige Reihenfolge ist auf jeder Achse identisch: reine intra axis Knoten | mixed intra axis Knoten | inter axis Knoten (real) | isolierte Knoten | virtuelle Knoten (dummys). 

    Args:
        layout: Das HivePlotLayout, dessen node_groups und Kanten finalisiert werden.
        isolated_node_groups: Pro Achse die während der Pipeline entfernten isolierten Knoten, die wieder angehängt werden sollen.
    
    """
    def _attach_intra_axis_order():
        """Stellt Reihenfolge in node_groups pro Achse her: reine intra axis Knoten | mixed intra axis Knoten | inter axis Knoten (real)"""
        merged = {key: layout.intra_axis_nodes[key] + layout.node_groups[key] for key in layout.node_groups}
        return merged
    def _attach_isolated_nodes(node_groups: dict[str, list[int]], isolated_node_groups: dict[str, list[int]]) -> None:
        """Fügt die isolierten Knoten wieder in die Knotenlisten auf den Achsen hinzu.

        Args:
            node_groups (dict[str, list[int]]): Die persistente Kontenliste des HivePlotLayouts.
            isolated_node_groups (dict[str, list[int]]): Die isolierten Knoten und ihre Achsenzuordnung.
        """
        for key in node_groups:
            node_groups[key].extend(isolated_node_groups[key])
    def _recover_edges():
        """Fügt die im Subdivide Schritt aus dem Graphen gefilterten reinen intra axis Kanten wieder dem nx.Graphmodell hinzu."""
        layout.graph.add_edges_from(layout.intra_axis_edges)
    
    if expanded:
        _attach_isolated_nodes(layout.node_groups_expanded, isolated_node_groups) # + isolierte Knoten
        layout.node_groups_expanded = layout.fuse_node_groups_with_dummies(expanded=expanded) # + inter axis (virtuell)
    else:
        layout.node_groups = _attach_intra_axis_order() # intra axis + mixed intra axis + inter axis (real)
        _attach_isolated_nodes(layout.node_groups, isolated_node_groups) # + isolierte Knoten
        layout.node_groups = layout.fuse_node_groups_with_dummies() # + inter axis (virtuell)
        _recover_edges()

def _sweep(layout: HivePlotLayout, neighborhood_map: dict[int | str, list[int | str]], node_axis_map: dict[int | str, int], threshold = float("inf"), real: bool = True, expanded: bool = False) -> None:
    """Führt wiederholte Barycenter-Sweeps im und gegen den Uhrzeigersinn über alle Achsen aus. Abhängig vom Parameter real werden entweder die realen Knoten (node_groups)
    oder die Dummy-Knoten (node_groups_dummies) pro Achse entsprechend der Barycenterposition ihrer Nachbarn umsortiert. Der Sweep endet, wenn keine Änderung mehr auftritt oder der threshold an Iterationen erreicht ist. Es kann zu Osszilationen im Sweep kommen, wenn
    z.B. wenn zwei Knoten die gleiche Barycenter Position haben oder in den Sweeps einfach nur ihre Positionen hin- und hertauschen. Dies führt dazu, dass die Schleife nie terminiert. In state_set werden dementsprechend alle erreichten Zustände gehasht und beim Wiederkehren eines zuvor errechneten Zustands kann die Schleife vor einem neuen Durchgang abbrechen.

    Args:
        layout: Aktuelles HivePlotLayout mit Achsenzuordnung und Knotenlisten.
        neighborhood_map: Map von Knoten (real und/oder Dummy, initialisierungsabhängig) auf deren Nachbarn.
        node_axis_map: Map von Knoten auf Achsen in phi.
        threshold: Maximale Anzahl Sweep-Durchläufe, bevor abgebrochen wird.
        real: True, um reale Knoten zu sortieren; False, um Dummy-Knoten zu sortieren.
        expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)

    """
    # initialiserung logik parameter
    changed = True # 1. abbruchbedingung: keine Änderung nach einem sweep-durchgang mehr festgestellt
    threshold_run = 0 # 2. abbruchbedingung: anzahl durchläufe erreicht
    # initialisierung layout parameter
    phi = layout.axis_order
    reversed_phi = list(reversed(phi))
    if expanded:
        node_groups = layout.node_groups_expanded
    else:
        node_groups = layout.node_groups
    dummy_node_groups = layout.node_groups_dummies
    state_set = set() # states sammeln um osszilation von zuständen zu erkennen
    # sweep-logik für reale knoten:
    if real == True:
        while  threshold_run < threshold and changed == True:
            state = tuple(tuple(node_groups[axis]) for axis in phi) # aktueller zustand
            if state in state_set: # falls aktueller zustand schon einmal gesehen
                print("ZUSTAND WIEDERERKANNT")
                break
            state_set.add(state)
            threshold_run += 1
            changed = False
            for axis in phi: # clockwise
                bary_axis_order = node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = neighborhood_map[node]
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors, node_axis_map, expanded=expanded))
                # umsortierung der knotenliste nach positionen
                new_order = [node for position, node in sorted(enumerate(bary_axis_order), key=lambda t: (bary_positions_axis[t[0]], t[0]))] # stabile sortierung, bei gleichen positionen wird die reihenfolge erhalten
                if node_groups[axis] != new_order: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                node_groups[axis] = new_order
            for axis in reversed_phi: # counter clockwise
                bary_axis_order = node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = neighborhood_map[node]
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors, node_axis_map, expanded=expanded))
                # umsortierung der knotenliste nach positionen
                # besser (stable sort mit Tiebreak auf aktuelle Position):
                new_order = [node for position, node in sorted(enumerate(bary_axis_order), key=lambda t: (bary_positions_axis[t[0]], t[0]))] # stabile sortierung, bei gleichen positionen wird die reihenfolge erhalten
                if node_groups[axis] != new_order: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                node_groups[axis] = new_order
    elif real == False:
        while  threshold_run < threshold and changed == True:
            state = tuple(tuple(node_groups[axis]) for axis in phi) # aktueller zustand
            if state in state_set: # falls aktueller zustand schon einmal gesehen
                break
            threshold_run += 1
            changed = False
            for axis in phi: # clockwise
                bary_axis_order = dummy_node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = neighborhood_map[node]
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors, node_axis_map, expanded=expanded))
                # umsortierung der knotenliste nach positionen
                new_order = [node for position, node in sorted(enumerate(bary_axis_order), key=lambda t: (bary_positions_axis[t[0]], t[0]))] # stabile sortierung, bei gleichen positionen wird die reihenfolge erhalten
                if dummy_node_groups[axis] != new_order: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                dummy_node_groups[axis] = new_order
            for axis in reversed_phi: # counter clockwise
                bary_axis_order = dummy_node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = neighborhood_map[node]
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors, node_axis_map, expanded=expanded))
                # umsortierung der knotenliste nach positionen
                new_order = [node for position, node in sorted(enumerate(bary_axis_order), key=lambda t: (bary_positions_axis[t[0]], t[0]))] # stabile sortierung, bei gleichen positionen wird die reihenfolge erhalten
                if dummy_node_groups[axis] != new_order: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                dummy_node_groups[axis] = new_order

def intra_axis_handler(layout: HivePlotLayout) -> None:
    """Bereitet intra-axis Knoten nach der Barycenter-Pipeline auf. Alle intra-axis Kanten werden zu Zusammenhangskomponenten gruppiert und pro Achse sortiert in zwei Kategorien abgelegt: kurze Pfade (Länge 2) und längere Pfade (Länge > 2). Diese Reihenfolge wird in layout.intra_axis_nodes
    gespeichert, um später wieder in die endgültige Achsenordnung integriert werden zu können. Es handelt sich hierbei um eine heuristische Sortierung der reinen intra axis Knoten, um beim Expandieren einer Achse die Knoten nach der Größe ihrer Zusammenhangskomponente zu ordnen.

    Args:
        layout (HivePlotLayout): Das HivePlotLayout mit gefüllten intra_axis_nodes und intra_axis_edges Feldern.
    """
    def reconstructed_intra_axis_graph():
        """Erstellt einen Subgraphen der intra axis Knoten im Networkx Format"""
        G = nx.Graph()
        for key in intra_nodes:
            G.add_nodes_from(intra_nodes[key], subset=key)
        G.add_edges_from(intra_edges)
        return G
    
    def intra_node_to_axis(node: int) -> int:
        """Auf welcher Achse dich der betrachtete inter axis Knoten befindet.

        Args:
            node (int): betrachteter Knoten

        Raises:
            ValueError: Ein isolierter Knoten ist durch den vorherigen Filter gerutscht.

        Returns:
            int: Achsen-ID auf der sich der Knoten befindet
        """
        for key in intra_nodes:
            if node in intra_nodes[key]:
                return key
        raise ValueError(f"Knoten {node} keiner intra-axis-Achse zugeordnet")
    
    intra_nodes = layout.intra_axis_nodes
    intra_edges = layout.intra_axis_edges
    intra_axis_graph = reconstructed_intra_axis_graph()
    sorted_intra_nodes_long = {key: [] for key in intra_nodes} # > 2
    sorted_intra_nodes_short = {key: [] for key in intra_nodes} # = 2
    for component in nx.connected_components(intra_axis_graph):
        path = sorted(component)
        if not path:
            raise ValueError("Leere Zusammenhangskomponente gefunden.")
        axis = intra_node_to_axis(path[0])
        if len(path) > 2: # nicht triviale inter axis pfade und keine doppelung der pfade TODO: robustheitsprüfung zweiter teil!
            sorted_intra_nodes_long[axis].extend(path)
        elif len(path) == 2:
            sorted_intra_nodes_short[axis].extend(path)
        else:
            raise ValueError(f"Bei {path} handelt es sich um einen isolierten Knoten oder etwas Seltsames!!")
    
    layout.intra_axis_nodes = {key: sorted_intra_nodes_short[key] + sorted_intra_nodes_long[key] for key in intra_nodes} # vorarbeit zum finish der achsenordnung ->  triviale intra-axis| cluster intra-axis

def calculate_barycenter_position(layout: HivePlotLayout, neighbor_group: list[int], node_axis_map, expanded: bool = False) -> float:
    """Berechnet die Barycenterposition eines Knotens über seine ermittelten Nachbarn. Siehe HivePlotLayout.get_proper_neighbors().

    Args:
        layout (HivePlotLayout): das zu berechnende HivePlotLayout
        neighbor_group (list[int]): Liste der Nachbarknoten
        expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)
    Returns:
        float: Barycenterposition
    """
    neighbor_sum = 0
    if expanded:
        real_nodes = layout.node_groups_expanded
    else:
        real_nodes = layout.node_groups
    virtual_nodes = layout.node_groups_dummies
    for neighbor in neighbor_group:
        node_axis_name = node_axis_map[neighbor]
        axis_len = len(real_nodes[node_axis_name]) + len(virtual_nodes[node_axis_name])
        if isinstance(neighbor, int):
            neighbor_sum += real_nodes[node_axis_name].index(neighbor)/axis_len # index teuer, ggf. map!
        elif isinstance(neighbor, str):
            neighbor_sum += (len(real_nodes[node_axis_name]) +(virtual_nodes[node_axis_name].index(neighbor)))/axis_len # index teuer, ggf. map!
    position = 1/len(neighbor_group) * neighbor_sum
    return position

def edge_node_cleanup(layout: HivePlotLayout, intra: bool = False):
    """Nachbereitung der Pipeline, dient als Absicherung, dass Kanten und intra Knoten im Layout korrekt gesetzt sind.
    """
    fused_edges = layout.fuse_edges_with_edge_dummies()
    layout.graph.add_edges_from(fused_edges)
    layout.graph.remove_edges_from(layout.long_edges)
    _, node_axis_map = node_to_axis_maps(layout, layout.fuse_node_groups_with_dummies())
    if intra:
        for edge in fused_edges:
            if node_axis_map[edge[0]] == node_axis_map[edge[1]] and edge not in layout.intra_axis_edges:
                layout.intra_axis_edges.append(edge)

def barycenter_crossmin_pipeline(layout: HivePlotLayout, threshold: float = float("inf"), expanded: bool = False) -> None:
    """Führt die Kreuzungsminimierungs-Pipeline mit der Barycenterheuristik aus (3a/3b).

    Die Pipeline umfasst im expandierten Fall:
    1. anfängliches Layout expandieren
    2. Entfernen isolierter Knoten auf den Achsen.
    3. Einfügen von Dummy-Knoten für lange Kanten (Span > 1) und sortieren der inter axis Knoten (Span = 0).
    4. Initialisierung des Sweeps und Updates der Datenstrukturen.
    5. Mehrfache CW/CCW-Sweeps für reale und anschließend virtuelle Knoten, die die Barycenterpositionen ermitteln und die Achsen entsprechend sortieren.
    6. Herstellen der Achsenornung und letztes Update der Datenstrukturen um die Visualisierung starten zu können.

    Die Pipeline umfasst im nicht expandierten Fall:
    1. Entfernen isolierter Knoten auf den Achsen.
    2. Einfügen von Dummy-Knoten für lange Kanten (Span > 1) und sortieren der inter axis Knoten (Span = 0).
    3. Initialisierung des Sweeps und Updates der Datenstrukturen.
    4. Mehrfache CW/CCW-Sweeps für reale und anschließend virtuelle Knoten, die die Barycenterpositionen ermitteln und die Achsen entsprechend sortieren.
    5. Sortierung der reinen intra axis Knoten.
    6. Herstellen der Achsenornung und letztes Update der Datenstrukturen um die Visualisierung starten zu können.

    Args:
        layout (HivePlotLayout): Das zu optimierende HivePlotLayout.
        threshold(int): Optionaler Abbruchschwellwert für die Anzahl der Sweep-Durchläufe.
        expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)
    """
    if expanded:
        # pipeline 3a <<<<<<<<<<<<
        # 1.
        node_position_map, node_axis_map = node_to_axis_maps(layout, layout.node_groups)
        neighborhood_map = layout.get_proper_neighborhood_map(layout.edges()) # initialisieren aus layout.graph
        layout.expand_axes(node_axis_map)
        # 2.
        isolated_nodes = remove_isolated_nodes(layout.graph, layout.node_groups_expanded)
        # 3.
        node_position_map, node_axis_map = node_to_axis_maps(layout, layout.node_groups_expanded) # UPDATE mit n_g_expanded
        neighborhood_map = layout.get_proper_neighborhood_map(layout.edges(), expanded=expanded) # UPDATE
        subdivide_long_edges(layout, node_position_map, node_axis_map, neighborhood_map)
        # 4.
        fused_edge_list = layout.fuse_edges_with_edge_dummies() # dummykanten einbeziehen
        fused_node_list = layout.fuse_node_groups_with_dummies(expanded=expanded) # UPDATE !!!
        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list) # UPDATE !!!
        neighborhood_map = layout.get_proper_neighborhood_map(fused_edge_list, expanded=expanded)
        # 5.
        _sweep(layout, neighborhood_map, node_axis_map, threshold=threshold, real=True, expanded=expanded) # nur real
        _sweep(layout, neighborhood_map, node_axis_map, threshold=threshold, real=False, expanded=expanded) # nur virtuell (dummies)
        # 6.
        finish_structured_axis_orders(layout, isolated_nodes, expanded=expanded)
    else:
        # pipeline 3a <<<<<<<<<<<<
        # 1.
        isolated_nodes = remove_isolated_nodes(layout.graph, layout.node_groups)
        # 2.
        node_position_map, node_axis_map = node_to_axis_maps(layout, layout.node_groups)
        neighborhood_map = layout.get_proper_neighborhood_map(layout.edges()) # initialisieren aus layout.graph
        subdivide_long_edges(layout, node_position_map, node_axis_map, neighborhood_map)
        # 3.
        fused_edge_list = layout.fuse_edges_with_edge_dummies() # dummykanten einbeziehen
        fused_node_list = layout.fuse_node_groups_with_dummies() # UPDATE !!!
        node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list) # UPDATE !!!
        neighborhood_map = layout.get_proper_neighborhood_map(fused_edge_list)
        layout.dummy_edge_segments = layout.fuse_edges_with_edge_dummies()
        # 4.
        _sweep(layout, neighborhood_map, node_axis_map, threshold=threshold, real=True) # nur real
        _sweep(layout, neighborhood_map, node_axis_map, threshold=threshold, real=False) # nur virtuell (dummies)
        #pipeline 3b <<<<<<<<<<<<
        # 5.
        intra_axis_handler(layout)
        # 6.
        finish_structured_axis_orders(layout, isolated_nodes)

if __name__ == "__main__":
    print("##########################################")
    import src.renderer as rr
    from src.hiveplot import HivePlotLayout

    # graph_mode = 0
    # graph_mode = 1
    graph_mode = 3

    #INITIALISIERUNG paperkonform
    G = graphs.sample_graph_selfconstructed_extended(graph_mode)
    nodes = list(G.nodes(data="subset"))
    axes = native_order(nodes)
    ng = node_groups(nodes)
    hpl = HivePlotLayout(
        graph=G,
        num_axes=len(axes),
        axis_order=axes,
        node_groups=ng
    )
    hpl.axis_order = brute_force_ordering(axes, ng, list(G.edges()))
    hpl.node_groups = reordered_node_groups(ng, hpl.axis_order)

    # PIPELINE nicht expandiert
    barycenter_crossmin_pipeline(hpl)
    edge_node_cleanup(hpl)
    rr.hiveplot_renderer("Barycenter_paperkonform", hpl)
    rr.hiveplot_renderer("Barycenter_paperkonform mit intra", hpl, intra=True)

    print("##########################################")
    print("Barycenter_paperkonform")
    print(hpl)
    print(hpl.edges())
    
    node_position_map, node_axis_map = node_to_axis_maps(hpl, hpl.node_groups)
    edge_cleanup(hpl)
    hpl.post_processing_expansion(node_axis_map)
    rr.hiveplot_renderer("Barycenter_paperkonform_expandiert", hpl, expanded=True)
    print("##########################################")
    print("Barycenter_paperkonform_expandiert")
    print(hpl)
    print(hpl.edges())
    # INITIALISIERUNG EXPANDIERT
    G = graphs.sample_graph_selfconstructed_extended(graph_mode)
    nodes = list(G.nodes(data="subset"))
    axes = native_order(nodes)
    ng = node_groups(nodes)
    hpl_two = HivePlotLayout(
        graph=G,
        num_axes=len(axes),
        axis_order=axes,
        node_groups=ng
    )
    hpl_two.axis_order = brute_force_ordering(axes, ng, list(G.edges()))
    hpl_two.node_groups = reordered_node_groups(ng, hpl_two.axis_order)

    barycenter_crossmin_pipeline(hpl_two, expanded=True)
    edge_cleanup(hpl_two)
    rr.hiveplot_renderer("Barycenter_eigen", hpl_two, expanded=True)
    print("##########################################")
    print("Barycenter eigen")
    print(hpl_two)
    print(hpl_two.edges())
    print("##########################################")
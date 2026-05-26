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


def _subdivide_long_edges(layout: HivePlotLayout, node_position_map, node_axis_map) -> None:
    """Funktion dient dem Einfügen von Dummyknoten für lange Kanten (span > 1) auf den Achsen zwischen Start- und Endknoten. Schema: d_[Startknoten]_[Endknoten]_[Sequenznummer]: z.B. d_5_10_2 ist der zweite Dummyknoten auf der zerlegten langen Kante von 5 nach 10. Die lange Kante kann dann folgendermaßen beschrieben werden:
    Startknoten - d_5_10_1 - d_5_10_2 - ... - d_5_10_(span-1) - Endknoten. Die Funktion schreibt direkt in layout.node_groups_dummies.

    Args:
        layout (HivePlotLayout): Das HivePlotLayout-Objekt, das die Informationen über den Graphen, die Achsen und die Knoten enthält. 
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
    
    def is_mixed(node, layout): # check ob ein knoten sowohl intra als auch inter ist
        # axis = node_position_map[node]
        # return any(
        #     node_to_axis(neighbor, layout.node_groups) != axis
        #     for neighbor in layout.graph.neighbors(node)
        # )
        return False
    
    layout.intra_axis_nodes = {key: [] for key in layout.node_groups}
    k = layout.num_axes
    edges = layout.edges()
    long_edges = layout.long_edges
    dummy_edges = layout.dummy_edge_segments
    dummies = layout.node_groups_dummies
    for axis in layout.axis_order: # initialisiere dummyliste, schreibt explizit in die HivePlotLayout Instanz
        dummies[axis] = []
    intra_axis_nodes = set()
    intra_candidate_list = []
    for edge in edges:
        start = node_axis_map[edge[0]] # startachse
        end = node_axis_map[edge[1]] # endachse
        start_pos = node_position_map[edge[0]] # startpositioon
        end_pos = node_position_map[edge[1]] # endposition
        span = node_or_axes_span(start_pos, end_pos, k)
        if span > 1:
            if (start_pos - end_pos) % k > (end_pos - start_pos) % k or (start_pos - end_pos) % k == (end_pos - start_pos) % k: # richtung start -> ende
                clockwise_count(start_pos, edge[0], edge[1], span)
            elif (start_pos - end_pos) % k < (end_pos - start_pos) % k: # richtung ende <- start, counter cw
                counter_clockwise_count(start_pos, edge[0], edge[1], span)
        # elif span == 0:
        #     intra_candidate_list.append(edge) # sammelt span 0 kanten
        # zero_span_subgraph = nx.Graph()
        # zero_span_subgraph.add_edges_from(intra_candidate_list)
        # ignore_set = set()
        # for edge in intra_candidate_list:
        #     if is_mixed(edge[0], layout) or is_mixed(edge[1], layout):
        #         for node in edge:
        #             ignore_set.update(nx.node_connected_component(zero_span_subgraph, node))
        # for edge in intra_candidate_list:
        #     if edge[0] not in ignore_set and edge[1] not in ignore_set:
        #         start = node_axis_map[edge[0]] # startachse
        #         end = node_axis_map[edge[1]]
        #         layout.intra_axis_edges.append(edge)
        #         layout.graph.remove_edge(edge[0], edge[1])
        #         if edge[0] not in layout.intra_axis_nodes[start]: 
        #             layout.intra_axis_nodes[start].append(edge[0]) # start = end (span = 0)
        #             intra_axis_nodes.add(edge[0])
        #         if edge[1] not in layout.intra_axis_nodes[end]: 
        #             layout.intra_axis_nodes[end].append(edge[1]) # start = end (span = 0)
        #             intra_axis_nodes.add(edge[1])
    for axis, nodes in layout.node_groups.items():
        layout.node_groups[axis] = [inter_node for inter_node in nodes if inter_node not in intra_axis_nodes]

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

def _remove_isolated_nodes(graph: nx.Graph, node_groups: dict[int, list[int]]) -> dict[int, list[int]]:
    """Die Funktion ermöglicht das Entfernen aller isolierten Knoten aus der persitenten node_group des HivePlotLayouts.

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

def finish_structured_axis_orders(layout: HivePlotLayout, isolated_node_groups: dict[str, list[int]]) -> None:
    def _attach_intra_axis_order():
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
        layout.graph.add_edges_from(layout.intra_axis_edges)
    layout.node_groups = _attach_intra_axis_order()
    _attach_isolated_nodes(layout.node_groups, isolated_node_groups)
    _recover_edges

def _sweep(layout: HivePlotLayout, neighborhood_map: dict[int, list[int | str]], node_position_map, node_axis_map, fused_list, threshold = float("inf"), real: bool = True) -> None:
    # initialiserung logik parameter
    changed = True # 1. abbruchbedingung: keine Änderung nach einem sweep-durchgang mehr festgestellt
    threshold_run = 0 # 2. abbruchbedingung: anzahl durchläufe erreicht
    # initialisierung layout parameter
    phi = layout.axis_order
    reversed_phi = list(reversed(phi))
    node_groups = layout.node_groups
    dummy_node_groups = layout.node_groups_dummies
    # sweep-logik für reale knoten:
    if real == True:
        while  threshold_run < threshold and changed == True:
            threshold_run += 1
            print(">>>>>>>>>>>>>>>>>>>>>>>>>REAL--------------------------")
            print(f"|REAL RUN: {threshold_run}/{threshold}")
            changed = False
            for axis in phi: # clockwise
                bary_axis_order = node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = neighborhood_map[node]
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors, node_axis_map))
                print(f"|BC ORDER{bary_axis_order}")
                print(f"|BC WERTE{bary_positions_axis}")
                # umsortierung der knotenliste nach positionen
                new_order = [node for position, node in sorted(zip(bary_positions_axis, bary_axis_order), key=lambda t: t[0])]# (position, node), soertierung explizit nach BC-position
                print(f"|Real CW -> VORHER: {node_groups[axis]} | NACHHER: {new_order} | changed = {changed} | new order list? {isinstance(new_order, list)}")
                if node_groups[axis] != new_order: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                node_groups[axis] = new_order
            print("--------------------------CCW---------------------------")
            for axis in reversed_phi: # counter clockwise
                bary_axis_order = node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = neighborhood_map[node]
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors, node_axis_map))
                print(f"|BC ORDER{bary_axis_order}")
                print(f"|BC WERTE{bary_positions_axis}")
                # umsortierung der knotenliste nach positionen
                new_order = [node for position, node in sorted(zip(bary_positions_axis, bary_axis_order), key=lambda t: t[0])]# (position, node), soertierung explizit nach BC-position
                print(f"|Real CCW -> VORHER: {node_groups[axis]} | NACHHER: {new_order} | changed = {changed} | new order list? {isinstance(new_order, list)}")
                if node_groups[axis] != new_order and changed == True: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                node_groups[axis] = new_order
            print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    elif real == False:
        while  threshold_run < threshold and changed == True:
            threshold_run += 1
            print(">>>>>>>>>>>>>>>>>>>>>>>>>VIRTUAL-----------------------")
            print(f"|VIRTUAL RUN: {threshold_run}/{threshold}")
            changed = False
            for axis in phi: # clockwise
                bary_axis_order = dummy_node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = neighborhood_map[node]
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors, node_axis_map))
                print(f"|BC ORDER{bary_axis_order}")
                print(f"|BC WERTE{bary_positions_axis}")
                # umsortierung der knotenliste nach positionen
                new_order = [node for position, node in sorted(zip(bary_positions_axis, bary_axis_order), key=lambda t: t[0])]# (position, node), soertierung explizit nach BC-position
                print(f"|Virtuell CW -> VORHER: {dummy_node_groups[axis]} | NACHHER: {new_order} | changed = {changed} | new order list? {isinstance(new_order, list)}")
                if dummy_node_groups[axis] != new_order: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                dummy_node_groups[axis] = new_order
            print("--------------------------CCW---------------------------")
            for axis in reversed_phi: # counter clockwise
                bary_axis_order = dummy_node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = neighborhood_map[node]
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors, node_axis_map))
                print(f"|BC ORDER{bary_axis_order}")
                print(f"|BC WERTE{bary_positions_axis}")
                # umsortierung der knotenliste nach positionen
                new_order = [node for position, node in sorted(zip(bary_positions_axis, bary_axis_order), key=lambda t: t[0])]# (position, node), soertierung explizit nach BC-position
                print(f"|Virtuell CCW -> VORHER: {dummy_node_groups[axis]} | NACHHER: {new_order} | changed = {changed} | new order list? {isinstance(new_order, list)}")
                if dummy_node_groups[axis] != new_order: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                dummy_node_groups[axis] = new_order
            print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")

def intra_axis_handler(layout: HivePlotLayout) -> None:
    def reconstructed_intra_axis_graph():
        G = nx.Graph()
        for key in intra_nodes:
            G.add_nodes_from(intra_nodes[key], subset=key)
        G.add_edges_from(intra_edges)
        return G
    
    def intra_node_to_axis(node):
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

    

def calculate_barycenter_position(layout: HivePlotLayout, neighbor_group: list[int], node_axis_map) -> float:
    """Berechnet die Barycenterposition eines Knotens über seine ermittelten Nachbarn. Siehe HivePlotLayout.get_proper_neighbors().

    Args:
        layout (HivePlotLayout): das zu berechnende HivePlotLayout
        neighbor_group (list[int]): Liste der Nachbarknoten

    Returns:
        float: Barycenterposition
    """
    neighbor_sum = 0
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

def barycenter_crossmin_pipeline(layout: HivePlotLayout, threshold=float("inf")):
    # pipeline 3a
    # print("11")
    isolated_nodes = _remove_isolated_nodes(layout.graph, layout.node_groups)
    print("1")
    fused_node_list = layout.fuse_node_groups_with_dummies()
    node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list)
    print("2")
    _subdivide_long_edges(layout, node_position_map, node_axis_map)
    print("3")
    fused_edge_list = layout.fuse_edges_with_edge_dummies()
    print("4")
    fused_node_list = layout.fuse_node_groups_with_dummies() # UPDATE !!!
    node_position_map, node_axis_map = node_to_axis_maps(layout, fused_node_list) # UPDATE !!!
    neighborhood_map = layout.get_proper_neighborhood_map(fused_edge_list)
    print("5")
    
    # print(f"layout.node_groups_dummies: {layout.node_groups_dummies}") # debugging
    # fused_nodes = layout.fuse_node_groups_with_dummies()
    layout.dummy_edge_segments = layout.fuse_edges_with_edge_dummies()
    print("6")
    _sweep(layout, neighborhood_map, node_position_map, node_axis_map, fused_node_list, threshold=threshold, real=True) # nur real
    print("7")
    _sweep(layout, neighborhood_map,node_position_map, node_axis_map,  fused_node_list, threshold=threshold, real=False) # nur virtuell (dummies)
    print("8")
    #pipeline 3b
    intra_axis_handler(layout)
    finish_structured_axis_orders(layout, isolated_nodes)
    print("9")
    # print("10")


if __name__ == "__main__":
    print("##########################################")
    printer = 0 # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< PRINTER
    # graph_mode = 0 # standard
    graph_mode = 1 # mit intr
    # graph_mode = 2 # dummy test
    from src.graphs import sample_graph_selfconstructed, sample_graph_multipartite, sample_graph_caveman
    from src.hiveplot import HivePlotLayout
    # # from src.partitioning import louvain_community_detection
    from src.debug_renderer import render_debug
    # # logging.basicConfig(level=logging.DEBUG)
    G = graphs.sample_graph_selfconstructed_extended(graph_mode)
    nodes = list(G.nodes(data="subset"))
    axes = native_order(nodes)
    ng = node_groups(nodes)
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
    barycenter_crossmin_pipeline(hpl, threshold=10)
    # barycenter_crossmin_pipeline(hpl)
    print("Pipeline -> Ende")
    hpl.node_groups = hpl.fuse_node_groups_with_dummies() # ACHTUNG: FÜR RENDERING NÖTIG, FÜR WEITERE PIPELINE-OPERATIONEN NICHT NÖTIG, DA DUMMYS IN SEPARATEN STRUKTUREN GEHALTEN WERDEN
    if printer == 1:
        render_debug(hpl, title="PIPELINE ABGESCHLOSSEN")
    print("Layout NACH OPTIMIERUNG")
    print(hpl)
    print(hpl.edges())
    print("##########################################")
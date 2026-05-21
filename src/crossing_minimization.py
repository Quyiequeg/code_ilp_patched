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

from src import graphs
from src.cost import node_or_axes_span
from src.ordering import brute_force_ordering, native_order, node_groups, node_to_axis, reordered_node_groups
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


def _subdivide_long_edges(layout: HivePlotLayout) -> None:
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
        for _ in range(span - 1): # achsen zwischen start und ende
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
        for _ in range(span - 1): # achsen zwischen start und ende
            current_dummy = make_dummy_name(start_node, end_node, sequence_number)
            axis = layout.axis_order[dummyposition] # position -> achse
            dummies[axis].append(current_dummy) # name unikal pro achse, achsensegmente leicht rekonstruierbar
            dummy_edges.append((previous, current_dummy)) # dummy edge von vorherigem knoten zum aktuellen dummy
            previous = current_dummy
            dummyposition = (dummyposition - 1) % k
            sequence_number += 1
        long_edges.add((start_node, end_node))
        dummy_edges.append((previous, end_node))
    
            
    k = layout.num_axes
    edges = layout.edges()
    long_edges = layout.long_edges
    dummy_edges = layout.dummy_edge_segments
    dummies = layout.node_groups_dummies
    for axis in layout.axis_order: # initialisiere dummyliste, schreibt explizit in die HivePlotLayout Instanz
        dummies[axis] = []
    pos = {axis: i for i, axis in enumerate(layout.axis_order)} # umrechnen von achsen zu positionen
    for edge in edges:
        start = node_to_axis(edge[0], layout.node_groups) # startachse
        end = node_to_axis(edge[1], layout.node_groups) # endachse
        start_pos = pos[start] # startpositioon
        end_pos = pos[end] # endposition
        span = node_or_axes_span(start_pos, end_pos, k)
        if span > 1:
            if (start_pos - end_pos) % k < (end_pos - start_pos) % k or (start_pos - end_pos) % k == (end_pos - start_pos) % k: # richtung start -> ende, clockwise oder span cw = span ccw
                clockwise_count(start_pos, edge[0], edge[1], span)
            elif (start_pos - end_pos) % k > (end_pos - start_pos) % k: # richtung ende <- start, counter cw
                counter_clockwise_count(start_pos, edge[0], edge[1], span)


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

def _remove_isolated_nodes(graph: nx.Graph, node_groups: dict[str, list[int]]) -> dict[str, list[int]]:
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

def _return_isolated_nodes(node_groups: dict[str, list[int]], isolated_node_groups: dict[str, list[int]]) -> None:
    """Fügt die isolierten Knoten wieder in die Knotenlisten auf den Achsen hinzu.

    Args:
        node_groups (dict[str, list[int]]): Die persistente Kontenliste des HivePlotLayouts.
        isolated_node_groups (dict[str, list[int]]): Die isolierten Knoten und ihre Achsenzuordnung.
    """
    for key in node_groups:
        node_groups[key].extend(isolated_node_groups[key])


def _sweep(layout: HivePlotLayout, threshold = float("inf"), real: bool = True) -> None:
    node_groups = layout.node_groups
    phi = layout.axis_order
    changed = True
    threshold_run = 1
    fused_edge_list = layout.fuse_edges_with_edge_dummies()
    dummy_node_groups = layout.node_groups_dummies
    # print(f"INIT: threshold={threshold}")
    if real == True:
        while  threshold_run <= threshold and changed == True: # 1 schleifendurchlauf: cw+ccw sweep mit anschließender abbruchprüfung
            # print(f"RUN {threshold_run}")
            threshold_run += 1
            changed = False
            reversed_phi = list(reversed(phi))
            for i, axis in enumerate(phi): # clockwise sweep
             # print(f"ORDER: {phi}")
                bary_axis_order = node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = layout.get_proper_neighbors(node, fused_edge_list)
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors))
                ziped_list = zip(bary_axis_order, bary_positions_axis) # (node, position)
                sorted_pairs = sorted(ziped_list, key=lambda pair: pair[1]) # nach position aufsteigend sortieren
                new_order = [node for node, _ in sorted_pairs] # neue ordnung der achse ohne dummies

                if node_groups[axis] != new_order: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                # print(f"CW: order vorher {node_groups[axis]} (Achse {axis})")
                node_groups[axis] = new_order
                # print(f"CW: order nachher {node_groups[axis]} (Achse {axis})")
            # print(changed)

            for i, axis in enumerate(reversed_phi): # counterclockwise sweep
                # print(f"ORDER: {reversed_phi}")
                bary_axis_order = node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = layout.get_proper_neighbors(node, fused_edge_list)
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors))
                ziped_list = zip(bary_axis_order, bary_positions_axis) # (node, position)
                sorted_pairs = sorted(ziped_list, key=lambda pair: pair[1]) # nach position aufsteigend sortieren
                new_order = [node for node, _ in sorted_pairs] # neue ordnung der achse ohne dummies
                if node_groups[axis] != new_order: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                # print(f"CCW: order vorher {node_groups[axis]} (Achse {axis})")
                node_groups[axis] = new_order
                # print(f"CCW: order nachher {node_groups[axis]} (Achse {axis})")
            # print(changed)
    elif real == False:
        while  threshold_run <= threshold and changed == True: # 1 schleifendurchlauf: cw+ccw sweep mit anschließender abbruchprüfung
            # print(f"RUN {threshold_run}")
            threshold_run += 1
            changed = False
            reversed_phi = list(reversed(phi))
            for i, axis in enumerate(phi): # clockwise sweep
             # print(f"ORDER: {phi}")
                bary_axis_order = dummy_node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = layout.get_proper_neighbors(node, fused_edge_list)
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors))
                ziped_list = zip(bary_axis_order, bary_positions_axis) # (node, position)
                sorted_pairs = sorted(ziped_list, key=lambda pair: pair[1]) # nach position aufsteigend sortieren
                new_order = [node for node, _ in sorted_pairs] # neue ordnung der achse ohne dummies

                if dummy_node_groups[axis] != new_order: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                # print(f"CW: order vorher {dummy_node_groups[axis]} (Achse {axis})")
                dummy_node_groups[axis] = new_order
                # print(f"CW: order nachher {dummy_node_groups[axis]} (Achse {axis})")
            # print(changed)

            for i, axis in enumerate(reversed_phi): # counterclockwise sweep
                # print(f"ORDER: {reversed_phi}")
                bary_axis_order = dummy_node_groups[axis]
                bary_positions_axis = []
                for node in bary_axis_order:
                    node_neighbors = layout.get_proper_neighbors(node, fused_edge_list)
                    bary_positions_axis.append(calculate_barycenter_position(layout, node_neighbors))
                ziped_list = zip(bary_axis_order, bary_positions_axis) # (node, position)
                sorted_pairs = sorted(ziped_list, key=lambda pair: pair[1]) # nach position aufsteigend sortieren
                new_order = [node for node, _ in sorted_pairs] # neue ordnung der achse ohne dummies
                if dummy_node_groups[axis] != new_order: # sichergehen, dass nur einmal geflaggt wird (reicht aus für abbruch)
                    changed = True
                # print(f"CCW: order vorher {dummy_node_groups[axis]} (Achse {axis})")
                dummy_node_groups[axis] = new_order
                # print(f"CCW: order nachher {dummy_node_groups[axis]} (Achse {axis})")
            # print(changed)  

# def _gap_handling(): VERMUTLICH NICHT NOWENDIG; DA REAL UND VIRTUELL SAUBER GETRENNT UND G=1
#     pass

def calculate_barycenter_position(layout: HivePlotLayout, neighbor_group: list[int]) -> float:
    """Berechnet die Barycenterposition eines Knotens über seine ermittelten Nachbarn. Siehe HivePlotLayout.get_proper_neighbors().

    Args:
        layout (HivePlotLayout): das zu berechnende HivePlotLayout
        neighbor_group (list[int]): Liste der Nachbarknoten

    Returns:
        float: Barycenterposition
    """
    fused_list = layout.fuse_node_groups_with_dummies()
    neighbor_sum = 0
    for neighbor in neighbor_group:
        node_axis_name = node_to_axis(neighbor, fused_list)
        neighbor_sum += fused_list[node_axis_name].index(neighbor)/len(fused_list[node_axis_name])
    position = 1/len(neighbor_group) * neighbor_sum
    return position

def barycenter_crossmin_pipeline(layout: HivePlotLayout, threshold=float("inf")):
    isolated = _remove_isolated_nodes(layout.graph, layout.node_groups)
    _subdivide_long_edges(layout)
    # fused_nodes = layout.fuse_node_groups_with_dummies()
    layout.dummy_edge_segments = layout.fuse_edges_with_edge_dummies()
    _sweep(layout, threshold=threshold, real=True)
    _sweep(layout, threshold=threshold, real=False)
    _return_isolated_nodes(layout.node_groups, isolated)

if __name__ == "__main__":
    print("##########################################")
    from src.graphs import sample_graph_selfconstructed, sample_graph_multipartite, sample_graph_caveman
    from src.hiveplot import HivePlotLayout
    # # from src.partitioning import louvain_community_detection
    from src.debug_renderer import render_debug
    # # logging.basicConfig(level=logging.DEBUG)
    G = graphs.sample_graph_selfconstructed_extended()
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
    # render_debug(hpl, title="ORIGINAL") # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< ORIGINAL
    hpl.axis_order = brute_force_ordering(axes, ng, list(G.edges()))
    hpl.node_groups = reordered_node_groups(ng, hpl.axis_order)
    # render_debug(hpl, title="OHNE PIPELINE - OPTIMIZED") # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< OHNE PIPELINE - OPTIMIZED
    # barycenter_crossmin_pipeline(hpl, threshold=10)
    barycenter_crossmin_pipeline(hpl)
    hpl.node_groups = hpl.fuse_node_groups_with_dummies() # ACHTUNG: FÜR RENDERING NÖTIG, FÜR WEITERE PIPELINE-OPERATIONEN NICHT NÖTIG, DA DUMMYS IN SEPARATEN STRUKTUREN GEHALTEN WERDEN
    # render_debug(hpl, title="PIPELINE ABGESCHLOSSEN") # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< PIPELINE ABGESCHLOSSEN
    print("Layout NACH OPTIMIERUNG")
    print(hpl)
    print(hpl.edges())
    print("##########################################")
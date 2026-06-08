from dataclasses import dataclass, field
from typing import Optional
import networkx as nx


@dataclass
class HivePlotLayout:
    """Zentrale Datenstruktur für ein berechnetes Hive-Plot-Layout.

    Attributes:
        graph (nx.Graph): ein Simple Graph den man nach der Verarbeitung der geparsten DBLP Daten erhält: V = Autoren, E = Coautorenschaft zu 
        num_axes (int): k = Anzahl Achsen
        axis_order (list[int]): phi: siehe native_order Funktion in ordering.py
        node_groups (dict[int, list[int]]): alpha: siehe node_groups Funktion in ordering.py
        node_groups_dummies (dict[int, list[int]]): Achsen mit Dummyknoten
        # dummy_edge_segments (dict[tuple[int,int], list[tuple[int, int]]]): key: Kantentupel (u,v) value: Liste von Kantensegmenten die u und v über Dummyknoten verbinden
        node_order (dict[int, list[int]]): pi_i pro Achse gebündelt
        node_order_plus (dict[int, list[int]]): pi_i^+
        node_order_minus (dict[int, list[int]]): pi_i^-
        crossings (Optional[int]): Kreuzungszahl Standardmodell
        crossings_extended (Optional[int]): Kreuzungszahl erweitertes Modell
    """
    # ursprünglicher graph und notwendige erweiterungen für die pipeline
    graph: nx.Graph
    num_axes: int
    axis_order: list[int]
    node_groups: dict[int, list[int]]

    # notwendig für Pipeline Schritt 3: lange Kanten segmentieren
    node_groups_dummies: dict[int, list[int]] = field(default_factory=dict)
    dummy_edge_segments: list[tuple[int, int]] = field(default_factory=list)
    long_edges: set[tuple[int, int]] = field(default_factory=set)
    intra_axis_nodes: dict[int, list[int]] = field(default_factory=dict)
    intra_axis_edges: list[tuple[int, int]] = field(default_factory=list)

    # knotenordnung auf achsen, wobei pi_i = p_i^+ = p_i^-
    node_order: dict[int, list[int]] = field(default_factory=dict)

    # unabhängige Kopien für pi+ und pi-, da diese sich im erweiterten Modell unterscheiden können
    node_groups_expanded:  dict[int, list[int | str]] = field(default_factory=dict)
    edges_expanded: list[tuple[int | str, int | str]] = field(default_factory=list)

    # ergebnisse zu evaluationszwecken !prüfen
    crossings: Optional[int] = None
    crossings_extended: Optional[int] = None

    def __str__(self):
        """Besser lesbarere Darstellung der HivePlotLayout-Instanz bei Test und debugging.

        Returns:
            str: Zeilenweise Ausgabe der Parameter und Felder.
        """
        lines = [
            f"HivePlotLayout:",
            f"  Graph: {self.graph}",
            f"  Number of Axes: {self.num_axes}",
            f"  Axis Order (phi): {self.axis_order}",
            f"  Node Groups (alpha): {self.node_groups}",
            f"  Node Groups with Dummies: {self.node_groups_dummies}",
            f"  Dummy Edge Segments: {self.dummy_edge_segments}",
            f"  Intra-Axis Nodes: {self.intra_axis_nodes}",
            f"  Intra-Axis Edges: {self.intra_axis_edges}",
            f"  Long Edges: {self.long_edges}",
            f"  Node Order (pi_i): {self.node_order}",
            f"  node_groups_expanded: {self.node_groups_expanded}",
            f"  edges_expanded: {self.edges_expanded}",
            f"  Crossings (standard): {self.crossings}",
            f"  Crossings (erweitert): {self.crossings_extended}"
        ]
        return "\n".join(lines)

    def edges(self) -> list[tuple]:
        """Gibt die Kantenliste des Graphen zurück. Notwendig, weil mit dem Networkx Edgeview nicht direkt gearbeitet werden kann.

        Returns:
            list[tuple]: Liste der Kanten als Tupel (u, v)
        """
        return list(self.graph.edges())

    def updated_nodes(self, fused_node_groups) -> list[int]:
        """Gibt die Knotenliste des Graphen zurück. Notwendig, weil die Knoten sich ändern und je nach Pipelineschritt die Knoten geupdated werden müssen.

        Args:
            fused_node_groups (dict[int, list[int | str]]): AchsenID: Knotenliste (real und virtuell)
        Returns:
            list[int]: Liste der realen und virtuellen Knoten
        """
        updated_node_list = []
        for key in fused_node_groups:
            for node in fused_node_groups[key]:
                updated_node_list.append(node)
        return updated_node_list

    def nodes_on_axis(self, axis: int, include_dummies: bool = False) -> list[int]:
        """Gibt die Knoten einer bestimmten Achse zurück.

        Args:
            axis (int): Die Achse, für die die Knoten zurückgegeben werden sollen
            include_dummies (bool): false (default) Rückgabe ohne dummies, true mit dummies

        Returns:
            list[int]: Liste der Knoten auf der angegebenen Achse
        """
        if include_dummies:
            return self.fuse_node_groups_with_dummies().get(axis, [])
        else:
            return self.node_groups.get(axis, [])
    
    def fuse_node_groups_with_dummies(self, expanded: bool = False) -> dict[int, list[int]]:
        """Erzeugt ein dict mit Achsen als Schlüssel und der vereinigten Menge aus Knoten und Dummyknoten pro Achse als Wert. Zuerst die realen dann die virtuellen Knoten.
        Args:
            expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)
        Returns:
            dict[int, list[int]]: Vereinigung der Knoten und Dummyknoten pro Achse.
        """
        fused_groups = {}
        for axis in self.axis_order:
            if expanded:
                original_nodes = self.node_groups_expanded.get(axis, [])
                dummy_nodes = self.node_groups_dummies.get(axis, [])
                fused_groups[axis] = list(original_nodes) + list(dummy_nodes)
            else:
                original_nodes = self.node_groups.get(axis, [])
                dummy_nodes = self.node_groups_dummies.get(axis, [])
                fused_groups[axis] = list(original_nodes) + list(dummy_nodes)
        return fused_groups

    def fuse_edges_with_edge_dummies(self, expanded: bool = False) -> list[tuple[int, int]]:
        """Erzeugt eine Liste die alle kurzen Kanten und Dummykanten vereinigt zurückgibt.

        Returns:
            list[tuple[int, int]]: Vereinigung aus Kanten und Dummykanten
        """
        direct_edges = [e for e in self.edges() if e not in self.long_edges]
        fused_edges = direct_edges + self.dummy_edge_segments
        return fused_edges
    
    def get_proper_neighborhood_map(self, fused_edge_list: list[tuple[int | str, int | str]], expanded: bool = False) -> dict[int | str: list[int | str]]:
        """Die Funktion ermittelt eine Liste, die jeden Knoten (sowohl real als auch virtuell) auf eine Liste seiner Nachbarn mappt.

        Args:
            fused_edge_list: list[tuple[int | str, int | str]]: Liste der realen und virtuellen Kantentupel
            expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)
        Returns:
            dict[int | str: list[int | str]]: KnotenID: Nachbarliste
        """
        neighbor_map = {}
        fused_node_groups = self.fuse_node_groups_with_dummies(expanded)
        node_list = self.updated_nodes(fused_node_groups)
        for node in node_list:
            neighbor_map[node] = set()
        for edge in fused_edge_list:
            neighbor_map[edge[0]].add(edge[1])
            neighbor_map[edge[1]].add(edge[0])
        return neighbor_map


    def expand_axes(self, node_axis_map) -> None:
        edge_axis_map = {edge: (node_axis_map[edge[0]], node_axis_map[edge[1]]) for edge in self.edges()} # initialisiere kanten zu achsen map
        expandable_axes_map = {}
        inter_expandables = {}
        node_groups_expanded = self.node_groups_expanded
        node_groups = self.node_groups
        # print(f"edge axis:{edge_axis_map}")
        for edge in edge_axis_map: # key = knotenpaar, filter nach intra axis kanten
            edge_positions = edge_axis_map[edge]
            if edge_positions[0] == edge_positions[1]:
                 expandable_axes_map.setdefault(edge_positions[0], []).append(edge) # check ob key vorhandenen + append
        print(f"Expandable axes:{expandable_axes_map}")
        for edge in edge_axis_map: # erst möglich nach dem filtern der einen intra kanten
            edge_positions = edge_axis_map[edge]
            if edge_positions[0] == edge_positions[1]:
                pass
            elif edge_positions[0] in expandable_axes_map:
                inter_expandables.setdefault(edge_positions[0], []).append(edge) # check ob key vorhandenen + append
            elif edge_positions[1] in expandable_axes_map:
                inter_expandables.setdefault(edge_positions[1], []).append(edge) # check ob key vorhandenen + append
        print(f"Inter-expandables:{inter_expandables}")
        for key in node_groups:
            if key not in expandable_axes_map:
                node_groups_expanded[key] = node_groups[key].copy()
            elif key in expandable_axes_map:
                node_groups_expanded[key] = node_groups[key].copy() # pi^- links
                node_groups_expanded[-key] = [-node for node in node_groups[key]] # pi^- rechts
        print(f"node_groups_expanded:{node_groups_expanded}")
        self.axis_order = list(node_groups_expanded.keys())
        self.num_axes = len(self.axis_order)
        axis_position_map = {}
        for i, axis in enumerate(self.axis_order): # achsenid: position in phi
            axis_position_map[axis] = i
        print(f"axis_position_map:{axis_position_map}")
        # die mit expandierten achsen verbundenen kanten aus dem hiveplotlayout entfernen und in korrektem format wieder hineinschreiben
        for axis in expandable_axes_map:
            self.graph.remove_edges_from(expandable_axes_map[axis])
            new_intra_edges = []
            for edge in expandable_axes_map[axis]: # expandierte achse und ihre intra knoten als
                new_intra_edges.append((-edge[0], edge[1]))
                new_intra_edges.append((edge[0], -edge[1]))
            self.graph.add_edges_from(new_intra_edges)
        for axis in inter_expandables:
            self.graph.remove_edges_from(inter_expandables[axis])
            new_inter_edges = []
            for edge in inter_expandables[axis]:
                k = self.num_axes
                axis_u = edge_axis_map[edge][0]
                axis_v = edge_axis_map[edge][1]
                pos_axis_u = axis_position_map.get(axis_u, axis_position_map.get((axis_u, 0))) # beide fälle müssen abgedeckt sein: achse ist int und achse ist expandiert und tupel
                pos_axis_v = axis_position_map.get(axis_v, axis_position_map.get((axis_v, 0)))
                span_uv = (pos_axis_u - pos_axis_v) % k
                span_vu = (pos_axis_v - pos_axis_u) % k
                if axis_u in expandable_axes_map and axis_v in expandable_axes_map: # ziel- und startachse expandiert
                    if span_uv <= span_vu: # v -> u + bei gleichstand immer links
                        new_inter_edges.append((edge[0], -edge[1]))
                    elif span_vu < span_uv: # u auf expandierter achse und u -> v
                        new_inter_edges.append((-edge[0], edge[1]))
                else: # ziel- oder startkante expandiert
                    if axis_u == axis:
                        if span_uv <= span_vu: # u auf expandierter achse und v -> u + bei gleichstand immer links
                            new_inter_edges.append((edge[0], edge[1]))
                        elif span_vu < span_uv: # u auf expandierter achse und u -> v
                            new_inter_edges.append((-edge[0], edge[1]))
                    elif axis_v == axis:
                        if span_vu <= span_uv: # v auf expandierter achse und u -> v
                            new_inter_edges.append((edge[0], edge[1]))
                        elif span_uv < span_vu: # v auf expandierter achse und v -> u
                            new_inter_edges.append((edge[0], -edge[1]))
            self.graph.add_edges_from(new_inter_edges)
        # self.graph neue knoten auf expandierten achsen wieder einem neuen subset zuordnen
        for axis, nodes in self.node_groups_expanded.items():
            for node in nodes:
                if node not in self.graph.nodes: # negative knotenids auf expandierten achsen behandeln
                    self.graph.add_node(node)
                self.graph.nodes[node]['subset'] = axis
        
    def post_processing_expansion(self, node_axis_map, dummy_copy: list[tuple[int | str, int | str]] = None) -> None:
        from src.crossing_minimization import parse_dummy_name
        if dummy_copy is None:
            dummy_edges = self.dummy_edge_segments
        else:
            dummy_edges = dummy_copy
        edge_axis_map = {edge: (node_axis_map[edge[0]], node_axis_map[edge[1]]) for edge in self.edges()} # initialisiere kanten zu achsen map
        intra_expandables = {}
        inter_expandables = {}
        node_groups_expanded = self.node_groups_expanded
        node_groups = self.node_groups
        # print(f"edge axis:{edge_axis_map}")
        for edge in edge_axis_map: # key = knotenpaar, filter nach intra axis kanten
            edge_positions = edge_axis_map[edge]
            if edge_positions[0] == edge_positions[1]:
                intra_expandables.setdefault(edge_positions[0], []).append(edge) # check ob key vorhandenen + append
        # print(f"Intra-expandables:{intra_expandables}")
        for edge in edge_axis_map: # erst möglich nach dem filtern der einen intra kanten
            edge_positions = edge_axis_map[edge]
            if edge_positions[0] == edge_positions[1]:
                pass
            elif edge_positions[0] in intra_expandables:
                inter_expandables.setdefault(edge_positions[0], []).append(edge) # check ob key vorhandenen + append
            elif edge_positions[1] in intra_expandables:
                inter_expandables.setdefault(edge_positions[1], []).append(edge) # check ob key vorhandenen + append
        print(f"Inter-expandables:{inter_expandables}")
        for axis in node_groups:
            if axis not in intra_expandables:
                node_groups_expanded[axis] = node_groups[axis].copy()
            elif axis in intra_expandables:
                node_groups_expanded[axis] = node_groups[axis].copy() # linke achsenkopie
                node_groups_expanded[-axis] = [] # rechte achsenkopie
                for node in node_groups[axis]:
                    if isinstance(node, int): # realer knoten
                        node_groups_expanded[-axis].append(-node)
                    elif isinstance(node, str): # virtueller knoten
                        dummy_node = parse_dummy_name(node)
                        node_groups_expanded[-axis].append(f"d_{dummy_node[0]}_{dummy_node[1]}_{dummy_node[2]+1}") # dummy signatur behalten und sequenznummer um eins erhöhen
                        dummy_edges.append((node, f"d_{dummy_node[0]}_{dummy_node[1]}_{dummy_node[2]+1}")) # kante zwischen expandierten dummyknoten neu erstellen
        # print(f"node_groups_expanded:{node_groups_expanded}")
        # update hpl phi & k
        
        print(self.axis_order)
        print(self.num_axes)
        # achsen und knotenexpansion abgeschlossen, folgend kantenexpansion
        axis_position_map = {}
        for i, axis in enumerate(self.axis_order): # achsenid: position in phi
            axis_position_map[axis] = i
        # print(f"axis_position_map:{axis_position_map}")
        # intra axis kanten aus dem hiveplotlayout entfernen und in expandierter wieder hineinschreiben
        for axis in intra_expandables:
            self.graph.remove_edges_from(intra_expandables[axis])
            new_intra_edges = []
            for edge in intra_expandables[axis]: # expandierte achse und ihre intra knoten
                new_intra_edges.append((-edge[0], edge[1]))
                new_intra_edges.append((edge[0], -edge[1]))
            self.graph.add_edges_from(new_intra_edges)
        print(f"EDGES:{self.edges()}") # expandierte achsen + reine intra axis kanten
        # print(f"DUMMY EDGES:{dummy_edges}") # dummy segmente + expandiert
        new_inter_edges = []
        for axis in inter_expandables:
            self.graph.remove_edges_from(inter_expandables[axis])
            for edge in inter_expandables[axis]:
                if edge_axis_map[edge][0] in inter_expandables and edge_axis_map[edge][1] in inter_expandables: # beide knoten auf expandierter achse
                    first_node = edge[0]
                    first_edge_position = axis_position_map[edge_axis_map[edge][0]]
                    second_node = edge[1]
                    second_edge_position = axis_position_map[edge_axis_map[edge][1]]
                    if first_edge_position - 1 == second_edge_position or first_edge_position - 1 < 0: # erster knoten rechts
                        if isinstance(second_node, int):
                            new_inter_edges.append((-second_node, first_node)) 
                        elif isinstance(second_node, str):
                            dummy_node = parse_dummy_name(second_node)
                            dummy_node_incremented = f"d_{dummy_node[0]}_{dummy_node[1]}_{dummy_node[2]+1}"
                            new_inter_edges.append((dummy_node_incremented, first_node))
                    elif first_edge_position + 1 == second_edge_position or first_edge_position + 1 == self.num_axes: # zweiter knoten rechts
                        if isinstance(first_node, int):
                            new_inter_edges.append((-first_node, second_node))
                        elif isinstance(first_node, str):
                            dummy_node = parse_dummy_name(first_node)
                            dummy_node_incremented = f"d_{dummy_node[0]}_{dummy_node[1]}_{dummy_node[2]+1}"
                            new_inter_edges.append((dummy_node_incremented, second_node))
                elif edge_axis_map[edge][0] in inter_expandables and edge_axis_map[edge][1] not in inter_expandables: # erster knoten auf expandierter achse = startknoten
                    start_node = edge[0]
                    start_position = axis_position_map[edge_axis_map[edge][0]] # achsen position in phi von startknoten achse
                    end_node = edge[1]
                    end_position = axis_position_map[edge_axis_map[edge][1]] # achsen position in phi von endknoten achse
                elif edge_axis_map[edge][0] not in inter_expandables and edge_axis_map[edge][1] in inter_expandables: # zweiter knoten auf expandierter achse = startknoten
                    start_node = edge[1]
                    start_position = axis_position_map[edge_axis_map[edge][1]]
                    end_node = edge[0]
                    end_position = axis_position_map[edge_axis_map[edge][0]]
                # CHECK: beides expandierte achsen?
                if start_position - 1 == end_position or start_position - 1 < 0 : # endknoten liegt links der expandierten achse oder letzte achse der ordnung
                    new_inter_edges.append(edge) # kann einfach übernommen werden
                elif start_position + 1 == end_position or start_position + 1 == self.num_axes: # endknoten liegt rechts der expandierten achse  oder ist erste achse der ordnung
                    if isinstance(start_node, int):
                        new_inter_edges.append((-start_node, end_node)) 
                    elif isinstance(start_node, str):
                        dummy_node = parse_dummy_name(start_node)
                        dummy_node_incremented = f"d_{dummy_node[0]}_{dummy_node[1]}_{dummy_node[2]+1}"
                        new_inter_edges.append((dummy_node_incremented, end_node))
        self.graph.add_edges_from(new_inter_edges)
        self.axis_order = list(node_groups_expanded.keys())
        self.num_axes = len(self.axis_order)
                


        ############################################
        # inter kanten aufspalten, dummy kanten spalten
        # for axis in node_groups: # nodegroups ist basis für node_groups_expanded
        #     if intra_axis_nodes[axis]: # kante hat intra axis knoten
        #         node_groups_expanded[axis] = node_groups[axis].copy() # linke achsenkopie
        #         node_groups_expanded[-axis] = [] # rechte achsenkopie
        #         for node in node_groups[axis]:
        #             if isinstance(node, int): # realer knoten
        #                 node_groups_expanded[-axis].append(-node)
        #             elif isinstance(node, str): # virtueller knoten
        #                 dummy_node = parse_dummy_name(node)
        #                 node_groups_expanded[-axis].append(f"d_{dummy_node[0]}_{dummy_node[1]}_{dummy_node[2]+1}") # dummy signatur behalten und sequenznummer um eins erhöhen
        #     else:
        #         node_groups_expanded[axis] = node_groups[axis].copy()
        # self.axis_order = list(node_groups_expanded.keys())
        # # kanten expandieren
                        
                        





            




    
if __name__ == "__main__":
    from src.graphs import sample_graph_multipartite, sample_graph_selfconstructed_extended
    from src.ordering import native_order, node_groups, node_to_axis_maps, brute_force_ordering, reordered_node_groups
    from src.debug_renderer import render_debug
    graph_mode = 3
    G = sample_graph_selfconstructed_extended(graph_mode)
    nodes = list(G.nodes(data="subset"))
    axes = [0, 1, 5, 4, 2, 3]
    # ng = node_groups(nodes)
    ng = {0: [1, 2, 0, 'd_4_11_1', 'd_5_11_1'], 1: [3, 4, 5, 'd_0_24_1'], 5: [19, 20, 21, 22, 24, 23, 25, 27, 28, 26, 'd_5_18_1'], 4: [14, 16, 15, 13, 17, 18], 2: [7, 6, 8, 'd_9_16_1'], 3: [9, 10, 11, 12, 'd_1_7_1', 'd_2_8_1']}
    # print("Layout ORIGINAL")
    hpl = HivePlotLayout(
        graph=G,
        num_axes=len(axes),
        axis_order=axes,
        node_groups=ng,
        dummy_edge_segments=[(0, 'd_0_24_1'), ('d_0_24_1', 24), (1, 'd_1_7_1'), ('d_1_7_1', 7), (2, 'd_2_8_1'), ('d_2_8_1', 8), (4, 'd_4_11_1'), ('d_4_11_1', 11), (5, 'd_5_11_1'), ('d_5_11_1', 11), (5, 'd_5_18_1'), ('d_5_18_1', 18), (9, 'd_9_16_1'), ('d_9_16_1', 16)]
    )
    # hpl.axis_order = brute_force_ordering(axes, ng, list(G.edges()))
    # hpl.node_groups = reordered_node_groups(ng, hpl.axis_order)
    # isolated_nodes = cm.remove_isolated_nodes(layout.graph, layout.node_groups)
    node_position_map, node_axis_map = node_to_axis_maps(hpl, hpl.node_groups)
    # hpl.expand_axes(node_axis_map)
    
    hpl.post_processing_expansion(node_axis_map)
    render_debug(hpl, title="Post-processing-test")
    # print(hpl)
    # print(hpl.edges())
    # print(hpl.graph.nodes)
    print("##########################################")
    print("##########################################")
    # print("##########################################")
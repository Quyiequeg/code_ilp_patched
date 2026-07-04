from dataclasses import dataclass, field
from typing import Optional
import networkx as nx
import copy

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
        crossings (Optional[int]): Kreuzungszahl Standardmodell
        crossings_extended (Optional[int]): Kreuzungszahl erweitertes Modell
    """
    # ursprünglicher graph und notwendige erweiterungen für die pipeline
    graph: nx.Graph
    num_axes: int
    axis_order: list[int]
    node_groups: dict[int, list[int | str]]

    # notwendig für Pipeline Schritt 3: lange Kanten segmentieren
    node_groups_dummies: dict[int, list[str]] = field(default_factory=dict)
    dummy_edge_segments: list[tuple[int | str, int| str]] = field(default_factory=list)
    long_edges: set[tuple[int, int]] = field(default_factory=set)
    intra_axis_nodes: dict[int, list[int]] = field(default_factory=dict)
    intra_axis_edges: list[tuple[int, int]] = field(default_factory=list)

    # knotenordnung auf achsen, wobei pi_i = p_i^+ = p_i^-
    # node_order: dict[int, list[int]] = field(default_factory=dict)

    node_groups_expanded:  dict[int, list[int | str]] = field(default_factory=dict)
    edges_expanded: list[tuple[int | str, int | str]] = field(default_factory=list)

    id_to_name: dict[int, str] = field(default_factory=dict)
    name_to_id: dict[str, int] = field(default_factory=dict)
    # ergebnisse zu evaluationszwecken !prüfen
    crossings: Optional[int] = None
    crossings_expanded: Optional[int] = None
    mix_nodes_by_axis: dict[int, list[int | str]] = field(default_factory=dict)
    strict_intra_nodes_by_axis: dict[int, list[int | str]] = field(default_factory=dict)
    fixed_inter_axis_delta: dict | None = None
    fixed_positions_by_axis: dict | None = None
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
            f"  node_groups_expanded: {self.node_groups_expanded}",
            f"  edges_expanded: {self.edges_expanded}",
            f"  Crossings (standard): {self.crossings}",
            f"  Crossings (erweitert): {self.crossings_expanded}"
            f"  fixed_delta: {self.fixed_inter_axis_delta}"
        ]
        return "\n".join(lines)
    
    def copy(self):
        "Gibt eine Deepcopy des Hiveplotlayouts zurück."
        return copy.deepcopy(self)

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
    
    def fuse_node_groups_with_dummies(self, layout_expanded:bool = False) -> dict[int, list[int | str]]:
        """Erzeugt ein dict mit Achsen als Schlüssel und der vereinigten Menge aus Knoten und Dummyknoten pro Achse als Wert. Zuerst die realen dann die virtuellen Knoten.
        Args:
            expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)
        Returns:
            dict[int, list[int]]: Vereinigung der Knoten und Dummyknoten pro Achse.
        """
        fused_groups = {}
        for axis in self.axis_order:
            if layout_expanded:
                original_nodes = self.node_groups_expanded.get(axis, [])
                dummy_nodes = self.node_groups_dummies.get(axis, [])
                fused_groups[axis] = list(original_nodes) + list(dummy_nodes)
            else:
                original_nodes = self.node_groups.get(axis, [])
                dummy_nodes = self.node_groups_dummies.get(axis, [])
                fused_groups[axis] = list(original_nodes) + list(dummy_nodes)
        return fused_groups

    def fuse_edges_with_edge_dummies(self,  layout_expanded:bool = False) -> list[tuple[int, int]]:
        """Erzeugt eine Liste die alle kurzen Kanten und Dummykanten vereinigt zurückgibt.

        Returns:
            list[tuple[int, int]]: Vereinigung aus Kanten und Dummykanten
        """
        direct_edges = [edge for edge in self.edges() if edge not in self.long_edges]
        fused_edges = direct_edges + self.dummy_edge_segments
        return fused_edges
    
    def get_proper_neighborhood_map(self, fused_edge_list: list[tuple[int | str, int | str]],  layout_expanded:bool = False) -> dict[int | str: list[int | str]]:
        """Die Funktion ermittelt eine Liste, die jeden Knoten (sowohl real als auch virtuell) auf eine Liste seiner Nachbarn mappt.

        Args:
            fused_edge_list: list[tuple[int | str, int | str]]: Liste der realen und virtuellen Kantentupel
            expanded(bool): dient der Unterscheidung, ob in der Pipeline mit expandierten Achsen gerechnet wird oder nicht, Default = False (nicht expandierter Fall)
        Returns:
            dict[int | str: list[int | str]]: KnotenID: Nachbarliste
        """
        neighbor_map = {}
        fused_node_groups = self.fuse_node_groups_with_dummies(layout_expanded)
        node_list = self.updated_nodes(fused_node_groups)
        for node in node_list:
            neighbor_map[node] = set()
        for edge in fused_edge_list:
            neighbor_map[edge[0]].add(edge[1])
            neighbor_map[edge[1]].add(edge[0])
        return neighbor_map

    def pre_processing_expansion(self, node_axis_map: dict[int | str, int]) -> None:
        """Die Funktion dient der Umsetzung unterschiedlicher Knotenordnungen auf expandierten Achsen. Die Funktion ist ausschließlich zum pre-processing des Eingabegraphen bevor etwaige Berechnungen der Pipeline durchgeführt werden gedacht. Dazu wird die Achse i zu den Achsen mit KnotenIDs i und -i expandiert.  Die intra-axis Kanten werden symmetrisch zwischen den Achsenkopien gezeichnet.
        Folgende Schritte werden durchgeführt:
        1. Initialisieren der Map intra_expandables mit Key AchsenID einer Kante und ihrer intra-axis Kanten (Achse wird nur aufgenommen, wenn es intra-axis Kanten gibt)
        2. Initialisieren der Map inter_expandables mit allen Kanten die genau einen Start oder Enknoten auf der expandierten Achse haben
        3. Initielisieren der node_groups_expanded mit Keys ursprüngliche AchsenIDs und expandierte AchsenIDs und ihre in node_groups enthaltenen Knotenlisten (expandierte Achse -i bekommt alle Knoten von i zugeordnet, jedoch werden die KnotenIDs negativ gesetzt)
        4. Update des Hiveplotlayouts mit neuer Achsenordnung und -anzahl
        5. Initialisieren einer axis_position_map mit Key AchsenID und Value ist Position der Achse in der neuen Achsenordnung
        6. Behandlung der intra-axis Kanten
            a. Entfernen der intra-axis Kanten aus dem Hiveplotlayout
            b. Erstellen der neuen intra-axis Kanten zwischen den expandierten Achsen (Kante (u,v) auf Achse i wird symmetrisch gespiegelt zu den Kanten (-u, v) und (u, -v))
            c. Einpflegen der neuen intra-axis Kanten in die Networkx Graphenstruktur des Hiveplotlayouts
        7. Behandlung der inter-axis Kanten
            a. Entfernen der inter-axis Kanten aus dem Hiveplotlayout
            b. Erstellen der neuen inter-axis Kanten:
                I: Ziel- und Startknoten der Kante auf expandierter Achse: betrachte Kanten i/j mit Knoten u/v wenn i vor j in der Achsenordnung, Kante (u, v) zu (-u, v) andernfalls zu (u, -v) [i -> -i -> j -> -j]
                II: Ziel- oder Startknoten der Kante auf expandierter Achse: betrachte Kanten i/j mit Knoten u/v (i expandiert), falls i vor j in der Achsenordnung (u,v) zu (-u, v), andernfalls Kante übernehmen [j -> i -> -i]
            c. Einpflegen der neuen inter-axis Kanten in die Networkx Graphenstruktur des Hiveplotlayouts
        8. Einpflegen und Zuordnung zu Subsets der neuen Knoten in der Networkx Graphenstruktur des Hiveplotlayouts

        Args:
            node_axis_map (dict[int  |  str, int]): Knoten-ID: Achsen-ID
        """
        edge_axis_map = {edge: (node_axis_map[edge[0]], node_axis_map[edge[1]]) for edge in self.edges()} # initialisiere kanten zu achsen map
        intra_expandables = {}
        inter_expandables = {}
        node_groups_expanded = self.node_groups_expanded
        node_groups = self.node_groups
        for edge in edge_axis_map: # key = knotenpaar, filter nach intra axis kanten
            edge_positions = edge_axis_map[edge]
            if edge_positions[0] == edge_positions[1]:
                 intra_expandables.setdefault(edge_positions[0], []).append(edge) # check ob key vorhandenen + append
        for edge in edge_axis_map: # erst möglich nach dem filtern der einen intra kanten
            edge_positions = edge_axis_map[edge]
            if edge_positions[0] == edge_positions[1]:
                pass
            elif edge_positions[0] in intra_expandables:
                inter_expandables.setdefault(edge_positions[0], []).append(edge) # check ob key vorhandenen + append
            elif edge_positions[1] in intra_expandables:
                inter_expandables.setdefault(edge_positions[1], []).append(edge) # check ob key vorhandenen + append
        for key in node_groups:
            if key not in intra_expandables:
                node_groups_expanded[key] = node_groups[key].copy()
            elif key in intra_expandables:
                node_groups_expanded[key] = node_groups[key].copy() # pi^- links
                node_groups_expanded[-key] = [-node for node in node_groups[key]] # pi^- rechts
        self.axis_order = list(node_groups_expanded.keys())
        self.num_axes = len(self.axis_order)
        axis_position_map = {}
        for i, axis in enumerate(self.axis_order): # achsenid: position in phi
            axis_position_map[axis] = i
        # die mit expandierten achsen verbundenen kanten aus dem hiveplotlayout entfernen und in korrektem format wieder hineinschreiben
        for axis in intra_expandables:
            self.graph.remove_edges_from(intra_expandables[axis])
            new_intra_edges = []
            for edge in intra_expandables[axis]: # expandierte achse und ihre intra knoten als
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
                dist_left_u_v = (pos_axis_u - pos_axis_v) % k
                dist_left_v_u = (pos_axis_v - pos_axis_u) % k
                if axis_u in intra_expandables and axis_v in intra_expandables: # ziel- und startachse expandiert
                    if dist_left_u_v <= dist_left_v_u: # v -> u + bei gleichstand immer links
                        new_inter_edges.append((edge[0], -edge[1]))
                    elif dist_left_v_u < dist_left_u_v: # u auf expandierter achse und u -> v
                        new_inter_edges.append((-edge[0], edge[1]))
                elif axis_u == axis:
                    if dist_left_u_v <= dist_left_v_u: # u auf expandierter achse und v -> u + bei gleichstand immer links
                        new_inter_edges.append((edge[0], edge[1]))
                    elif dist_left_v_u < dist_left_u_v: # u auf expandierter achse und u -> v
                        new_inter_edges.append((-edge[0], edge[1]))
                elif axis_v == axis:
                    if dist_left_v_u <= dist_left_u_v: # v auf expandierter achse und u -> v
                        new_inter_edges.append((edge[0], edge[1]))
                    elif dist_left_u_v < dist_left_v_u: # v auf expandierter achse und v -> u
                        new_inter_edges.append((edge[0], -edge[1]))
            self.graph.add_edges_from(new_inter_edges)
        # self.graph neue knoten auf expandierten achsen wieder einem neuen subset zuordnen
        for axis, nodes in self.node_groups_expanded.items():
            for node in nodes:
                if node not in self.graph.nodes: # negative knotenids auf expandierten achsen behandeln
                    self.graph.add_node(node)
                self.graph.nodes[node]['subset'] = axis
        
    def post_processing_expansion(self, node_axis_map: dict[int | str, int], dummy_copy: list[tuple[int | str, int | str]] = None) -> None:
        """Die Funktion dient dem post-processing des Eingabegraphen nach der Pipeline, sodass bei diesem die Achsen expandiert werden. Dazu wird die Achse i (> 0) zu den Achsen mit KnotenIDs i und -i expandiert.  Die intra-axis Kanten werden symmetrisch zwischen den Achsenkopien gezeichnet.
        Folgende Schritte werden durchgeführt:
        1. Initialiseren der Dummysegmente, diese werden in der Funktion mutiert
        2. Initialisieren der Map intra_expandables mit Key AchsenID einer Kante und ihrer intra-axis Kanten (Achse wird nur aufgenommen, wenn es intra-axis Kanten gibt)
        3. Initialisieren der Map inter_expandables mit allen Kanten die genau einen Start oder Enknoten auf der expandierten Achse haben
        4. Initielisieren der node_groups_expanded mit Keys ursprüngliche AchsenIDs und expandierte AchsenIDs und ihre in node_groups enthaltenen Knotenlisten (expandierte Achse -i bekommt alle Knoten von i zugeordnet, jedoch werden die KnotenIDs negativ gesetzt, für virtuelle Knoten wird die neue Sequenznummer ermittelt und die neue Kante zwischen den virtuellen Knoten direkt in das Netwworkx Graphmodell hinzugefügt)
        5. Update des Hiveplotlayouts mit neuer Achsenordnung und -anzahl und Update der edge_axis_map
        6. Initialisieren einer axis_position_map mit Key AchsenID und Value Position der Achse in der neuen Achsenordnung
        7. Behandlung der intra-axis Kanten
            a. Entfernen der intra-axis Kanten aus dem Hiveplotlayout
            b. Erstellen der neuen intra-axis Kanten zwischen den expandierten Achsen (Kante (u,v) auf Achse i wird symmetrisch gespiegelt zu den Kanten (-u, v) und (u, -v))
            c. Einpflegen der neuen intra-axis Kanten in die Networkx Graphenstruktur des Hiveplotlayouts
        8. Behandlung der inter-axis Kanten
            a. Entfernen der inter-axis Kanten aus dem Hiveplotlayout und den Dummykantensegmenten
            b. Erstellen der neuen inter-axis Kanten, Fallbehandlung:
                I: Sonderfall: sowohl u als auch v auf expandierten achsen
                    i.) v muss aktualisiert werden
                        <1> v ist real und muss negiert werden
                        <2> v ist dummy und muss aktualisiert werden
                    ii.) u muss aktualisiert werden
                        <1> u ist real und muss negiert werden
                        <2> u ist dummy und muss aktualisiert werden
                II: u auf expandierter achse, v auf nicht expandierter achse
                    i.) u ist real und muss negiert werden
                    ii.) u ist dummy und muss aktualisiert werden
                III: v auf expandierter achse, u auf nicht expandierter achse
                    i.) v ist real und muss negiert werden
                    ii.) v ist dummy und muss aktualisiert werden
            c. Einpflegen der neuen inter-axis Kanten in die Networkx Graphenstruktur des Hiveplotlayouts
        9. alle neuen Knoten in hiveplot.graph.nodes speichern und subset zuordnen

        Args:
            node_axis_map (dict[int  |  str, int]): Knoten-ID: Achsen-ID
            dummy_copy (list[tuple[int  |  str, int  |  str]], optional): eine Aktuelle Kopie der Dummysegmente, Default ist None
        """
        from crossing_minimization import parse_dummy_name
        from ordering import node_to_axis_maps

        if dummy_copy is None:
            dummy_edges = self.dummy_edge_segments
        else:
            dummy_edges = dummy_copy

        node_groups_expanded = self.node_groups_expanded
        node_groups = self.node_groups

        edge_axis_map = {
            edge: (node_axis_map[edge[0]], node_axis_map[edge[1]])
            for edge in self.edges()
        }

        intra_expandables = {}
        inter_expandables = {}

        for edge, (axis_u, axis_v) in edge_axis_map.items():
            if axis_u == axis_v:
                intra_expandables.setdefault(axis_u, []).append(edge)

        for edge in self.intra_axis_edges:
            axis_u = node_axis_map[edge[0]]
            axis_v = node_axis_map[edge[1]]
            if axis_u == axis_v:
                intra_expandables.setdefault(axis_u, []).append(edge)

        for edge, (axis_u, axis_v) in edge_axis_map.items():
            if axis_u == axis_v:
                continue
            if axis_u in intra_expandables:
                inter_expandables.setdefault(axis_u, []).append(edge)
            if axis_v in intra_expandables:
                inter_expandables.setdefault(axis_v, []).append(edge)

        for axis in node_groups:
            node_groups_expanded[axis] = node_groups[axis].copy()

            if axis in intra_expandables:
                node_groups_expanded[-axis] = []

                for node in node_groups[axis]:
                    if isinstance(node, int):
                        mirrored = -node
                    else:
                        u, v, seq = parse_dummy_name(node)
                        mirrored = f"d_{u}_{v}_{-seq}"

                    if mirrored not in node_groups_expanded[-axis]:
                        node_groups_expanded[-axis].append(mirrored)

                    if mirrored not in self.graph:
                        self.graph.add_node(mirrored)

                    if isinstance(node, str):
                        self.graph.add_edge(node, mirrored)
                        if (node, mirrored) not in dummy_edges:
                            dummy_edges.append((node, mirrored))

        self.axis_order = list(node_groups_expanded.keys())
        self.num_axes = len(self.axis_order)

        node_groups_for_axis_map = {
            axis: list(nodes)
            for axis, nodes in node_groups_expanded.items()
        }

        for axis, dummies in self.node_groups_dummies.items():
            node_groups_for_axis_map.setdefault(axis, [])
            for dummy in dummies:
                if dummy not in node_groups_for_axis_map[axis]:
                    node_groups_for_axis_map[axis].append(dummy)

        _, node_to_axis_map_updated = node_to_axis_maps(self, node_groups_for_axis_map)

        def mirror_endpoint(node):
            if isinstance(node, int):
                return -node

            u, v, seq = parse_dummy_name(node)
            mirrored = f"d_{u}_{v}_{-seq}"

            axis = node_to_axis_map_updated[node]
            mirror_axis = -axis

            self.node_groups_dummies.setdefault(mirror_axis, [])
            if mirrored not in self.node_groups_dummies[mirror_axis]:
                self.node_groups_dummies[mirror_axis].append(mirrored)

            node_groups_for_axis_map.setdefault(mirror_axis, [])
            if mirrored not in node_groups_for_axis_map[mirror_axis]:
                node_groups_for_axis_map[mirror_axis].append(mirrored)

            node_to_axis_map_updated[mirrored] = mirror_axis

            if mirrored not in self.graph:
                self.graph.add_node(mirrored)

            # interne verbindung zwischen dummy und dummy spiegel
            if not self.graph.has_edge(node, mirrored):
                self.graph.add_edge(node, mirrored)

            if (node, mirrored) not in dummy_edges and (mirrored, node) not in dummy_edges:
                dummy_edges.append((node, mirrored))

            return mirrored

        edge_axis_map = {
            edge: (node_to_axis_map_updated[edge[0]], node_to_axis_map_updated[edge[1]])
            for edge in self.edges()
        }

        axis_position_map = {
            axis: i
            for i, axis in enumerate(self.axis_order)
        }

        def remove_dummy_segment(edge):
            if edge in self.dummy_edge_segments:
                self.dummy_edge_segments.remove(edge)
            elif (edge[1], edge[0]) in self.dummy_edge_segments:
                self.dummy_edge_segments.remove((edge[1], edge[0]))

        for axis, edges in intra_expandables.items():
            self.graph.remove_edges_from(edges)

            new_intra_edges = []
            for u, v in edges:
                new_intra_edges.append((mirror_endpoint(u), v))
                new_intra_edges.append((u, mirror_endpoint(v)))

            self.graph.add_edges_from(new_intra_edges)

        for axis, edges in inter_expandables.items():
            self.graph.remove_edges_from(edges)

            new_inter_edges = []

            for edge in edges:
                axis_u, axis_v = edge_axis_map[edge]

                pos_u = axis_position_map[axis_u]
                pos_v = axis_position_map[axis_v]
                k = self.num_axes

                dist_left_u_v = (pos_u - pos_v) % k
                dist_left_v_u = (pos_v - pos_u) % k

                u, v = edge
                new_u, new_v = u, v

                if axis_u in intra_expandables and axis_v in intra_expandables:
                    if dist_left_u_v <= dist_left_v_u:
                        # u bleibt auf Originalachse, v geht auf Kopie
                        new_v = mirror_endpoint(v)
                    else:
                        # v bleibt auf Originalachse, u geht auf Kopie
                        new_u = mirror_endpoint(u)

                elif axis_u == axis:
                    if dist_left_u_v > dist_left_v_u:
                        new_u = mirror_endpoint(u)

                elif axis_v == axis:
                    if dist_left_v_u > dist_left_u_v:
                        new_v = mirror_endpoint(v)

                new_edge = (new_u, new_v)
                new_inter_edges.append(new_edge)
                remove_dummy_segment(edge)

            self.graph.add_edges_from(new_inter_edges)

        for axis, nodes in self.node_groups_expanded.items():
            for node in nodes:
                if node not in self.graph.nodes:
                    self.graph.add_node(node)
                self.graph.nodes[node]["subset"] = axis
    def prepare_for_rendering(self) -> None:
        """Funktion entfernt alle intra-axis Kanten aus self.edges() und schreibt sie nach self.intra_axis_edges. Notwendig, weil die Rendererlogik sonst falsche 
        Kanten zeichnet. Wird für das zeichnen im nicht expandierten Fall benötigt, da sonst intra-axis Kanten eingezeichnet werden, was zu Fehlern in der Darstellung führt. 
        """
        # ><
        node_axis_map = {}
        groups = self.node_groups_expanded if self.node_groups_expanded else self.fuse_node_groups_with_dummies()
        for axis, nodes in groups.items():
            for node in nodes:
                node_axis_map[node] = axis
        
        intra_edges = [edge for edge in self.edges()
                if edge[0] in node_axis_map 
                and edge[1] in node_axis_map
                and node_axis_map[edge[0]] == node_axis_map[edge[1]]]
        
        self.graph.remove_edges_from(intra_edges)
        for edge in intra_edges:
            if edge not in self.intra_axis_edges:
                self.intra_axis_edges.append(edge)
        
    def count_crossings(self: HivePlotLayout,  layout_expanded:bool = False) -> int:
        """X"""
        if layout_expanded:
            node_groups = self.node_groups_expanded
        else:
            node_groups = self.node_groups
        hpl_copy = self.copy()
        for edge in self.intra_axis_edges:
            if edge in self.graph.edges() and not layout_expanded:
                hpl_copy.graph.remove_edge(edge[0], edge[1])
        
        if layout_expanded:
            neighbor_map = self.get_proper_neighborhood_map(self.edges(), layout_expanded)
        else:
            hpl_copy.graph.add_edges_from(self.dummy_edge_segments)
            neighbor_map = self.get_proper_neighborhood_map(hpl_copy.edges(), layout_expanded)
        node_positions_pi = {} # knoten -> position in pi
        node_axis_map = {} 
        for axis in node_groups: 
            for i, node in enumerate(node_groups[axis]):
                node_positions_pi[node] = i
                node_axis_map[node] = axis
        crossings = 0
        k = len(self.axis_order)
        for step in range(k): # betrachte achsen paarweise
            axis_i = self.axis_order[step]
            axis_j = self.axis_order[(step + 1) % k]
            order_i = node_groups.get(axis_i, [])
            for idx_u, u in enumerate(order_i): # betrachte knoten paarweise
                for v in order_i[idx_u + 1:]:
                    for s in neighbor_map.get(u, []):
                        for t in neighbor_map.get(v, []):
                            if (node_axis_map.get(s) == axis_j and node_axis_map.get(t) == axis_j and node_positions_pi[t] < node_positions_pi[s]):
                                crossings += 1
        return crossings
    
    def classify_nodes_for_3b(self) -> None:
        """Klassifiziert die Knoten für den zweiten Optimierungsschritt (3b).

        mixed_nodes_by_axis:
            Alle Knoten, deren relative Ordnung bereits in 3a bestimmt wurde
            (mixed + inter-axis).

        strict_intra_nodes_by_axis:
            Alle reinen intra-axis Knoten, deren Reihenfolge erst in 3b
            optimiert werden soll.
        """

        self.mixed_nodes_by_axis = {}
        self.strict_intra_nodes_by_axis = {}

        for axis in self.node_groups:

            self.mixed_nodes_by_axis[axis] = []
            self.strict_intra_nodes_by_axis[axis] = []

            for node in self.node_groups[axis]:

                if node in self.intra_axis_nodes.get(axis, []):
                    self.strict_intra_nodes_by_axis[axis].append(node)
                else:
                    self.mixed_nodes_by_axis[axis].append(node)
    
    def freeze_inter_axis_delta(self):
        """X"""
        from ip_model import delta_mapping

        groups_copy = {}

        for axis in self.node_groups:
            groups_copy[axis] = []

            for node in self.node_groups[axis]:
                groups_copy[axis].append(node)

        full_delta = delta_mapping(groups_copy)
        partial_delta = {}

        for key in full_delta:
            u = key[0]
            v = key[1]
            axis = key[2]

            u_is_fixed = False
            v_is_fixed = False

            if axis in self.mixed_nodes_by_axis:
                for fixed_node in self.mixed_nodes_by_axis[axis]:
                    if u == fixed_node:
                        u_is_fixed = True
                    if v == fixed_node:
                        v_is_fixed = True

            if u_is_fixed and v_is_fixed:
                partial_delta[key] = full_delta[key]

        self.fixed_inter_axis_delta = partial_delta

    def freeze_barycenter_positions(self, layout_expanded=False):
        """X"""
        self.fixed_positions_by_axis = {}

        if layout_expanded:
            node_groups = self.node_groups_expanded
        else:
            node_groups = self.node_groups

        for axis, nodes in node_groups.items():
            self.fixed_positions_by_axis[axis] = {
                node : pos
                for pos, node in enumerate(nodes)
            }

if __name__ == "__main__":
   pass
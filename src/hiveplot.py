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
    node_order_plus:  dict[int, list[int]] = field(default_factory=dict) # +
    node_order_minus: dict[int, list[int]] = field(default_factory=dict) # -

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
            f"  Node Order Plus (pi_i^+): {self.node_order_plus}",
            f"  Node Order Minus (pi_i^-): {self.node_order_minus}",
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
    
    def fuse_node_groups_with_dummies(self) -> dict[int, list[int]]:
        """Erzeugt ein dict mit Achsen als Schlüssel und der vereinigten Menge aus Knoten und Dummyknoten pro Achse als Wert. Zuerst die realen dann die virtuellen Knoten.

        Returns:
            dict[int, list[int]]: Vereinigung der Knoten und Dummyknoten pro Achse.
        """
        fused_groups = {}
        for axis in self.axis_order:
            original_nodes = self.node_groups.get(axis, [])
            dummy_nodes = self.node_groups_dummies.get(axis, [])
            fused_groups[axis] = list(original_nodes) + list(dummy_nodes)
        return fused_groups

    def fuse_edges_with_edge_dummies(self) -> list[tuple[int, int]]:
        """Erzeugt eine Liste die alle kurzen Kanten und Dummykanten vereinigt zurückgibt.

        Returns:
            list[tuple[int, int]]: Vereinigung aus Kanten und Dummykanten
        """
        direct_edges = [e for e in self.edges() if e not in self.long_edges]
        fused_edges = direct_edges + self.dummy_edge_segments
        return fused_edges
    
    def get_proper_neighborhood_map(self, fused_edge_list: list[tuple[int | str, int | str]]) -> dict[int | str: list[int | str]]:
        """Die Funktion ermittelt eine Liste, die jeden Knoten (sowohl real als auch virtuell) auf eine Liste seiner Nachbarn mappt.

        Args:
            fused_edge_list: list[tuple[int | str, int | str]]: Liste der realen und virtuellen Kantentupel
        Returns:
            dict[int | str: list[int | str]]: KnotenID: Nachbarliste
        """
        neighbor_map = {}
        fused_node_groups = self.fuse_node_groups_with_dummies()
        node_list = self.updated_nodes(fused_node_groups)
        for node in node_list:
            neighbor_map[node] = set()
        for edge in fused_edge_list:
            neighbor_map[edge[0]].add(edge[1])
            neighbor_map[edge[1]].add(edge[0])
        return neighbor_map
        #     if edge[0] == node:
        #         neighbors_set.add(edge[1])
        #     elif edge[1] == node:
        #         neighbors_set.add(edge[0])
        #     neighbor_list_int = []
        #     neighbor_list_string = []
        #     for neighbor in neighbors_set:
        #         if isinstance(neighbor, int):
        #             neighbor_list_int.append(neighbor)
        #         elif isinstance(neighbor, str):
        #             neighbor_list_string.append(neighbor)
        #     neighbor_list_int.sort()
        #     neighbor_list_string.sort()
        #     neighbors_set = neighbor_list_int + neighbor_list_string
        #     neighbor_map[node] = neighbors_set
        # return neighbor_map

if __name__ == "__main__":
    from src.graphs import sample_graph_multipartite
    from src.ordering import native_order, node_groups

    G = sample_graph_multipartite()
    nodes = list(G.nodes(data="subset"))
    phi = native_order(nodes)
    grps = node_groups(nodes)

    hpl = HivePlotLayout(
        graph=G,
        num_axes=len(phi),
        axis_order=phi,
        node_groups=grps
    )
    print("##########################################")
    print(hpl)
    print("##########################################")
    print("Achsen:", hpl.axis_order)
    print("Knoten auf Achse 0:", hpl.nodes_on_axis(0))
    print("##########################################")
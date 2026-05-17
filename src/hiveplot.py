from dataclasses import dataclass, field
from typing import Optional
import networkx as nx


@dataclass
class HivePlotLayout:
    """Zentrale Datenstruktur für ein berechnetes Hive-Plot-Layout.

    Attributes:
        graph (nx.Graph): der zugrundeliegende Graph G
        num_axes (int): k = Anzahl Achsen
        axis_order (list[int]): phi: siehe cyclic_ordering Funktion in ordering.py
        node_groups (dict[int, list[int]]): alpha: siehe node_groups Funktion in ordering.py
        node_order (dict[int, list[int]]): pi_i pro Achse gebündelt
        node_order_plus (dict[int, list[int]]): pi_i^+
        node_order_minus (dict[int, list[int]]): pi_i^-
        crossings (Optional[int]): Kreuzungszahl Standardmodell
        crossings_extended (Optional[int]): Kreuzungszahl erweitertes Modell
    """
    # ursprünglicher graph und notwendige erweiterungen für die pipeline
    graph: nx.Graph # der zugrundeliegende Graph G
    num_axes: int # k = Anzahl Achsen
    axis_order: list[int] # phi
    node_groups: dict[int, list[int]] # alpha

    # knotenordnung auf achsen, wobei pi_i = p_i^+ = p_i^-
    node_order: dict[int, list[int]] = field(default_factory=dict) # pi_i pro Achse gebündelt

    # unabhängige Kopien für pi+ und pi-, da diese sich im erweiterten Modell unterscheiden können
    node_order_plus:  dict[int, list[int]] = field(default_factory=dict) # +
    node_order_minus: dict[int, list[int]] = field(default_factory=dict) # -

    # ergebnisse zu evaluationszwecken !prüfen
    crossings: Optional[int] = None           # kreuzungszahl standardmodell
    crossings_extended: Optional[int] = None  # kreuzungszahl erweitertes modell

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
            f"  Node Order (pi_i): {self.node_order}",
            f"  Node Order Plus (pi_i^+): {self.node_order_plus}",
            f"  Node Order Minus (pi_i^-): {self.node_order_minus}",
            f"  Crossings (standard): {self.crossings}",
            f"  Crossings (erweitert): {self.crossings_extended}"
        ]
        return "\n".join(lines)

    def edges(self) -> list[tuple]:
        """Gibt die Kantenliste des Graphen zurück.

        Returns:
            list[tuple]: Liste der Kanten als Tupel (u, v)
        """
        return list(self.graph.edges())

    def axes(self) -> list[int]:
        """Gibt die geordneten Achsen zurück (= axis_order).

        Returns:
            list[int]: Geordnete Liste der Achsen
        """
        return self.axis_order

    def nodes_on_axis(self, axis: int) -> list[int]:
        """Gibt die Knoten einer bestimmten Achse zurück.

        Args:
            axis (int): Die Achse, für die die Knoten zurückgegeben werden sollen

        Returns:
            list[int]: Liste der Knoten auf der angegebenen Achse
        """
        return self.node_groups.get(axis, [])


if __name__ == "__main__":
    from src.graphs import sample_graph_multipartite
    from src.ordering import cyclic_ordering, node_groups

    G = sample_graph_multipartite()
    nodes = list(G.nodes(data="subset"))
    phi = cyclic_ordering(nodes)
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
    print("Achsen:", hpl.axes())
    print("Knoten auf Achse 0:", hpl.nodes_on_axis(0))
    print("##########################################")
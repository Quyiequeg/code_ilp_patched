"""debug_renderer.py – Visuelle Debug-Hilfe für die Hiveplot-Pipeline.

Verwendung in beliebigen Modulen:

    from debug_renderer import render_debug

    render_debug(layout, title="nach subdivide", highlight_nodes=[...])

Die Funktion zeigt standardmäßig den Hiveplot-Achsen-Plot.
Mit dem Flag just_edges=True können nur die Kanten aus dem Graphen gezeichnet werden.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np

from hiveplot import HivePlotLayout


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def render_debug(
    layout: HivePlotLayout,
    title: str = "Debug",
    highlight_nodes: list | None = None,
    highlight_edges: list[tuple] | None = None,
    save_path: str | None = None,
    just_edges: bool = False,
) -> None:
    """Rendert einen Hiveplot-Plot für das angegebene Layout.

    Args:
        layout: HivePlotLayout-Instanz.
        title: Titel des Plots.
        highlight_nodes: Liste von Knoten, die hervorgehoben werden sollen.
        highlight_edges: Liste von Kanten, die hervorgehoben werden sollen.
        save_path: Optionaler Pfad zum Speichern der Grafik.
        just_edges: Wenn True, werden nur die Kanten aus layout.graph gezeichnet
                    (keine dummy_edge_segments oder intra_axis_edges).
    """
    fig, ax = plt.subplots(1, 1, figsize=(7, 6))
    fig.suptitle(title, fontsize=13, fontweight="bold")

    _draw_hive(ax, layout, title, highlight_nodes, highlight_edges, just_edges)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=120, bbox_inches="tight")
        print(f"  [debug_renderer] Gespeichert: {save_path}")

    plt.show()


_AXIS_COLORS = [
    "#4f98a3", "#e07b39", "#6daa45", "#a86fdf",
    "#dd6974", "#d19900", "#006494", "#964219",
]


def _node_color_spring(
    node,
    layout: HivePlotLayout,
    highlight_nodes: list | None,
) -> str:
    if highlight_nodes and node in highlight_nodes:
        return "#e03c3c"
    groups = layout.node_groups_expanded if layout.node_groups_expanded else layout.node_groups
    if groups:
        for axis_id, nodes in groups.items():
            if node in nodes:
                return _AXIS_COLORS[abs(axis_id) % len(_AXIS_COLORS)]
    return "#4f98a3"


def _draw_spring(
    ax,
    layout: HivePlotLayout,
    title: str,
    highlight_nodes: list | None,
    highlight_edges: list[tuple] | None,
) -> None:
    G = layout.graph
    pos = nx.spring_layout(G, seed=42)

    groups = layout.node_groups_expanded if layout.node_groups_expanded else layout.node_groups

    node_colors = [
        _node_color_spring(n, layout, highlight_nodes)
        for n in G.nodes()
    ]

    edge_set = set()
    if highlight_edges:
        for u, v in highlight_edges:
            edge_set.add((u, v))
            edge_set.add((v, u))

    edge_colors = [
        "#e03c3c" if (u, v) in edge_set or (v, u) in edge_set else "#aaaaaa"
        for u, v in G.edges()
    ]

    nx.draw_networkx(
        G, pos=pos, ax=ax,
        node_color=node_colors,
        edge_color=edge_colors,
        node_size=420,
        font_size=7,
        font_color="white",
        width=1.5,
    )

    if layout.node_groups:
        patches = [
            mpatches.Patch(
                color=_AXIS_COLORS[abs(i) % len(_AXIS_COLORS)],
                label=f"Achse {i}"
            )
            for i in sorted(groups.keys())
        ]
        if highlight_nodes:
            patches.append(mpatches.Patch(color="#e03c3c", label="highlight"))
        ax.legend(handles=patches, fontsize=7, loc="upper left")

    ax.set_title(f"{title} – Spring Layout", fontsize=10)
    ax.axis("off")


def _draw_hive(
    ax,
    layout: HivePlotLayout,
    title: str,
    highlight_nodes: list | None,
    highlight_edges: list[tuple] | None,
    just_edges: bool = False,
) -> None:
    """Zeichnet den Hiveplot-Achsen-Plot.

    Jede Achse aus axis_order wird als Strahl dargestellt.
    Knoten aus node_groups (oder node_groups_expanded) werden auf ihrer Achse platziert.
    Kanten werden als gebogene Verbindungen gezeichnet.

    Args:
        ax: matplotlib Axes-Objekt.
        layout: Das aktuelle HivePlotLayout.
        title: Subplot-Titel.
        highlight_nodes: Hervorgehobene Knoten.
        highlight_edges: Hervorgehobene Kanten.
        just_edges: Wenn True, nur Kanten aus G.edges() zeichnen.
    """
    G = layout.graph
    k = len(layout.axis_order)
    if k == 0:
        ax.set_title("Kein axis_order vorhanden", fontsize=10)
        return

    angles = {
        axis_id: np.pi / 2 - 2 * np.pi * idx / k
        for idx, axis_id in enumerate(layout.axis_order)
    }

    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"{title} – Hiveplot", fontsize=10)

    node_pos: dict = {}

    # Achsen und Knoten zeichnen
    for axis_id in layout.axis_order:
        ang = angles[axis_id]
        # Achse als Strahl
        ax.plot(
            [0, np.cos(ang) * 1.1],
            [0, np.sin(ang) * 1.1],
            color="#cccccc", lw=1.5, zorder=0
        )
        ax.text(
            np.cos(ang) * 1.18, np.sin(ang) * 1.18,
            f"A{axis_id}",
            ha="center", va="center", fontsize=8,
            color=_AXIS_COLORS[axis_id % len(_AXIS_COLORS)]
        )

        # Knotenreihenfolge: node_groups_expanded > node_groups
        source = layout.node_groups_expanded if layout.node_groups_expanded else layout.node_groups
        ordered_nodes = source.get(axis_id) or []

        n = len(ordered_nodes)
        for rank, node in enumerate(ordered_nodes):
            r = 0.15 + 0.75 * (rank / max(n - 1, 1))
            x = np.cos(ang) * r
            y = np.sin(ang) * r
            node_pos[node] = (x, y)
            is_dummy = isinstance(node, str) and node.startswith("d_")
            color = (
                "#e03c3c"
                if (highlight_nodes and node in highlight_nodes) or is_dummy
                else _AXIS_COLORS[axis_id % len(_AXIS_COLORS)]
            )
            ax.plot(x, y, "o", color=color, ms=7, zorder=3)
            ax.text(
                x + 0.03, y + 0.03, str(node),
                fontsize=6, zorder=4, color="#333333"
            )

    # Kanten vorbereiten
    if just_edges:
        edges_to_draw = list(G.edges())
    else:
        direct_edges = [
            e for e in G.edges()
            if e not in layout.long_edges
            and (e[1], e[0]) not in layout.long_edges
        ]
        edges_to_draw = direct_edges + layout.dummy_edge_segments + layout.intra_axis_edges

    # Hervorhebungskanten in Set
    edge_set = set()
    if highlight_edges:
        for u, v in highlight_edges:
            edge_set.add((u, v))
            edge_set.add((v, u))

    # Kanten zeichnen
    for u, v in edges_to_draw:
        if u not in node_pos or v not in node_pos:
            continue
        x0, y0 = node_pos[u]
        x1, y1 = node_pos[v]
        color = "#e03c3c" if (u, v) in edge_set or (v, u) in edge_set else "#01696f"

        # Kreuzprodukt z-Komponente: positiv → v liegt links von u (vom Ursprung aus),
        # rad entsprechend wählen, damit sich die Kurve nach außen wölbt.
        cross_z = x0 * y1 - y0 * x1
        rad = 0.25 if cross_z > 0 else -0.25

        ax.annotate(
            "",
            xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(
                arrowstyle="-",
                color=color,
                lw=1.2,
                connectionstyle=f"arc3,rad={rad}"
            ),
            zorder=1
        )
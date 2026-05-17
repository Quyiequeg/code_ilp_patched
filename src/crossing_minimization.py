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

from prompt_toolkit import layout

from src.cost import node_or_axes_span
from src.ordering import brute_force_ordering, native_order, node_groups, node_to_axis, reordered_node_groups
from src.partitioning import clauset_newman_moore_communities


def subdivide_long_edges(layout: HivePlotLayout) -> dict[int, list[int]]:

    def clockwise_count(start, end, span):
        dummyposition = (start + 1) % k
        for _ in range(span - 1): # achsen zwischen start und ende
            dummies[dummyposition].append(f"d_{start}_{end}") # name unikal pro achse, achsensegmente leicht rekonstruierbar
            dummyposition = (dummyposition + 1) % k

    def counter_clockwise_count(start, end, span):
        dummyposition = (start - 1) % k
        for _ in range(span - 1): # achsen zwischen start und ende
            dummies[dummyposition].append(f"d_{start}_{end}") # name unikal pro achse, achsensegmente leicht rekonstruierbar
            dummyposition = (dummyposition - 1) % k
            
    k = layout.num_axes
    edges = layout.edges()
    dummies = layout.node_groups_dummies
    for axis in layout.axis_order: # initialisiere dummyliste
        dummies[axis] = []
    for edge in edges:
        # egg = [edge[0]]
        # print(type(egg))
        start = node_to_axis(edge[0], layout.node_groups)
        end = node_to_axis(edge[1], layout.node_groups)
        if node_or_axes_span(start, end, k) > 1:
            span = node_or_axes_span(start, end, k)
            if (start - end) % k < (end - start) % k: # richtung start -> ende, clockwise
                clockwise_count(start, end, span)
            elif (start - end) % k > (end - start) % k: # richtung ende <- start, counter cw
                counter_clockwise_count(start, end, span)
            else: # gleicher spann, routing im uhrzeigersinn
                clockwise_count(start, end, span)




def _sweep():
    pass

def _gap_handling():
    pass

def barycenter_crossmin_pipeline():
    pass

if __name__ == "__main__":
    from src.graphs import sample_graph_selfconstructed, sample_graph_multipartite, sample_graph_caveman
    from src.hiveplot import HivePlotLayout
    # from src.partitioning import louvain_community_detection
    from src.debug_renderer import render_debug

    mode = 0
    if mode == 0:
        G = sample_graph_selfconstructed()
    elif mode == 1:
        G = sample_graph_multipartite()
    elif mode == 2:     
        G = sample_graph_caveman(4, 10)
        # grps = clauset_newman_moore_communities(G)
    print(">>> Initialisierung")
    nodes = list(G.nodes(data="subset"))
    axes = native_order(nodes)
    ng = node_groups(nodes)
    print("<<< ")
    print(">>> Berechnung von phi und alpha-liste")
    phi = brute_force_ordering(axes, ng, list(G.edges()))
    grps = reordered_node_groups(ng, phi)
    print("<<< ")
    print(">>> Initialisiere Layout")
    hpl = HivePlotLayout(
        graph=G,
        num_axes=len(phi),
        axis_order=phi,
        node_groups=grps
    )
    print("<<< ")
    print(">>> Lange Kanten segmentieren und dem Layout übergeben")
    subdivide_long_edges(hpl)
    print("<<< ")
    print("##########################################")
    print(hpl)
    print(hpl.edges())
    print("=== VOR subdivide ===")
    render_debug(hpl, title="VOR subdivide") #output 1
    hpl.node_groups = hpl.fuse_node_groups_with_dummies() # wichtig für die folgenden Schritte, damit die Dummyknoten in den Berechnungen berücksichtigt werden
    print(f"\n=== NACH subdivide ===")
    print("Node Groups mit Dummies:", hpl.node_groups)
    # print(f"Neue Dummy-Knoten: {dummies}")
    render_debug(hpl, title="NACH subdivide") #output 2
    print("##########################################")
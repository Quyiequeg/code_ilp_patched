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

from src.ordering import cyclic_ordering, node_groups


def subdivide_long_edges():
    pass

def _sweep():
    pass

def _gap_handling():
    pass

def barycenter_crossmin_pipeline():
    pass

if __name__ == "__main__":
    print("##########################################")
    from src.graphs import sample_graph_selfconstructed
    from src.hiveplot import HivePlotLayout
    # from src.partitioning import louvain_community_detection
    from src.debug_renderer import draw_hiveplot_debug

    G = sample_graph_selfconstructed()
    nodes = list(G.nodes(data="subset"))
    phi = cyclic_ordering(nodes)
    grps = node_groups(nodes)

    hpl = HivePlotLayout(
        graph=G,
        num_axes=len(phi),
        axis_order=phi,
        node_groups=grps
    )

    print("=== VOR subdivide ===")
    print(hpl)
    print(hpl.axes())
    draw_hiveplot_debug(G, hpl, title="VOR subdivide") #output 1

    # dummies = subdivide_long_edges(G, layout)

    # print(f"\n=== NACH subdivide ===")
    # print(f"Neue Dummy-Knoten: {dummies}")
    # draw_hiveplot_debug(G, layout, title="NACH subdivide",
    #                     highlight_nodes=dummies) #output 2
    print("##########################################")
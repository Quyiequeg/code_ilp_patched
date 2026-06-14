import os
import sys
import time
from datetime import datetime
from logger_setup import setup_logger
import logging
# import cairosvg
from pathlib import Path
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pickle
import networkx as nx
import cost as ct
import graphs as g
from partitioning import (
    clauset_newman_moore_communities,
    louvain_community_detection,
)
from dblp_parser import (
    build_node_identity_maps,
)
from ordering import (
    native_order,
    node_groups,
    brute_force_ordering,
    reordered_node_groups,
    node_to_axis_maps,
)
from crossing_minimization import (
    barycenter_crossmin_pipeline,
    edge_node_cleanup,
)
from ip_model import (
    ip_model_pipeline
)

from hiveplot import HivePlotLayout
from renderer import hiveplot_renderer
import re

def settings(svg_path, node_pt=5, line_pt=1.2, text_pt=0, draw_dummys=True, dummy_size=3):
    with open(svg_path, "r") as f:
        svg = f.read()

    if line_pt != 0:
        svg = re.sub(r'stroke-width="[\d.]+"', f'stroke-width="{line_pt}"', svg)

    if node_pt != 0:
        if draw_dummys:
            svg = re.sub(r'r="0"', f'r="{dummy_size}"', svg)
            svg = re.sub(r'r="[1-9][\d.]*"', f'r="{node_pt}"', svg)
        else:
            svg = re.sub(r'r="[1-9][\d.]*"', f'r="{node_pt}"', svg)

        # x-Koordinate nur in <text ...>-Tags verschieben
        offset = node_pt - 2
        def shift_text_x(match):
            tag_content = match.group(1)
            def replace_x(m):
                x_val = float(m.group(1))
                return f'x="{x_val + offset}"'
            tag_content = re.sub(r'x="([-\d.]+)"', replace_x, tag_content)
            return f'<text {tag_content}'
        svg = re.sub(r'<text ([^>]+)', shift_text_x, svg)

    if text_pt != 0:
        svg = re.sub(r'font-size="[\d.]+"', f'font-size="{text_pt}"', svg)

    with open(svg_path, "w") as f:
        f.write(svg)

def generate_hiveplot(graph_mode: int, pipeline: str = "bary"):
    G = g.sample_graph_selfconstructed_extended(graph_mode)
    nodes = list(G.nodes(data="subset"))
    axes = native_order(nodes)
    ng = node_groups(nodes)
    hpl = HivePlotLayout(
        graph=G,
        num_axes=len(axes),
        axis_order=axes,
        node_groups=ng
    )
    hpl_copy = hpl.copy()
    hpl.axis_order = brute_force_ordering(axes, ng, list(G.edges()))
    print(f"Kosten nach brute force: {ct.cost_function_whole(hpl.axis_order, hpl.node_groups, hpl.edges())}")
    hpl.node_groups = reordered_node_groups(ng, hpl.axis_order)

    # PIPELINE nicht expandiert
    # hpl.node_groups = hpl.fuse_node_groups_with_dummies()
    if pipeline == "bary":
        barycenter_crossmin_pipeline(hpl)
        edge_node_cleanup(hpl)
    elif pipeline == "ilp":
        ip_model_pipeline(hpl, threshold=10)
        edge_node_cleanup(hpl, intra=True)
    return hpl, hpl_copy


if __name__ == "__main__":
    graph_mode = 2
    pipeline = "ilp"
    # pipeline = "bary"
    sec = "3"
    titel = "Model Graph"
    titel_two = f"{titel}_original"
    name = f"{titel}_kapitel_{sec}_gm{graph_mode}_{pipeline}"
    name_two = f"{titel_two}_kapitel_{sec}_gm{graph_mode}_{pipeline}"
    hpl, hpl_copy = generate_hiveplot(graph_mode, pipeline=pipeline)
    expanded = False
    intra = None
    mode = "ba"
    node_labels = True
    axes_labels = True
    draw_dummys = False
    

    hiveplot_renderer(name, hpl, expanded, intra, mode, node_labels, axes_labels)
    hiveplot_renderer(name_two, hpl_copy, expanded, intra, mode, node_labels, axes_labels)
    settings(f"output/ba/{name_two}.svg", node_pt=8, line_pt=3, text_pt=25, draw_dummys=False, dummy_size=None)
    settings(f"output/ba/{name}.svg", node_pt=8, line_pt=3, text_pt=25, draw_dummys=draw_dummys, dummy_size=5)
    if mode == "ba":
        svg_path = f"output/ba/{name}.svg"
    drawing = svg2rlg(f"output/ba/{name}.svg")
    renderPDF.drawToFile(drawing, f"output/ba/{name}.pdf")
    drawing = svg2rlg(f"output/ba/{name_two}.svg")
    renderPDF.drawToFile(drawing, f"output/ba/{name_two}.pdf")
    print(f"Kosten Optimiert: {ct.cost_function_whole(hpl.axis_order, hpl.node_groups, hpl.edges())}")
    print(f"Kosten Original: {ct.cost_function_whole(hpl_copy.axis_order, hpl_copy.node_groups, hpl_copy.edges())}")
    # print(f"Kosten nach brute force: {ct.cost_function_whole(hpl_copy.axis_order, hpl_copy.node_groups, hpl_copy.edges())}")
    # hiveplot_renderer(f"{name}_mit_intra", hpl, intra=True, mode="ba", node_labels=node_labels, axes_labels=axes_labels)
    print(hpl_copy.edges())
import os
import sys
import time
from datetime import datetime
from logger_setup import setup_logger
import logging

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pickle
import networkx as nx

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
    edge_cleanup,
)
from ip_model import (
    ip_model_pipeline
)

from hiveplot import HivePlotLayout
from renderer import hiveplot_renderer


def main():
    setup_logger(per_session=False)
    logger = logging.getLogger(__name__)
    start = time.time()
    year = 2020
    save = True
    # pipeline = "barycenter"
    # method = "paper"
    cache_path = r"E:\Programming Workspace\Python\BA-Sauerteig\dblp_daten_gesamt\gd_graphs.pkl"
    with open(cache_path, "rb") as file:
        graphs = pickle.load(file)
    # Initialisiere Hiveplotlayout
    id_to_name, name_to_id = build_node_identity_maps(graphs[year].nodes())
    original_edges = graphs[year].edges()
    edges = []
    for edge in original_edges:
        edges.append((name_to_id[edge[0]], name_to_id[edge[1]]))
    # logger.info(edges)
    # logger.info(id_to_name, name_to_id)
    G = nx.Graph()
    G.add_edges_from(edges)
    # logger.info(graphs[year])
    # logger.info(G)
    # check auf graphs[year] nodes/edges == G?
    node_grps = clauset_newman_moore_communities(G, 8)
    axes = list(node_grps.keys())
    # logger.info(node_groups)
    hpl = HivePlotLayout(
        graph=G,
        num_axes=len(axes),
        axis_order=axes,
        node_groups=node_grps
    )
    logger.info(f"------------------------START-------{year}------------")
    print(f"ZEIT: {time.time() - start:.1f}")
    logger.info(f"Hiveplotlaut fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen.")
    print(f"ZEIT: {time.time() - start:.1f}")
    hpl.axis_order = brute_force_ordering(axes, node_grps, list(G.edges()))
    hpl.node_groups = reordered_node_groups(node_grps, hpl.axis_order)
    logger.info(f"Brute Force fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen.")
    print(f"ZEIT: {time.time() - start:.1f}")
    ############################################# Pipeline beginnt
    # paper_like = True ##########################
    paper_like = False #########################
    # modus = "bary" #############################
    modus = "ilp" ###############################
    #############################################
    if modus == "bary":
        if paper_like:
            # PIPELINE nicht expandiert
            logger.info(f"paperlike = {paper_like}")
            barycenter_crossmin_pipeline(hpl)
            edge_cleanup(hpl)
            hpl_copy = hpl.copy()
            logger.info(f"Pipeline und Cleanup fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen.")
            print(f"ZEIT: {time.time() - start:.1f}")
            hiveplot_renderer(f"Barycenter_paperkonform_{year}", hpl)
            hiveplot_renderer(f"Barycenter_paperkonform mit intra_{year}", hpl, intra=True)
            # POST EXPANSION
            node_position_map, node_axis_map = node_to_axis_maps(hpl, hpl.node_groups)
            # edge_cleanup(hpl)
            hpl.post_processing_expansion(node_axis_map)
            edge_cleanup(hpl)
            logger.info(f"Post Processing fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen.")
            # logger.info(hpl)
            hiveplot_renderer(f"Barycenter_paperkonform_expandiert_{year}", hpl, expanded=True)
            if save:
                timestamp = datetime.now().strftime("%d.%m--%H.%M")
                filename = f"paper_expanded_hpl_k{hpl.num_axes}_{year}_{timestamp}_edges{len(hpl.edges())}_intra{len(hpl.intra_axis_edges)}.pkl"
                cache_path_out = os.path.join(r"E:\Programming Workspace\Python\BA-Sauerteig\dblp_daten_gesamt", filename)
                with open(cache_path_out, "wb") as file:
                    pickle.dump(hpl, file)
                
                timestamp = datetime.now().strftime("%d.%m--%H.%M")
                filename_copy = f"paper_hpl_k{hpl_copy.num_axes}_{year}_{timestamp}_edges{len(hpl_copy.edges())}_intra{len(hpl_copy.intra_axis_edges)}.pkl"
                cache_path_copy = os.path.join(r"E:\Programming Workspace\Python\BA-Sauerteig\dblp_daten_gesamt", filename_copy)
                with open(cache_path_copy, "wb") as file:
                    pickle.dump(hpl_copy, file)
                logger.info(f"Nicht expandiert Cache gespeichert: {cache_path_copy}")
                logger.info(f"Expandiert Cache gespeichert: {cache_path_out}")
            logger.info(f"Fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen")
            print(f"ZEIT: {time.time() - start:.1f}")
            # logger.info(hpl)
            # logger.info(hpl.edges())
            print(f"ZEIT: {time.time() - start:.1f}")
            logger.info(f"------------------------STOPP--------------------------------")
        elif paper_like == False:
            # PIPELINE expandiert
            logger.info(f"paperlike = {paper_like}")
            barycenter_crossmin_pipeline(hpl, expanded=True)
            edge_cleanup(hpl)
            logger.info(f"Pipeline und Cleanup fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen.")
            print(f"ZEIT: {time.time() - start:.1f}")
            hiveplot_renderer(f"Barycenter_eigen_{year}", hpl, expanded=True)
            if save:
                timestamp = datetime.now().strftime("%d.%m--%H.%M")
                filename = f"self_hpl_k{hpl.num_axes}_{year}_{timestamp}_edges{len(hpl.edges())}_intra{len(hpl.intra_axis_edges)}.pkl"
                cache_path_out = os.path.join(r"E:\Programming Workspace\Python\BA-Sauerteig\dblp_daten_gesamt", filename)
                with open(cache_path_out, "wb") as file:
                    pickle.dump(hpl, file)
                logger.info(f"Cache gespeichert: {cache_path_out}")
            logger.info(f"Fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen")
            # logger.info(hpl)
            # logger.info(hpl.edges())
            print(f"ZEIT: {time.time() - start:.1f}")
            logger.info(f"------------------------STOPP--------------------------------")
    ###################################### ILP
    elif modus == "ilp":
        if paper_like:
            # PIPELINE nicht expandiert
            logger.info(f"paperlike = {paper_like}")
            ip_model_pipeline(hpl, threshold=10)
            edge_cleanup(hpl)
            hpl_copy = hpl.copy()
            logger.info(f"Pipeline und Cleanup fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen.")
            print(f"ZEIT: {time.time() - start:.1f}")
            hiveplot_renderer(f"ILP_paperkonform_{year}", hpl)
            hiveplot_renderer(f"ILP_paperkonform mit intra_{year}", hpl, intra=True)
            # POST EXPANSION
            node_position_map, node_axis_map = node_to_axis_maps(hpl, hpl.node_groups)
            edge_cleanup(hpl)
            hpl.post_processing_expansion(node_axis_map)
            # edge_cleanup(hpl)
            logger.info(f"Post Processing fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen.")
            # logger.info(hpl)
            hiveplot_renderer(f"ILP_paperkonform_expandiert_{year}", hpl, expanded=True)
            if save:
                timestamp = datetime.now().strftime("%d.%m--%H.%M")
                filename = f"paper_expanded_ILP_k{hpl.num_axes}_{year}_{timestamp}_edges{len(hpl.edges())}_intra{len(hpl.intra_axis_edges)}.pkl"
                cache_path_out = os.path.join(r"E:\Programming Workspace\Python\BA-Sauerteig\dblp_daten_gesamt", filename)
                with open(cache_path_out, "wb") as file:
                    pickle.dump(hpl, file)
                
                timestamp = datetime.now().strftime("%d.%m--%H.%M")
                filename_copy = f"paper_ILP_k{hpl_copy.num_axes}_{year}_{timestamp}_edges{len(hpl_copy.edges())}_intra{len(hpl_copy.intra_axis_edges)}.pkl"
                cache_path_copy = os.path.join(r"E:\Programming Workspace\Python\BA-Sauerteig\dblp_daten_gesamt", filename_copy)
                with open(cache_path_copy, "wb") as file:
                    pickle.dump(hpl_copy, file)
                logger.info(f"Nicht expandiert Cache gespeichert: {cache_path_copy}")
                logger.info(f"Expandiert Cache gespeichert: {cache_path_out}")
            logger.info(f"Fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen")
            print(f"ZEIT: {time.time() - start:.1f}")
            # logger.info(hpl)
            # logger.info(hpl.edges())
            print(f"ZEIT: {time.time() - start:.1f}")
            logger.info(f"------------------------STOPP--------------------------------")
        elif paper_like == False:
            # PIPELINE expandiert
            logger.info(f"paperlike = {paper_like}")
            ip_model_pipeline(hpl, threshold=10, expanded=True)
            edge_cleanup(hpl)
            logger.info(f"Pipeline und Cleanup fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen.")
            print(f"ZEIT: {time.time() - start:.1f}")
            hiveplot_renderer(f"ILP_eigen_{year}", hpl, expanded=True)
            if save:
                timestamp = datetime.now().strftime("%d.%m--%H.%M")
                filename = f"self_ILP_k{hpl.num_axes}_{year}_{timestamp}_edges{len(hpl.edges())}_intra{len(hpl.intra_axis_edges)}.pkl"
                cache_path_out = os.path.join(r"E:\Programming Workspace\Python\BA-Sauerteig\dblp_daten_gesamt", filename)
                with open(cache_path_out, "wb") as file:
                    pickle.dump(hpl, file)
                logger.info(f"Cache gespeichert: {cache_path_out}")
            logger.info(f"Fertig. Berechnung in {time.time() - start:.1f}s abgeschlossen")
            # logger.info(hpl)
            # logger.info(hpl.edges())
            print(f"ZEIT: {time.time() - start:.1f}")
            logger.info(f"------------------------STOPP--------------------------------")



if __name__ == "__main__":
    main()
    # start = time.time()
    # year = 2000
    # cache_path = r"E:\Programming Workspace\Python\BA-Sauerteig\dblp_daten_gesamt\gd_graphs.pkl"
    # with open(cache_path, "rb") as file:
    #     graphs = pickle.load(file)

    # id_to_name, name_to_id = build_node_identity_maps(graphs[year].nodes())
    # original_edges = graphs[year].edges()
    # edges = [(name_to_id[e[0]], name_to_id[e[1]]) for e in original_edges]

    # G = nx.Graph()
    # G.add_edges_from(edges)

    # node_grps = clauset_newman_moore_communities(G, 8)

    # for axis, nodes in node_grps.items():
    #     intra = G.subgraph(nodes).number_of_edges()
    #     inter = sum(1 for u, v in G.edges(nodes) if u not in set(nodes) or v not in set(nodes))
    #     print(f"Achse {axis}: {len(nodes)} Knoten | intra={intra} | inter={inter}")
    
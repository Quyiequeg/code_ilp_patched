# stdlib pakete
import os
import sys
from pathlib import Path
import time
from datetime import datetime
import logging
import pickle
import threading

# pakete
import networkx as nx
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

#os path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# src ordner + gd daten
CACHE_DIR = ROOT / "dblp_daten_gesamt"
GD_DATA    = CACHE_DIR / "gd_graphs.pkl"
OUTPUT_DIR = ROOT / "output"

# ordnerstruktur
DEBUG_DIR = OUTPUT_DIR / "debug" # entfernen?
GRAPH_DIR = OUTPUT_DIR / "graphs"
SAVE_DIR = OUTPUT_DIR / "save"
LOAD_DIR = ROOT / "load"
LOG_DIR   = OUTPUT_DIR / "logs"

# bei erstem programmstart ordnerstruktur anlegen
for d in [OUTPUT_DIR, DEBUG_DIR, GRAPH_DIR, SAVE_DIR, LOAD_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# module
from logger_setup import setup_logger
from hiveplot import HivePlotLayout
from renderer import hiveplot_renderer
from logger_setup import log

from partitioning import (
    clauset_newman_moore_communities,
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
    ip_ordering
)
from crossing_minimization import (
    barycenter_crossmin_pipeline,
    edge_node_cleanup,
)
from ip_model import (
    ip_model_pipeline
)

# hilfsfunktionen


## für pipeline
def start_pipeline(config: dict[str, int | str | bool]): # falls gui = true
    thread = threading.Thread(target=pipeline, kwargs=config)
    thread.start()

def init_logger(per_session):
    setup_logger(LOG_DIR, per_session)
    return logging.getLogger(__name__)

def init_original(year: int, own_pkl: str | None = None) -> nx.Graph:
    """Lädt einen Graphen aus dem Cache oder einer eigenen Pickle-Datei.
    
    Args:
        year (int): gewünschte GD-Jahr
        own_pkl (str | None, optional): Dateiname einer .pkl-Datei in LOAD_DIR. Muss ein nx.Graph-Objekt enthalten.

    Returns:
        nx.Graph: das Graph-Objekt
    """
    path = LOAD_DIR / own_pkl if own_pkl else GD_DATA
    with open(path, "rb") as file:
        if own_pkl:
            return pickle.load(file) # nxgraph objekt
        else:
            graphs = pickle.load(file) # dict
            return graphs[year] # eintrag

def init_graph(original: nx.Graph, name_to_id: dict[str, int]): # transformieren
    output_graph = nx.Graph()
    original_edges = original.edges()
    edges = []
    for edge in original_edges:
        edges.append((name_to_id[edge[0]], name_to_id[edge[1]]))
    output_graph.add_edges_from(edges)
    return output_graph

def init_hiveplot(year, own_pkl, partitions, logger) -> HivePlotLayout:
    original = init_original(year=year, own_pkl=own_pkl)
    hpl_basis = {}
    hpl_basis["id_to_name"], hpl_basis["name_to_id"] = build_node_identity_maps(original.nodes())
    hpl_basis["graph"] = init_graph(original, hpl_basis["name_to_id"])
    hpl_basis["node_groups"] = clauset_newman_moore_communities(hpl_basis["graph"], partitions)
    log(logger, "Schritt 1/6 erfolgreich: Pipelineschritt 1 - Partitionierung - abgeschlossen.")
    hpl_basis["axis_order"] = list(hpl_basis["node_groups"].keys())
    hpl_basis["num_axes"] = len(hpl_basis["axis_order"])
    hiveplot = HivePlotLayout(**hpl_basis)
    log(logger, "Schritt 2/6 erfolgreich: HivePlotLayout zum Start der Pipeline erstellt.")
    return hiveplot

def step_ordering(hiveplot: HivePlotLayout, logger: logging.Logger | None ) -> None:
    hiveplot.axis_order = ip_ordering(hiveplot)
    hiveplot.node_groups = reordered_node_groups(hiveplot.node_groups, hiveplot.axis_order)
    log(logger, "Schritt 3/6 erfolgreich: Pipelineschritt 2 - Optimierung der Achsenordnung - abgeschlossen.")

def bary_pipe(): # bekommt paper_like, führt cleanup schon aus
    pass

def ip_pipe(): # bekommt paper_like, führt cleanup schon aus
    pass

def rendering():
    pass

def save_pkl(hiveplot: HivePlotLayout, name: str, save: bool ,logger: logging.Logger | None) -> None:
    if save:
        path = SAVE_DIR / (name + ".pkl")
        with open(path, "wb") as file:
            pickle.dump(hiveplot, file) # dict
        log(logger, f"Hiveplotlayout gespeichert: {path}")
    else:
        log(logger, "Speichern deaktiviert!")

def save_rendered_hiveplot(svg_path: Path, year: int, logger: logging.Logger) -> None:
        year_dir = GRAPH_DIR / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)
        drawing = svg2rlg(svg_path)
        pdf_path = year_dir / svg_path.with_suffix(".pdf").name # verzeichnis ändern
        renderPDF.drawToFile(drawing, str(pdf_path))
        log(logger, f"PDF erfolgreich gespeichert: {pdf_path}")

def pipeline(year: int, output_name: str, variant: str, paper_like: bool, partitions: int = 8, threshold: int = 5,save: bool = False, debug: bool = False, batch: bool = False, own_pkl: str | None = None, gui: bool = False):
    print("Berechnung Start.")
    start = time.time()
    # logging
    if debug: 
        logger = init_logger(per_session = not batch)
    else:
        logger = None
    # graph erzeugen und partitionieren
    log(logger, f"Starte Berechnung für {variant} für das Jahr {year}. Ordnung nach Original: {paper_like}.")
    hiveplot = init_hiveplot(year, own_pkl, partitions, logger)
    # phi berechnen
    step_ordering(hiveplot, logger)
    # zwischenspeichern als debugging-tool
    save_pkl(hiveplot, f"{variant}_{year}_basis_nach_ordering", save, logger)
    if variant == "Barycenterheuristik":
        if paper_like: # originalframework
            # pipeline 3a/b + nachbereitung
            barycenter_crossmin_pipeline(hiveplot, logger, threshold)
            edge_node_cleanup(hiveplot)
            log(logger, "Schritt 4/6 erfolgreich: Pipelineschritt 3 - Barycenter - abgeschlossen.")
            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_vor_expansion", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_vor_expansion", hiveplot, DEBUG_DIR) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            # achsenexpansion vorbereitung + durchführung + nachbereitung
            _, node_axis_map = node_to_axis_maps(hiveplot, hiveplot.node_groups)
            hiveplot.post_processing_expansion(node_axis_map)
            log(logger, "Schritt 5/6 erfolgreich: Achsenexpansion - Barycenter - abgeschlossen.")
            edge_node_cleanup(hiveplot)
            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_nach_expansion_geordnet", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_nach_expansion_geordnet", hiveplot, DEBUG_DIR, expanded = True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            log(logger, "Schritt 6/6 erfolgreich: Speichern - Barycenter - abgeschlossen.")
            log(logger, f"Pipeline ENDE nach {elapsed:.2f}s")
        else:
            # pre_processing_expansion + pipeline 3a/b + nachbereitung
            barycenter_crossmin_pipeline(hiveplot, logger, expanded=True)
            log(logger, "Schritt 4/6 erfolgreich: Pipelineschritt 3 - Barycenter - abgeschlossen.")
            edge_node_cleanup(hiveplot)
            log(logger, "Schritt 5/6 erfolgreich: Bereinigung - Barycenter - abgeschlossen.")
            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_nach_expansion_ungeordnet", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_nach_expansion_ungeordnet", hiveplot, DEBUG_DIR, expanded = True, unordered = True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            log(logger, "Schritt 6/6 erfolgreich: Rendern und Speichern - Barycenter - abgeschlossen.")
            elapsed = time.time() - start
            log(logger, f"Pipeline ENDE nach {elapsed:.2f}s")
    else:
        if paper_like: # originalframework
            # pipeline 3a/b + nachbereitung
            ip_model_pipeline(hiveplot, logger, threshold)
            edge_node_cleanup(hiveplot)
            log(logger, "Schritt 4/6 erfolgreich: Pipelineschritt 3 - ILP - abgeschlossen.")
            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_vor_expansion", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_vor_expansion", hiveplot, DEBUG_DIR) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            # achsenexpansion vorbereitung + durchführung + nachbereitung
            _, node_axis_map = node_to_axis_maps(hiveplot, hiveplot.node_groups)
            hiveplot.post_processing_expansion(node_axis_map)
            log(logger, "Schritt 5/6 erfolgreich: Achsenexpansion - ILP - abgeschlossen.")
            edge_node_cleanup(hiveplot)
            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_nach_expansion_geordnet", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_nach_expansion_geordnet", hiveplot, DEBUG_DIR, expanded = True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            log(logger, "Schritt 6/6 erfolgreich: Speichern - ILP - abgeschlossen.")
            elapsed = time.time() - start
            log(logger, f"Pipeline ENDE nach {elapsed:.2f}s")
        else:
            # pre_processing_expansion + pipeline 3a/b + nachbereitung
            ip_model_pipeline(hiveplot, logger, threshold, expanded = True)
            log(logger, "Schritt 4/6 erfolgreich: Pipelineschritt 3 - ILP - abgeschlossen.")
            edge_node_cleanup(hiveplot)
            log(logger, "Schritt 5/6 erfolgreich: Bereinigung - ILP - abgeschlossen.")
            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_nach_expansion_ungeordnet", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_nach_expansion_ungeordnet", hiveplot, DEBUG_DIR, expanded = True, unordered = True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            log(logger, "Schritt 6/6 erfolgreich: Rendern und Speichern - ILP - abgeschlossen.")
            elapsed = time.time() - start
            log(logger, f"Pipeline ENDE nach {elapsed:.2f}s")
    log(logger, f"-----------------------------------")
    print("Berechnung Ende.")


def main():
    config = {
        "year": 2019,
        "output_name": "beispiel",
        "variant": "Barycenterheuristik",
        # "variant": "1L2S-ILP",
        # "paper_like": True,
        "paper_like": False,
        "partitions": 8,
        "threshold": 5,
        # "save": False,
        "save": True,
        # "debug": False,
        "debug": True,
        # "batch": False,
        "batch": True,
        "own_pkl": None,
        "gui": False,
    }
    

    # für einzeln
    pipeline(**config)

    # für batch
    # for year in range(2000, 2025):
    #     config["year"] = year
    #     pipeline(**config)

if __name__ == "__main__":
    main()
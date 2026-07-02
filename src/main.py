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
from experiments import DataCollector

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
EXPERIMENT_DATA = OUTPUT_DIR / "experiments"

# bei erstem programmstart ordnerstruktur anlegen
for d in [OUTPUT_DIR, DEBUG_DIR, GRAPH_DIR, SAVE_DIR, LOAD_DIR, LOG_DIR, EXPERIMENT_DATA]:
    d.mkdir(parents=True, exist_ok=True)


# module
from logger_setup import setup_logger
from hiveplot import (HivePlotLayout, )
from renderer import hiveplot_renderer
from logger_setup import setup_logger, log

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
from experiments import hypothesis_one
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
    path = SAVE_DIR / own_pkl if own_pkl else GD_DATA
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
    start = time.time()
    original = init_original(year=year, own_pkl=own_pkl)
    hpl_basis = {}
    hpl_basis["id_to_name"], hpl_basis["name_to_id"] = build_node_identity_maps(original.nodes())
    hpl_basis["graph"] = init_graph(original, hpl_basis["name_to_id"])
    hpl_basis["node_groups"] = clauset_newman_moore_communities(hpl_basis["graph"], partitions)
    elapsed = time.time() - start
    # log(logger, f"Schritt 1/6 erfolgreich: Pipelineschritt 1 - Partitionierung - abgeschlossen nach {elapsed:.10f}s.")
    hpl_basis["axis_order"] = list(hpl_basis["node_groups"].keys())
    hpl_basis["num_axes"] = len(hpl_basis["axis_order"])
    hiveplot = HivePlotLayout(**hpl_basis)
    # log(logger, "Schritt 2/6 erfolgreich: HivePlotLayout zum Start der Pipeline erstellt.")
    return hiveplot

def step_ordering(hiveplot: HivePlotLayout, logger: logging.Logger | None ) -> None:
    hiveplot.axis_order = ip_ordering(hiveplot)
    hiveplot.node_groups = reordered_node_groups(hiveplot.node_groups, hiveplot.axis_order)
    # log(logger, "Schritt 3/6 erfolgreich: Pipelineschritt 2 - Optimierung der Achsenordnung - abgeschlossen.")

def save_pkl(hiveplot: HivePlotLayout, name: str, save: bool ,logger: logging.Logger | None) -> None:
    if save:
        path = SAVE_DIR / (name + ".pkl")
        with open(path, "wb") as file:
            pickle.dump(hiveplot, file) # dict
        log(logger, f"Hiveplotlayout gespeichert: {path}")
    # else:
    #     log(logger, "Speichern deaktiviert!")

def save_rendered_hiveplot(svg_path: Path, year: int, logger: logging.Logger) -> None:
        year_dir = GRAPH_DIR / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)
        drawing = svg2rlg(svg_path)
        pdf_path = year_dir / svg_path.with_suffix(".pdf").name # verzeichnis ändern
        renderPDF.drawToFile(drawing, str(pdf_path))
        # log(logger, f"PDF erfolgreich gespeichert: {pdf_path}")

def pipeline(year: int, run: int, logger: logging.Logger, output_name: str | None, variant: str, paper_like: bool, partitions: int = 8, threshold: int = 5, save: bool = False, debug: bool = False, batch: bool = False, own_pkl: str | None = None, gui: bool = False):
    print("Berechnung Start.")
    collector = DataCollector()
    collected_data = {}
    start_begin = time.time()
    # graph erzeugen und partitionieren
    # log(logger, f"Starte Berechnung für {variant} für das Jahr {year}. Ordnung nach Original: {paper_like}.")
    
    hiveplot = init_hiveplot(year, own_pkl, partitions, logger)
    if variant == "Barycenterheuristik":
        collected_data["init_hiveplot Bary t"] = time.time() - start_begin
    else:    
        collected_data["init_hiveplot ILP t"] = time.time() - start_begin

    # phi berechnen
    start = time.time()
    step_ordering(hiveplot, logger)
    if variant == "Barycenterheuristik":
        collected_data["step_ordering Bary t"] = time.time() - start
    else:    
        collected_data["step_ordering ILP t"] = time.time() - start

    # zwischenspeichern als debugging-tool
    save_pkl(hiveplot, f"{variant}_{year}_basis_nach_ordering", save, logger)
    if variant == "Barycenterheuristik":
        if paper_like: # originalframework
            # pipeline 3a/b + nachbereitung
            start = time.time()
            barycenter_crossmin_pipeline(hiveplot, logger, threshold)
            collected_data["barycenter_crossmin_pipeline t"] = time.time() - start

            start = time.time()
            hiveplot.crossings = hiveplot.count_crossings()
            collected_data["count_crossings Bary 1 t"] = time.time() - start

            edge_node_cleanup(hiveplot)
            # log(logger, "Schritt 4/6 erfolgreich: Pipelineschritt 3 - Barycenter - abgeschlossen.")
            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_vor_expansion_P({partitions})", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_vor_expansion_P({partitions})", hiveplot, DEBUG_DIR) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            # achsenexpansion vorbereitung + durchführung + nachbereitung
            _, node_axis_map = node_to_axis_maps(hiveplot, hiveplot.node_groups)

            start = time.time()
            hiveplot.post_processing_expansion(node_axis_map)
            collected_data["post_processing_expansion Bary t"] = time.time() - start

            # log(logger, "Schritt 5/6 erfolgreich: Achsenexpansion - Barycenter - abgeschlossen.")
            edge_node_cleanup(hiveplot)

            start = time.time()
            hiveplot.crossings_expanded = hiveplot.count_crossings(True)
            collected_data["count_crossings Bary 2 t"] = time.time() - start
            
            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_nach_expansion_geordnet_P({partitions})", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_nach_expansion_geordnet_P({partitions})", hiveplot, DEBUG_DIR, expanded = True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            # log(logger, "Schritt 6/6 erfolgreich: Speichern - Barycenter - abgeschlossen.")
            # elapsed = time.time() - start
            # log(logger, f"Pipeline ENDE nach {elapsed:.2f}s")

            elapsed = time.time() - start_begin
            collected_data["Barycenter gesamt t"] = elapsed
            collector.update(f"Laufzeitenvergleich Bary/ILP", year, **collected_data)
        else:
            # pre_processing_expansion + pipeline 3a/b + nachbereitung
            barycenter_crossmin_pipeline(hiveplot, logger, expanded=True)
            log(logger, "Schritt 4/6 erfolgreich: Pipelineschritt 3 - Barycenter - abgeschlossen.")
            edge_node_cleanup(hiveplot)
            hiveplot.crossings_expanded = hiveplot.count_crossings(True)
            log(logger, "Schritt 5/6 erfolgreich: Bereinigung - Barycenter - abgeschlossen.")
            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_nach_expansion_ungeordnet_P({partitions})", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_nach_expansion_ungeordnet_P({partitions})", hiveplot, DEBUG_DIR, expanded = True, unordered = True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            log(logger, "Schritt 6/6 erfolgreich: Rendern und Speichern - Barycenter - abgeschlossen.")
            elapsed = time.time() - start
            log(logger, f"Pipeline ENDE nach {elapsed:.2f}s")
    else:
        if paper_like: # originalframework
            # pipeline 3a/b + nachbereitung
            start = time.time()
            ip_model_pipeline(hiveplot, logger, threshold)
            collected_data["ip_model_pipeline t"] = time.time() - start

            start = time.time()
            hiveplot.crossings = hiveplot.count_crossings()
            collected_data["count_crossings ILP 1 t"] = time.time() - start
            
            edge_node_cleanup(hiveplot)
            # log(logger, "Schritt 4/6 erfolgreich: Pipelineschritt 3 - ILP - abgeschlossen.")
            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_vor_expansion_P({partitions})", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_vor_expansion_P({partitions})", hiveplot, DEBUG_DIR) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            # achsenexpansion vorbereitung + durchführung + nachbereitung
            _, node_axis_map = node_to_axis_maps(hiveplot, hiveplot.node_groups)

            start = time.time()
            hiveplot.post_processing_expansion(node_axis_map)
            collected_data["post_processing_expansion ILP t"] = time.time() - start

            # log(logger, "Schritt 5/6 erfolgreich: Achsenexpansion - ILP - abgeschlossen.")
            edge_node_cleanup(hiveplot)

            start = time.time()
            hiveplot.crossings_expanded = hiveplot.count_crossings(True)
            collected_data["count_crossings ILP 2 t"] = time.time() - start

            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_nach_expansion_geordnet_P({partitions})", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_nach_expansion_geordnet_P({partitions})", hiveplot, DEBUG_DIR, expanded = True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            # log(logger, "Schritt 6/6 erfolgreich: Speichern - ILP - abgeschlossen.")


            elapsed = time.time() - start_begin
            collected_data["1L2S-ILP gesamt t"] = elapsed
            collector.update(f"Laufzeitenvergleich Bary/ILP", year, **collected_data)
            print(f"Speichere x = {run}, Laufzeit = {elapsed:.5f}, crossings = {hiveplot.crossings_expanded}")
            # log(logger, f"Pipeline ENDE nach {elapsed:.2f}s")
        else:
            # pre_processing_expansion + pipeline 3a/b + nachbereitung
            ip_model_pipeline(hiveplot, logger, threshold, expanded = True)
            log(logger, "Schritt 4/6 erfolgreich: Pipelineschritt 3 - ILP - abgeschlossen.")
            edge_node_cleanup(hiveplot)
            hiveplot.crossings_expanded = hiveplot.count_crossings(True)
            log(logger, "Schritt 5/6 erfolgreich: Bereinigung - ILP - abgeschlossen.")
            # zwischenspeichern + rendern
            save_pkl(hiveplot, f"{variant}_{year}_nach_expansion_ungeordnet_P({partitions})", save, logger) # snapshot
            svg_path = hiveplot_renderer(f"{variant}_{year}_nach_expansion_ungeordnet_P({partitions})", hiveplot, DEBUG_DIR, expanded = True, unordered = True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)
            log(logger, "Schritt 6/6 erfolgreich: Rendern und Speichern - ILP - abgeschlossen.")
            elapsed = time.time() - start
            log(logger, f"Pipeline ENDE nach {elapsed:.2f}s")
    # log(logger, f"-----------------------------------")
    print(f" FIXED DELTA: {hiveplot.fixed_inter_axis_delta}")
    print("Berechnung Ende.")


def main():
    config = {
        "year": 2001,
        "output_name": "",
        "logger": None,
        # "variant": "Barycenterheuristik",
        "variant": "1L2S-ILP",
        "paper_like": True,
        # "paper_like": False,
        "partitions": 8,
        "threshold": 10,
        "save": False,
        # "save": True,
        "debug": False,
        # "debug": True,
        "batch": False,
        # "batch": True,
        "own_pkl": None,
        "gui": False,
    }
    if config["output_name"]: # ausgabe für experimente
            logger = setup_logger(EXPERIMENT_DATA, per_session = not config["batch"], file_name = config["output_name"])
            config["logger"] = logger
    else:
        if config["debug"]: # ausgabe für debug
            logger = init_logger(per_session = not logger["batch"])
            config["logger"] = logger
    

    # für einzeln
    pipeline(run = 0, **config)
    # für batch
    # for i in range(1, 101):
    # for year in range(2000, 2025):
        # print(i)
        # pipeline(run = i, **config)


    ############################ H1 ##################################
    # E1: auswahl an graphen ermitteln, vergleich der knoten möglich
    # get_values_overall(EXPERIMENT_DATA, "Kanten_Knoten_komplett", 1)

    # E2.1: einzellaufzeiten ermitteln -> 1. versuch tau = 4, 8, nativ = 0 -> abbruch laufzeit zu lang
    # E2.3: threshold von nativ auf 12 -> 2. versuch tau = 4, 8, 12 -> abbruch und test mit 10
    # E2.4: threshold von 12 auf 10
    # free_range = [2000, 2008, 2024] # testgruppe
    # partitions = [4, 8, 10] # threshold tau
    # for year in free_range:
    #     for partition in partitions:
    #         config["year"] = year
    #         config["partitions"] = partition
    #         pipeline(**config)
    #         print(f"Jahr: {year}, TAU: {partition} - abgeschlossen")
    
    # E2.2 versuch 2: native communities bestimmen, daraus threshold ableiten
    # hypothesis_one(EXPERIMENT_DATA, mode = 2, config=config)
    # nach evaluation des ergebnisses dritten threshold auf tau = 12
    
    # E2.5 relative anzahl der intra-axis kanten an der gesamtzahl ermitteln, könnte ein guter indikator für die rechenzeit des ILP für Optimierung der Achsenordnung sein
    # wir normieren über tau = 6 -> guter kompromiss zwischen optimierter ordnung und rechenzeit, wir erfassen zusätzlich die rechenzeit
    # hypothesis_one(EXPERIMENT_DATA, mode = 3, config = config)
    
    # E2.6 vorherige daten sind noch nicht aussagekräftig, wir ermitteln nochmal für tau=8 und vergleichen die ergebnisse
    # hypothesis_one(EXPERIMENT_DATA, 3, config)
    # Feststellung: wir wählen tau 4, 6, 8 und G2004 0 inter für tau = 6 / G2016 (besonders interessant) anteil inter axis für tau = 6 6,71% und tau = 8 10,79%/G2024 für viele, stabile inter axis kanten

    # E3 wir haben nun graph_range und partition_range bestimmt und führen die abschließende berechnungen durch, wonach wir die kreuzungszahlen vergleichen
    # berechnung mit 1L2S, paper_like = True, Abbruchparameter für 1L2S = 10
    # erst einzelner testlauf für einen durchgang
    # graph_range = [2000, 2008, 2024] # testgruppe
    # partitions = [4, 6, 8] # threshold tau
    # log(logger, f"| {'Jahr':>5} | {'Rechenzeit':>5} | {'Schwellenwert':>5} | {'Kreuzungen':>5} |")
    # log(logger, f"-----------------------------------------")
    # for year in graph_range:
    #     for partition in partitions:
    #         print(f"Start, Graph: {year}, tau: {partition}")
    #         config["year"] = year
    #         config["partitions"] = partition
    #         pipeline(**config)
    #         print(f"Ende, Graph: {year}, tau: {partition}")
    #         print("--------------------")
    # log(logger, f"-----------------------------------------")

if __name__ == "__main__":
    main()
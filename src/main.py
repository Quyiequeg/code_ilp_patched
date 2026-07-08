# stdlib pakete
import sys
from pathlib import Path
import time
from datetime import datetime
import logging
import pickle

# pakete
import networkx as nx
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
from hiveplot import (HivePlotLayout)
from renderer import hiveplot_renderer
from logger_setup import setup_logger, log

from partitioning import (
    clauset_newman_moore_communities,
)
from dblp_parser import (
    build_node_identity_maps,
)
from ordering import (
    reordered_node_groups,
    ip_ordering
)
from crossing_minimization import (
    barycenter_crossmin_pipeline,
    edge_node_cleanup,
)
from ip_model import (
    ip_model_pipeline
)
from experiments import DataCollector
## hilfsfunktionen für pipeline
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
    original = init_original(year=year, own_pkl=own_pkl)
    hpl_basis = {}
    hpl_basis["id_to_name"], hpl_basis["name_to_id"] = build_node_identity_maps(original.nodes())
    hpl_basis["graph"] = init_graph(original, hpl_basis["name_to_id"])
    hpl_basis["node_groups"] = clauset_newman_moore_communities(hpl_basis["graph"], partitions)
    hpl_basis["axis_order"] = list(hpl_basis["node_groups"].keys())
    hpl_basis["num_axes"] = len(hpl_basis["axis_order"])
    hiveplot = HivePlotLayout(**hpl_basis)
    return hiveplot

def step_ordering(hiveplot: HivePlotLayout, logger: logging.Logger | None ) -> None:
    hiveplot.axis_order = ip_ordering(hiveplot)
    hiveplot.node_groups = reordered_node_groups(hiveplot.node_groups, hiveplot.axis_order)

def save_pkl(hiveplot: HivePlotLayout, name: str, save: bool , logger: logging.Logger | None) -> None:
    if save:
        path = SAVE_DIR / (name + ".pkl")
        with open(path, "wb") as file:
            pickle.dump(hiveplot, file) # dict
        log(logger, f"Hiveplotlayout gespeichert: {path}")

def save_rendered_hiveplot(svg_path: Path, year: int, logger: logging.Logger) -> None:
        year_dir = GRAPH_DIR / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)
        drawing = svg2rlg(svg_path)
        pdf_path = year_dir / svg_path.with_suffix(".pdf").name # verzeichnis ändern
        renderPDF.drawToFile(drawing, str(pdf_path))

## pipeline
def pipeline(year: int, run: int, logger: logging.Logger, output_name: str | None, variant: str, paper_like: bool, partitions: int = 8, threshold: int = 5, save: bool = False, debug: bool = False, batch: bool = False, own_pkl: str | None = None, gui: bool = False):

    # für versuchsdaten, siehe unten
    print("Berechnung Start.")
    collector = DataCollector()
    collected_data_time = {}
    collected_data_crossings = {}
    start_time = time.time()

    # graph erzeugen und partitionieren
    hiveplot = init_hiveplot(year, own_pkl, partitions, logger)

    # achsenordnung optimieren
    step_ordering(hiveplot, logger)

    # zwischenspeichern der zwischenbasis
    save_pkl(hiveplot, f"{variant}_{year}_basis_nach_ordering", save, logger)

    if variant == "Barycenterheuristik":
        if paper_like: # originalframework
            # subpipeline
            barycenter_crossmin_pipeline(hiveplot, logger, threshold, paper_like)

            # kreuzungszahlen und konsistenz
            hiveplot.crossings_expanded = hiveplot.count_crossings(True)
            edge_node_cleanup(hiveplot)
            print(hiveplot.crossings_expanded)

            # Beispiel: Messdaten speichern
            # elapsed = time.time() - start_time
            # collected_data_time[f"Laufzeit {partitions}"] = round(elapsed, 5)
            # collected_data_crossings[f"Kreuzungen {partitions}"] = hiveplot.crossings_expanded
            # collector.update("Parameterstudie", partitions, **collected_data_time)
            # collector.update("Parameterstudie", partitions, **collected_data_crossings)

            # speichern des fertigen HPL
            save_pkl(hiveplot, f"{variant}_{year}_P({partitions})_paperlike({paper_like})", save, logger) # snapshot

            # rendern und als pdf speichern
            svg_path = hiveplot_renderer(f"{variant}_{year}_P({partitions})_paperlike({paper_like})", hiveplot, DEBUG_DIR, layout_expanded=True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)

        else: # erweitert
            # subpipeline
            barycenter_crossmin_pipeline(hiveplot, logger, threshold, paper_like=False)

            # kreuzungszahlen und konsistenz
            edge_node_cleanup(hiveplot)
            hiveplot.crossings_expanded = hiveplot.count_crossings(True)
            print(hiveplot.crossings_expanded)

            # speichern des fertigen HPL
            save_pkl(hiveplot, f"{variant}_{year}_P({partitions})_paperlike({paper_like})", save, logger) # snapshot
            
            # rendern und als pdf speichern
            svg_path = hiveplot_renderer(f"{variant}_{year}_P({partitions})_paperlike({paper_like})", hiveplot, DEBUG_DIR, layout_expanded = True, unordered = True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)

    else: # ilp
        if paper_like: # originalframework
            # subpipeline
            ip_model_pipeline(hiveplot, logger, threshold, paper_like)

            # kreuzungszahlen und konsistenz
            hiveplot.crossings_expanded = hiveplot.count_crossings(True)
            print(hiveplot.crossings_expanded)
            edge_node_cleanup(hiveplot)

            # speichern des fertigen HPL
            save_pkl(hiveplot, f"{variant}_{year}_P({partitions})_paperlike({paper_like})", save, logger) # snapshot
            
            # rendern und als pdf speichern
            svg_path = hiveplot_renderer(f"{variant}_{year}_P({partitions})_paperlike({paper_like})", hiveplot, DEBUG_DIR, layout_expanded=True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)

        else: # erweitert
            # subpipeline
            ip_model_pipeline(hiveplot, logger, threshold, paper_like=False)

            # kreuzungszahlen und konsistenz
            edge_node_cleanup(hiveplot)
            hiveplot.crossings_expanded = hiveplot.count_crossings(True)
            print(hiveplot.crossings_expanded)

            # speichern des fertigen HPL
            save_pkl(hiveplot, f"{variant}_{year}_P({partitions})_paperlike({paper_like})", save, logger) # snapshot

            # rendern und als pdf speichern
            svg_path = hiveplot_renderer(f"{variant}_{year}_P({partitions})_paperlike({paper_like})", hiveplot, DEBUG_DIR, layout_expanded = True, unordered = True) # optionale parameter möglich
            save_rendered_hiveplot(svg_path, year, logger)

    print("Berechnung Ende.")

def main():
    # parameter für die pipeline
    config = {
        "year": 2017,
        "output_name": "",
        "logger": None,
        # "variant": "Barycenterheuristik",
        "variant": "1L2S-ILP",
        # "paper_like": True,
        "paper_like": False,
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

    #logger init
    if config["output_name"]: # ausgabe für experimente
            logger = setup_logger(EXPERIMENT_DATA, per_session = not config["batch"], file_name = config["output_name"])
            config["logger"] = logger
    else:
        if config["debug"]: # ausgabe für debug
            logger = init_logger(per_session = not logger["batch"])
            config["logger"] = logger
    

    # einzeldurchlauf
    pipeline(run = 0, **config)

    # für batchläufe
    # for i in range(2000, 2025): # run kann auch als run = 0 übergeben und die iteration angepasst werden
    #         config["year"] = i
    #         print(f"year {i} - variant {config['variant']}")
    #         pipeline(run=0, **config)

if __name__ == "__main__":
    main()
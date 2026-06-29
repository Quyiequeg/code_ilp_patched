import networkx as nx
from logger_setup import setup_logger, log
from pathlib import Path


def hypothesis_one(exp_dir: Path, mode: int, config: dict[str, str | bool | int | None], theme: str = None) -> None:
    from main import init_original, init_hiveplot, step_ordering
    from partitioning import clauset_newman_moore_communities
    from cost import node_or_axes_span
    import time
    from datetime import datetime
    from ordering import node_to_axis_maps
    if not theme:
         theme = config["output_name"]
    logger = setup_logger(exp_dir, False, theme)
    graphs = {}
    for year in range(2000, 2025): # graphen lesen
            graphs[year] = init_original(year)
    logger = setup_logger(exp_dir, False, theme)
    log(logger, f"Tabelle: {theme}")
    log(logger, f"--------------------------------------------------------------------")
    if mode == 1: # E1  eingabegraphen bestimmen
        for year in range(2000, 2025):
            graph = graphs[year]
            log(logger, f"|Jahr: {year} | Knoten: {len(graph.nodes):>5} | Kanten: {len(graph.edges):>6} |")
            log(logger, f"--------------------------------------------------------------------")
    elif mode == 2: # E2.2 threshold nativ nicht umsetzbar da achsenordnung zu lang rechnet 17 min für graph 2000 dann abgebrochen, finde native communities für alle graphen heraus
        for year in range(2000, 2025):
            graph = graphs[year]
            node_groups = clauset_newman_moore_communities(graph, 0)
            log(logger, f"|Jahr: {year} | native Partitionen: {len(node_groups.keys()):>5} |")
            log(logger, f"--------------------------------------------------------------------")
    elif mode == 3: # E2.5 tau=6, E2.6 tau = 8
        table = []
        for year in range(2000, 2025):
            runtime = time.time()
            print(f"Berechne: {year}")
            native = clauset_newman_moore_communities(graphs[year], 0)
            hiveplot = init_hiveplot(year, config["own_pkl"], config["partitions"], logger)
            step_ordering(hiveplot, logger)
            _, node_axis_map = node_to_axis_maps(hiveplot, hiveplot.node_groups)
            edges = hiveplot.edges()
            inter_axis_count = 0
            for edge in edges:
                 if node_or_axes_span(node_axis_map[edge[0]], node_axis_map[edge[1]], hiveplot.num_axes) >=1:
                    inter_axis_count += 1
            elapsed = time.time() - runtime
            table.append(f"|Jahr {year:>5} | {inter_axis_count:> 5} | {(inter_axis_count/len(hiveplot.edges())*100):>5.2f} | {len(native.keys()):>5} | {elapsed:>10.5f} |")
            print(f"Abgeschlossen: {year}")
        log(logger, f"| {'Jahr':>5} | {'inter-axis Kanten':>5} | {'absoluter Anteil an Kanten':>5} | {'native Partitionen':>5} | {'Rechenzeit':>5} |")
        log(logger, f"--------------------------------------------------------------------")
        for tab in table:
            log(logger, tab)
            log(logger, f"--------------------------------------------------------------------")
    elif mode == 4:
        
        pass
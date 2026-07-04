import networkx as nx
from logger_setup import setup_logger, log
from pathlib import Path
import pickle

_BASE = Path(__file__).parent.parent  # src/ -> repo root
_DEFAULT_PATH = _BASE / "output/experiments/results.pkl"

class DataCollector:
    """Zentrale Datenstruktur für den Datensatz der Experimente.
    """
    data_sets: dict[str, dict[str, list]]
    BASE = Path(__file__).parent.parent  # src/ -> repo root
    path: Path = BASE / "output/experiments/results.pkl"

    def __init__(self, path: Path = _DEFAULT_PATH):
        # path exists -> path laden, falls nicht save()
        self.path = path
        if path.exists():
            with open(path, "rb") as file:
                self.data_sets = pickle.load(file)
        else:
            self.data_sets = {}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.save()
            

    def __str__(self):
            """Besser lesbarere Darstellung der -Instanz bei Test und debugging.

            Returns:
                str: Zeilenweise Ausgabe der Felder.
            """
            lines = [
                f"Datensatz der Experimente:",
                f"  Anzahl erfasster Datensätze: {len(self.data_sets.keys())}",
            ]
            return "\n".join(lines)

    def update(self, data_set: str, x_val: str | int | float = None, **kwargs: int | float | None) -> None:
        if data_set not in self.data_sets: # muss neu angelegt werden
            self.data_sets[data_set] = {}
            dset = self.data_sets[data_set]
            dset.setdefault("x", []).append(x_val)
            for arg in kwargs:
                dset.setdefault(arg, []).append(kwargs[arg])
        else: # update
            dset = self.data_sets[data_set]
            if x_val in dset["x"]: # falls x vorhanden, ersetze kwargs für index x
                index = dset["x"].index(x_val)
                for arg in kwargs: # vorhandenen key updaten, neuen key anlegen
                    dset.setdefault(arg, [None] * len(dset["x"]))[index] = kwargs[arg]
            else: # falls x nicht vorhanden, setze x und ordne kwarg einträge zu
                dset["x"].append(x_val)
                for arg in kwargs:
                    dset[arg].append(kwargs[arg])
        self.save()

    def save(self) -> None:
        with open(self.path, "wb") as file:
            pickle.dump(self.data_sets, file)

    def delete(self, data_set: str, x_val: list[int | str] | str | int | float = None) -> None:
        if data_set in self.data_sets:
            dset = self.data_sets[data_set]
            if x_val is not None: # alle einträge für x aus keys entfernen
                targets = x_val if isinstance(x_val, list) else [x_val]
                for val in targets:
                    index = dset["x"].index(val)
                    for key in dset:
                        dset[key].pop(index)
            else: # komplett löschen
                confirm = input(
                    f"Datensatz '{data_set}' vollständig löschen? "
                    "(j/N): "
                ).strip().lower()

                if confirm in ("j", "y", "ja", "yes"):
                    del self.data_sets[data_set]
                    self.save()
                    print(f"Datensatz {data_set} erfolgreich gelöscht!")
                else:
                    print("Löschvorgang abgebrochen.")
        else:
            print("Datenset nicht bekannt!")

    def data_keys(self, data_set: str = None) -> list[str]:
        if data_set is not None:
            return list(self.data_sets[data_set].keys())
        return list(self.data_sets.keys())
    
    def get_data_set(self, data_set: str):
        if data_set in self.data_sets:
            dset = self.data_sets[data_set]
            print(f">>> {data_set} <<<")
            for key in dset:
                print(key)
                print(dset[key])
                print("--------")
            return self.data_sets[data_set]
        else:
            print("Datensatz unbekannt!")
        pass
    
    def missing(self) -> list[tuple[str, str | int | float, list[str]]]:
        """Überprüft die Datensätze auf fehlende Einträge. Falls welche gefunden werden gibt es eine Liste aus Tupeln zurück, 
        wobei das Tupel (Datensatz, x, fehlende Datenpunktbezeichner) ist. Falls x schon fehlt wird dies kenntlich gemacht.

        Returns:
            list[tuple[str, str | int | float, list[str]]]: Fehlende Einträge
        """
        missing = []
        for data_set in self.data_sets:
            dset = self.data_sets[data_set]
            for i, x_val in enumerate(dset["x"]):
                missing_keys = []
                for key in dset:
                    if key != "x" and dset[key][i] is None:
                        missing_keys.append(key)
                if x_val is None:
                    missing_keys.append("x")
                if missing_keys:
                    label = x_val if x_val is not None else f"Index {i}"
                    missing.append((data_set, label, missing_keys))
        return missing
                    
    def validate(self, data_set: str) -> bool | None:
        """Ermittelt ob die Einträge des Datensatzes gleich viele Datenpunkte enthalten. 

        Args:
            data_set (str): betrachteter Datensatz

        Returns:
            bool | None: True = wenn Einträge gleiche Länge, sonst False. falls Datensatz fehlt Debug-Ausgabe
        """
        if data_set in self.data_sets:
            dset = self.data_sets[data_set]
            for data_point in dset:
                if len(dset[data_point]) != len(dset["x"]):
                    return False
            return True
        else:
            print("Datenset nicht vorhanden!")
    
    def merge(self):
        raise NotImplementedError("merge not implemented yet")


def hypothesis_one(exp_dir: Path, mode: int, config: dict[str, str | bool | int | None], theme: str = None) -> None:
    from main import init_original, init_hiveplot, step_ordering
    from partitioning import clauset_newman_moore_communities
    from cost import node_or_axes_span
    import time
    from datetime import datetime
    from ordering import node_to_axis_maps

    db = DataCollector()
    if not theme:
         theme = config["output_name"]
    logger = setup_logger(exp_dir, False, theme)
    graphs = {}
    for year in range(2000, 2025): # graphen lesen
            graphs[year] = init_original(year)
    logger = setup_logger(exp_dir, False, theme)
    # log(logger, f"Tabelle: {theme}")
    # log(logger, f"--------------------------------------------------------------------")
    if mode == 1: # E1  eingabegraphen bestimmen
        for year in range(2000, 2025):
            graph = graphs[year]
            log(logger, f"|Jahr: {year} | Knoten: {len(graph.nodes):>5} | Kanten: {len(graph.edges):>6} |")
            log(logger, f"--------------------------------------------------------------------")
    elif mode == 2: # E2.2 threshold nativ nicht umsetzbar da achsenordnung zu lang rechnet 17 min für graph 2000 dann abgebrochen, finde native communities für alle graphen heraus
        ds = {}
        for year in range(2000, 2025):
            graph = graphs[year]
            node_groups = clauset_newman_moore_communities(graph, 0)
            ds["Gesamtkanten"] = len(graph.edges())
            ds["Gesamtknoten"] = len(graph.nodes())
            ds["Native Communities"] = len(node_groups.keys())
            ds["kleinste Community"] = min(len(v) for v in node_groups.values())
            ds["größte Community"] = max(len(v) for v in node_groups.values())

            db.update("Gesamtkanten und -anteile tau = 8", year, **ds)
            
    elif mode == 3: # E2.5 tau=6, E2.6 tau = 8
        table = []
        for year in range(2000, 2025):
            ds = {}
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
            ds["Gesamtkanten"] = len(hiveplot.edges())
            ds["absoluter Anteil intra-axis Kanten"] = len(hiveplot.edges()) - inter_axis_count
            ds["absoluter Anteil inter-axis Kanten"] = inter_axis_count
            ds["relativer Anteil intra-axis Kanten"] = round(100 - inter_axis_count/len(hiveplot.edges())*100, 2)
            ds["relativer Anteil inter-axis Kanten"] = round(inter_axis_count/len(hiveplot.edges())*100, 2)
            db.update("Gesamtkanten und -anteile tau = 8", year, **ds)
            # table.append(f"|Jahr {year:>5} | {inter_axis_count:> 5} | {(inter_axis_count/len(hiveplot.edges())*100):>5.2f} | {len(native.keys()):>5} | {elapsed:>10.5f} |")
            print(f"Abgeschlossen: {year}")
        # for tab in table:
            # log(logger, tab)
            # log(logger, f"--------------------------------------------------------------------")
    elif mode == 4:
        pass

if __name__ == "__main__":
    data = DataCollector()
    # data.delete("Laufzeiten und Kreuzungszahlen für tau = 4")
    # print(data.get_data_set("Laufzeiten und Kreuzungszahlen für tau = 8, GD2000"))
    print(data.data_keys())
    # data.delete("Laufzeitenvergleich Bary/ILP")
    # data.get_data_set("GDJahre_gesamt_knoten_kanten_native")

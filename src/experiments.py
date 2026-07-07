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
            lines = [
                f"Datensatz der Experimente:",
                f"  Anzahl erfasster Datensätze: {len(self.data_sets.keys())}",
            ]
            return "\n".join(lines)

    def update(self, data_set: str, x_val: str | int | float = None, **kwargs: int | float | None) -> None:
        if data_set not in self.data_sets:
            self.data_sets[data_set] = {"x": []}

        dset = self.data_sets[data_set]

        if x_val in dset["x"]:
            index = dset["x"].index(x_val)
        else:
            dset["x"].append(x_val)
            index = len(dset["x"]) - 1

        for arg, value in kwargs.items():
            dset.setdefault(arg, [])
            while len(dset[arg]) < len(dset["x"]):
                dset[arg].append(None)
            dset[arg][index] = value

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

if __name__ == "__main__":
    data = DataCollector()
    print(data.data_sets["H2"])
    # data.delete("Parameterstudie")
    # data.delete("H1")
    # data.delete("H2")
    # data.delete("Laufzeitenvergleich Bary/ILP")
    # data.get_data_set("GDJahre_gesamt_knoten_kanten_native")
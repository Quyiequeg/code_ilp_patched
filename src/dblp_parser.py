import time
import pickle
from pathlib import Path
from lxml import etree
import networkx as nx

GD_TITLES = {
    "GD",
    "GD (1)",
    "GD (2)",
    "Graph Drawing",
    "Graph Drawing with Applications to Bioinformatics and Social Sciences" # große schnittmenge an autoren zu GD, deshalb mit aufgenommen
} # vorgefilterte Titel

YEAR_MIN = 2000
YEAR_MAX = 2024

class LocalDTDResolver(etree.Resolver):
    """Da es beim Parse trotz schneller Hardware zu Performanzproblemen kam mussten Einstellungen feingranular festgelegt werden. Unter anderem in dieser Klasse gebündelt die dtd-Datei zur Übersetzung von Umlauten und Sonderzeichen. Sie wird, falls vorhanden, von lokal bevorzugt.
    """
    def __init__(self, dtd_path: str):
        self.dtd_path = dtd_path

    def resolve(self, url, id, context):
        return self.resolve_filename(self.dtd_path, context)

def scan_booktitles(xml_path: str, dtd_path: str) -> set[str]:
    """Vorverarbeitung der dblp-xml Datei um nach booktitles zu filtern, da die xml-Datei neben Konferenzbänden auch andere wissenschaftliche Erzeugnisse wie Dissertationen oder Buchpublikationen enthält, die nichts mit der GD-Konferenz zu tun haben.
    """
    found = set()

    parser = etree.XMLParser(load_dtd=True, resolve_entities=True, no_network=True)
    parser.resolvers.add(LocalDTDResolver(dtd_path))
    etree.set_default_parser(parser)

    context = etree.iterparse(
        xml_path,
        events=("end",),
        tag="inproceedings",
        load_dtd=True,
        resolve_entities=False,
        recover=True
)

    start = time.time()
    count = 0

    for _, elem in context: # iterationsloop
        count += 1
        booktitle = elem.findtext("booktitle") or ""
        if "gd" in booktitle.lower() or "graph drawing" in booktitle.lower():
            found.add(booktitle)

        elem.clear() # wichtig, speicher freigeben!
        while elem.getprevious() is not None:
            del elem.getparent()[0]

        if count % 500_000 == 0: # statusmeldung nach 0.5mio
            elapsed = time.time() - start
            print(f"{count:,} Einträge verarbeitet – {elapsed:.1f}s vergangen")

        if count >= 4_000_000: # bei performance problemen kann hier debuggt werden
            print("Testlimit erreicht, breche ab.")
            break

    print(f"Fertig. {count:,} Einträge in {time.time() - start:.1f}s")
    return found

def parse_gd_coauthor_networks(xml_path: str, cache_path: str = None) -> dict[int, nx.Graph]:
    """
    Parst dblp und gibt Co-Autoren-Graphen pro Jahr zurück. Ausgabe erfolgt als pickle, um die Daten wiederverwendbar zu halten, ohne den Parse wieder durchzuführen. Lädt aus Cache falls vorhanden. 
    """
    if cache_path and Path(cache_path).exists():
        print("Cache gefunden, lade...")
        with open(cache_path, "rb") as file:
            return pickle.load(file)

    graphs: dict[int, nx.Graph] = {}

    context = etree.iterparse(
        xml_path,
        events=("end",),
        tag="inproceedings",
        load_dtd=True,
        resolve_entities=False,
        recover=True
    )

    start = time.time()
    count = 0
    gd_count = 0

    for _, elem in context: # loop und filter
        count += 1

        booktitle = elem.findtext("booktitle") or ""
        if booktitle not in GD_TITLES:
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
            continue

        year_text = elem.findtext("year")
        if not year_text or not (YEAR_MIN <= int(year_text) <= YEAR_MAX):
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
            continue

        year = int(year_text)
        authors = [a.text for a in elem.findall("author") if a.text]

        if year not in graphs:
            graphs[year] = nx.Graph()

        for i in range(len(authors)):
            for j in range(i + 1, len(authors)):
                graphs[year].add_edge(authors[i], authors[j])

        gd_count += 1
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

        if count % 500_000 == 0:
            elapsed = time.time() - start
            print(f"{count:,} Einträge verarbeitet – {elapsed:.1f}s – {gd_count} GD-Paper gefunden")

    elapsed = time.time() - start
    print(f"Fertig. {count:,} Einträge in {elapsed:.1f}s – {gd_count} GD-Paper, {len(graphs)} Jahre")

    if cache_path: # pickle speichern
        with open(cache_path, "wb") as file:
            pickle.dump(graphs, file)
        print(f"Cache gespeichert: {cache_path}")

    return graphs

def build_node_identity_maps(nodes: list[str]) -> tuple[dict[int, str], dict[str, int]]:
    """Funktion dient der Erstellung der Maps für die gleichnamigen Felder im Hiveplotlayout. Es werden KnotenIDs als Integer auf die Namen der Forschenden als Strings und vice versa gemappt. Dadurch wird es einerseits ermöglicht den Eingabegraphen in ein pipelinefreundliches Format zu übersetzen und
    gleichzeitig aus diesem am Ende die Label für den Renderer abzuleiten.
    """
    id_to_name = {}
    name_to_id = {}
    for i, node in enumerate(nodes, start=1): # knoten ids ab 1 beginnend
        id_to_name[i] = node
        name_to_id[node] = i
    return id_to_name, name_to_id

if __name__ == "__main__":
    pass   
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
    "Graph Drawing with Applications to Bioinformatics and Social Sciences"
} # vorgefilterte Titel

YEAR_MIN = 2000
YEAR_MAX = 2024

class LocalDTDResolver(etree.Resolver):
    def __init__(self, dtd_path: str):
        self.dtd_path = dtd_path

    def resolve(self, url, id, context):
        return self.resolve_filename(self.dtd_path, context)

def scan_booktitles(xml_path: str, dtd_path: str) -> set[str]:
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

    for _, elem in context:
        count += 1
        bt = elem.findtext("booktitle") or ""
        if "gd" in bt.lower() or "graph drawing" in bt.lower():
            found.add(bt)

        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

        if count % 500_000 == 0:
            elapsed = time.time() - start
            print(f"{count:,} Einträge verarbeitet – {elapsed:.1f}s vergangen")

        if count >= 4_000_000:
            print("Testlimit erreicht, breche ab.")
            break

    print(f"Fertig. {count:,} Einträge in {time.time() - start:.1f}s")
    return found

def parse_gd_coauthor_networks(xml_path: str, cache_path: str = None) -> dict[int, nx.Graph]:
    """
    Parst DBLP-XML und gibt Co-Autoren-Graphen pro Jahr zurück.
    Lädt aus Cache falls vorhanden.
    """
    if cache_path and Path(cache_path).exists():
        print("Cache gefunden, lade...")
        with open(cache_path, "rb") as f:
            return pickle.load(f)

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

    for _, elem in context:
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

    if cache_path:
        with open(cache_path, "wb") as file:
            pickle.dump(graphs, file)
        print(f"Cache gespeichert: {cache_path}")

    return graphs

def build_node_identity_maps(nodes):
    id_to_name = {}
    name_to_id = {}
    for i, node in enumerate(nodes, start=1): # knoten ids ab 1 beginnend
        id_to_name[i] = node
        name_to_id[node] = i
    return id_to_name, name_to_id

if __name__ == "__main__":
    xml_path   = r"E:\Programming Workspace\Python\BA-Sauerteig\dblp_daten_gesamt\dblp-2025-05-02.xml"
    cache_path = r"E:\Programming Workspace\Python\BA-Sauerteig\dblp_daten_gesamt\gd_graphs.pkl"

    # graphs = parse_gd_coauthor_networks(xml_path, cache_path)

    # for year in sorted(graphs.keys()):
    #     G = graphs[year]
        # print(f"{year}: {G.number_of_nodes()} Autoren, {G.number_of_edges()} Co-Autorenschaft-Kanten")
    with open(cache_path, "rb") as f:
        graphs = pickle.load(f)
    G = graphs[2000]
    print(G)
    print(G.edges())
    print(G.nodes())
    
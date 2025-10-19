import argparse
import sys
import os
import networkx as nx

# ensure the package root is importable when running from the repo root
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.graphs import nx_to_pyvis


def build_sample_graph() -> nx.Graph:
    """Create a simple sample graph (path) with labels."""
    G = nx.path_graph(5)
    for n in G.nodes:
        G.nodes[n]["label"] = f"Node {n}"
    return G


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize a sample graph with pyvis")
    parser.add_argument("-o", "--output", default="graph.html", help="Output HTML file")
    parser.add_argument("--physics", action="store_true", help="Enable physics layout")
    parser.add_argument("--width", default="100%", help="Canvas width (CSS)")
    parser.add_argument("--height", default="600px", help="Canvas height (CSS)")
    args = parser.parse_args()

    G = build_sample_graph()
    net = nx_to_pyvis(G, height=args.height, width=args.width, physics=args.physics)
    net.show(args.output)


if __name__ == "__main__":
    main()

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from flexitext import flexitext
from hiveplotlib import HivePlot
from hiveplotlib.converters import networkx_to_nodes_edges

def sample_graph():
    G = nx.complete_multipartite_graph(10, 10, 10)
    return G

# def cost_axis_ordering(nodes, edges):

def node_span(node_0, node_1): #span(a_i, a_j) function
    

G = sample_graph()
nodes, edges = networkx_to_nodes_edges(G)

# split node IDs into separate lists based on which "subset" they're in
partition_variable = nodes.create_partition_variable(
    data_column="subset",
    cutoffs=3,  # split into our 3 groups
    labels=["Group 1", "Group 2", "Group 3"],
)

# not concerned with on-axis patterns, place nodes on axes randomly
rng = np.random.default_rng(0)
nodes.data["val"] = rng.uniform(size=len(nodes.data))
hp = HivePlot(
    nodes=nodes,
    edges=edges,
    partition_variable=partition_variable,
    sorting_variables="val",
    repeat_axes=True,
)
fig, ax = hp.plot(color="C0")
ax.set_title(
    "By definition, a multipartite graph has no within-group connections",
    y=1.1,
    size=20,
    x=0,
    ha="left",
)
plt.show()
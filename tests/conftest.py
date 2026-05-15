#hilfsfunktion für tests, damit nicht jedesmal der gleiche graph erstellt werden muss
import pytest
import networkx as nx

@pytest.fixture
def sample_graph():
    return nx.complete_multipartite_graph(10, 10, 10)

@pytest.fixture
def caveman_graph():
    return nx.caveman_graph(4, 10)
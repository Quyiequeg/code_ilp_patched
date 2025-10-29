import argparse
import sys
import os
import networkx as nx
from pyvis.network import Network
from PyQt5 import QtWidgets
# import pyqtgraph as pg
from PyQt6 import QtCore, QtGui, QtWidgets
# ensure local gui module is importable when running main.py as a script
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
from gui import Ui_MainWindow

# ensure the package root is importable when running from the repo root
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def main():
    # G = nx.Graph()
    # G.add_nodes_from([1, 2, 3])
    # G.add_edges_from([(1, 2), (2, 3)])
    # print(list(G.nodes))
    # nt = Network(height='500px', width='500px')
    # nt.from_nx(G)
    # nt.show('G.html', notebook=False)
    print("Lade GUI.")
    # app = QtWidgets.QApplication(sys.argv)
    # MainWindow = QtWidgets.QMainWindow()
    # ui = Ui_MainWindow()
    # ui.setupUi(MainWindow)
    # print("Laden abgeschlossen.")
    # MainWindow.show()
    # sys.exit(app.exec())
    
    
    
if __name__ == "__main__":
    main()

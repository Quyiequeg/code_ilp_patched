import os
import sys

PROJECT_ROOT = os.path.abspath("../..")
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SRC_DIR)

project = 'BA-Sauerteig'
author = 'Patrick Sauerteig'
release = '1.0'
language = 'de'

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]
autodoc_default_options = {'members': True, 'undoc-members': False, 'show-inheritance': True}
html_theme = 'sphinx_rtd_theme'
latex_elements = {
    'papersize': 'a4paper',
    "preamble": r"""\let\cleardoublepage\clearpage""",
}
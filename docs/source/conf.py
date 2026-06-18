import os, sys
sys.path.insert(0, r'E:\Programming Workspace\Python\BA-Sauerteig\src')

project = 'BA-Sauerteig'
author = 'Quyiequeg'
release = '1.0'
language = 'de'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon', 'sphinx.ext.viewcode']
autodoc_default_options = {'members': True, 'undoc-members': False, 'show-inheritance': True}
html_theme = 'sphinx_rtd_theme'
latex_elements = {'papersize': 'a4paper'}
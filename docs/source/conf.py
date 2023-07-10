# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


# -- Path setup --------------------------------------------------------------

# If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys
import harmonize_wq
#from importlib.metadata import version

sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("../.."))


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'harmonize_wq'
copyright = '2023, US Environmental Protection Agency'
author = 'Justin Bousquin (US Environmental Protection Agency)'

# ToDO:single source version
#version = "0.3.0"
#release = version(project)
release = harmonize_wq.__version__
version = '.'.join(release.split('.')[:2])


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
]

autosummary_generate = True  # Turn on sphinx.ext.autosummary
html_show_sourcelink = False  # Remove 'view source code' from top of page (for html, not python)

templates_path = ['_templates']
exclude_patterns = ['_build', '_templates']


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']

# Readthedocs theme (may be useful for actions)
# on_rtd is whether on readthedocs.org, this line of code grabbed from docs.readthedocs.org...
#on_rtd = os.environ.get("READTHEDOCS", None) == "True"
#if not on_rtd:  # only import and set the theme if we're building docs locally
#    import sphinx_rtd_theme
#    html_theme = "sphinx_rtd_theme"
#    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
#html_css_files = ["readthedocs-custom.css"] # Override some CSS settings

# -- Options for Napolean output ---------------------------------------------
napolean_include_private_with_doc = False
napolean_include_special_with_doc = False
napoleon_include_init_with_doc = False
napolean_use_param = True
napolean_use_rtype = True
napolean_reprocess_types = True
napoleon_google_docstring = False
napoleon_numpy_docstring = True

# -- Options for sphinx-contrib\apidoc -----------------------------------------------------
# NOT currently using apidoc
apidoc_separate_modules = True
apidoc_module_dir = "../harmonize_wq"
apidoc_excluded_paths = ["tests"]
apidoc_module_first = True

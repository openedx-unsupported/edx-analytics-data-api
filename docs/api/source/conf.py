import os
import sys
import django

from path import Path

import edx_theme

# Add any paths that contain templates here, relative to this directory.
# templates_path.append('source/_templates')

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path.append('source/_static')

master_doc = 'index'
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
root = Path('../../..').abspath()
sys.path.insert(0, root)
sys.path.append(root / "analytics_data_api/v0/views")
sys.path.append('.')

# -- General configuration -----------------------------------------------------

#  django configuration  - careful here
os.environ['DJANGO_SETTINGS_MODULE'] = 'analyticsdataserver.settings.local'
django.setup()

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'edx_theme',
    'sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx',
    'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.imgmath',
    'sphinx.ext.mathjax', 'sphinx.ext.viewcode']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['build', 'links.rst']

project = 'Open edX Data Analytics API'
copyright = '2021, edX'

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'edx_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = [edx_theme.get_html_theme_path()]

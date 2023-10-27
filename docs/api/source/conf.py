import os
import sys

import django
from path import Path

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
    'sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx',
    'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.imgmath',
    'sphinx.ext.mathjax', 'sphinx.ext.viewcode']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['build', 'links.rst']

project = 'Open edX Data Analytics API'
copyright = '2021, Axim Collaborative, Inc'

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_book_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
 "repository_url": "https://github.com/openedx/edx-analytics-data-api",
 "repository_branch": "master",
 "path_to_docs": "docs/api/source",
 "home_page_in_toc": True,
 "use_repository_button": True,
 "use_issues_button": True,
 "use_edit_page_button": True,
 # False was the default value for navigation_with_keys. However, in version 0.14.2 of pydata-sphinx-theme, this default
 # was removed and a warning was added that would be emitted whenever navigation_with_keys was not set. Because of the
 # "SPHINXOPTS = -W" configuration in tox.ini, all warnings are promoted to an error. Therefore, it's necesary to set
 # this value. I have set it to the default value explicitly. Please see the following GitHub comments for context.
 # https://github.com/pydata/pydata-sphinx-theme/issues/1539
 # https://github.com/pydata/pydata-sphinx-theme/issues/987#issuecomment-1277214209
 "navigation_with_keys": False,
 # Please don't change unless you know what you're doing.
 "extra_footer": """
        <a rel="license" href="https://creativecommons.org/licenses/by-sa/4.0/">
            <img
                alt="Creative Commons License"
                style="border-width:0"
                src="https://i.creativecommons.org/l/by-sa/4.0/80x15.png"/>
        </a>
        <br>
        These works by
            <a
                xmlns:cc="https://creativecommons.org/ns#"
                href="https://openedx.org"
                property="cc:attributionName"
                rel="cc:attributionURL"
            >Axim Collaborative, Inc</a>
        are licensed under a
            <a
                rel="license"
                href="https://creativecommons.org/licenses/by-sa/4.0/"
            >Creative Commons Attribution-ShareAlike 4.0 International License</a>.
    """
}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = []

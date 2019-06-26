import sphinx_fontawesome
import sys, os, datetime


html_theme = "sphinx_rtd_theme"
html_theme_options = {
    'canonical_url': '',
    'analytics_id': 'UA-XXXXXXX-1',  #  Provided by Google in your dashboard
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
#    'vcs_pageview_mode': '',
    'style_nav_header_background': '#010101',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}
html_logo = './images/waterbear-cloud-url-head-1.png'
html_static_path = ['_static',]


def setup(app):
    app.add_stylesheet('css/aim.css')


# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx_fontawesome'
    ]

# Looks for aim.model's objects
intersphinx_mapping = {
#    'aim.models':
#    ('https://github.com/waterbear-cloud/aim.models', None),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'AIM'
thisyear = datetime.datetime.now().year
copyright = '2018-%s, Waterbear Cloud' % thisyear

# The short X.Y version.
with open('../version.txt') as f:
    version = f.read()

# The full version, including alpha/beta/rc tags.
release = version

today_fmt = '%B %d, %Y'
exclude_patterns = ['_themes/README.rst',]


# Options for HTML output
# -----------------------

html_favicon = '_static/favicon.ico'

# If not '', a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = False


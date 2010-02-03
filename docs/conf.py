# -*- coding: utf-8 -*-
import sys, os, shutil
import mpeg1audio

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.todo',
              'sphinx.ext.autosummary']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = mpeg1audio.__description__
copyright = mpeg1audio.__copyright__
version = mpeg1audio.__version__
release = mpeg1audio.__release__
exclude_trees = ['_build', '_templates']
pygments_style = 'sphinx'

# HTML ---------------------------------------

html_theme = 'default'
html_static_path = ['_static']
htmlhelp_basename = 'MPEG-1AudioPythonpackagedoc'

# Autodoc ------------------------------------

# autoclass_content = "both"
autodoc_member_order = "groupwise"
autosummary_generate = True

# Todo ------------------------------------

todo_include_todos = False

if os.path.exists("api"):
    print "Deleting old api..."
    shutil.rmtree("api")

if os.path.exists("_build"):
    print "Deleting old build..."
    shutil.rmtree("_build")

def non_init_skip(app, what, name, obj, skip, options):
    """
    Otherwise normally, but don't skip init. 
    """
    if skip and name == '__init__':
        return False
    return skip

def setup(app):
    app.connect('autodoc-skip-member', non_init_skip)

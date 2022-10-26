"""
pychecker — Never use print() to debug again

License: MIT
"""


from . import *
from .pychecker import *
from . import __version__
from .builtins import install, uninstall

globals().update(dict((k, v) for k, v in __version__.__dict__.items()))

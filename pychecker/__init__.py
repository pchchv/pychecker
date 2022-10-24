"""
pychecker — Never use print() to debug again

License: MIT
"""


from . import __version__


globals().update(dict((k, v) for k, v in __version__.__dict__.items()))

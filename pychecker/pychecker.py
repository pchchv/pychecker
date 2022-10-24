"""
"""


import sys
from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import PythonLexer, Python3Lexer
from .coloring import SolarizedDark

PYTHON2 = (sys.version_info[0] == 2)


def bind_static_variable(name, value):
    """
    Creating a decorator
    """
    def decorator(obj):
        setattr(obj, name, value)
        return obj
    return decorator


@bind_static_variable('formatter', Terminal256Formatter(style=SolarizedDark))
@bind_static_variable('lexer', PythonLexer(ensurenl=False) if PYTHON2 else Python3Lexer(ensurenl=False))
def colorize(string):
    """
    Implement the representation of the class SolarizedDark
    """
    self = colorize
    return highlight(string, self.lexer, self.formatter)

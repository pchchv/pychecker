"""
"""


import ast
import sys
from contextlib import contextmanager
import colorama
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


@contextmanager
def support_terminal_colors_in_windows():
    """
    Filter and replace ANSI escape sequences on Windows with equivalent Win32
    API calls. This code does nothing on non-Windows systems.
    """
    colorama.init()
    yield
    colorama.deinit()


def stderr_print(*args):
    """
    Prints std error
    """
    print(*args, file=sys.stderr)


def is_literal(string):
    """
    Checks if the string consists of literals
    """
    try:
        ast.literal_eval(string)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False
    return True


def colorized_stderr_print(string):
    """
    Colors the std error print
    """
    colored = colorize(string)
    with support_terminal_colors_in_windows():
        stderr_print(colored)


class NoAvailableSourceError(OSError):
    """
    Occurs if the source code needed for parsing and analysis cannot be found or accessed.
    This can occur when:
      - check() is called inside a REPL or interactive shell,
        for example from the command line (CLI) or with the python -i command.
      - The source code is corrupted and/or packaged, for example with PyInstaller.
      - The underlying source code has changed at runtime.
    """
    infoMessage = (
        'Failed to access the underlying source code for analysis.'
        'Is check() called in a REPL (e.g. from the command line),'
        'in a frozen application (e.g. packaged with PyInstaller),'
        'or has the underlying source code changed at runtime?')

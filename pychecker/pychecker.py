"""
"""


import ast
import sys
from textwrap import dedent
from contextlib import contextmanager
import functools
import pprint
import executing
import colorama
from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import PythonLexer, Python3Lexer
from .coloring import SolarizedDark


PYTHON2 = (sys.version_info[0] == 2)
DEFAULT_ARG_TO_STRING_FUNCTION = pprint.pformat


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


class Source(executing.Source):
    """
    Processes the source code of the file and its associated metadata.
    """

    def get_text_with_indentation(self, node):
        """
        Gets indented text
        """
        result = self.asttokens().get_text(node)
        if '\n' in result:
            result = ' ' * node.first_token.start[1] + result
            result = dedent(result)
        result = result.strip()
        return result


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


def call_or_value(obj):
    """
    If the object is a callable — calls it
    If not — returns its value
    """
    return obj() if callable(obj) else obj


def prefix_lines_after_first(prefix, string):
    """
    Adds prefix lines
    """
    lines = string.splitlines(True)
    for i in range(1, len(lines)):
        lines[i] = prefix + lines[i]
    return ''.join(lines)


def indented_lines(prefix, string):
    """
    Adds indents
    """
    lines = string.splitlines()
    return [prefix + lines[0]] + [' ' * len(prefix) + line for line in lines[1:]]


def format_pair(prefix, arg, value):
    """
    Formatting argument-value pairs
    """
    arg_lines = indented_lines(prefix, arg)
    value_prefix = arg_lines[-1] + ': '
    looks_like_a_string = value[0] + value[-1] in ["''", '""']
    if looks_like_a_string:  # Align the start of multiline strings
        value = prefix_lines_after_first(' ', value)
    value_lines = indented_lines(value_prefix, value)
    lines = arg_lines[:-1] + value_lines
    return '\n'.join(lines)


def single_dispatch(func):
    """
    Converting a function into a general function
    """
    if "singledispatch" not in dir(functools):
        def unsupport_py2(*args, **kwargs):
            raise NotImplementedError(
                "functools.singledispatch is missing in " + sys.version
            )
        func.register = func.unregister = unsupport_py2
        return func
    func = functools.singledispatch(func)
    closure = dict(zip(func.register.__code__.co_freevars,
                   func.register.__closure__))
    registry = closure['registry'].cell_contents
    dispatch_cache = closure['dispatch_cache'].cell_contents

    def unregister(cls):
        del registry[cls]
        dispatch_cache.clear()
    func.unregister = unregister
    return func


@single_dispatch
def convert_argument_to_string(obj):
    """
    Converts object to a string
    """
    string = DEFAULT_ARG_TO_STRING_FUNCTION(obj)
    string = string.replace('\\n', '\n')
    return string

"""
pychecker — Never use print() to debug again

License: MIT
"""


import ast
import sys
from textwrap import dedent
from datetime import datetime
from contextlib import contextmanager
from os.path import basename, realpath
import functools
import pprint
import inspect
import executing
import colorama
from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import PythonLexer, Python3Lexer
from .coloring import SolarizedDark


PYTHON2 = (sys.version_info[0] == 2)
DEFAULT_PREFIX = 'check| '
DEFAULT_LINE_WRAP_WIDTH = 70  # Characters.
DEFAULT_CONTEXT_DELIMITER = '- '
DEFAULT_ARG_TO_STRING_FUNCTION = pprint.pformat
_absent = object()


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


DEFAULT_OUTPUT_FUNCTION = colorized_stderr_print


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
def argument_to_string(obj):
    """
    Converts object to a string
    """
    string = DEFAULT_ARG_TO_STRING_FUNCTION(obj)
    string = string.replace('\\n', '\n')
    return string


class PyCheckDebugger:
    """
    General class

    Called with the check()
    """

    _pairDelimiter = ', '  # Used by the tests in tests/.
    lineWrapWidth = DEFAULT_LINE_WRAP_WIDTH
    context_delimiter = DEFAULT_CONTEXT_DELIMITER

    def __init__(self, prefix=DEFAULT_PREFIX,
                 output_function=DEFAULT_OUTPUT_FUNCTION,
                 arg_to_string_function=argument_to_string, include_context=False,
                 context_abs_path=False):
        self.enabled = True
        self.prefix = prefix
        self.include_context = include_context
        self.output_function = output_function
        self.arg_to_string_function = arg_to_string_function
        self.context_abs_path = context_abs_path

    def __call__(self, *args):
        if self.enabled:
            call_frame = inspect.currentframe().f_back
            try:
                out = self._format(call_frame, *args)
            except NoAvailableSourceError as err:
                prefix = call_or_value(self.prefix)
                out = prefix + 'Error: ' + err.infoMessage
            self.output_function(out)
        if not args:
            passthrough = None
        elif len(args) == 1:
            passthrough = args[0]
        else:
            passthrough = args
        return passthrough

    def format(self, *args):
        """
        Formats the received arguments
        """
        call_frame = inspect.currentframe().f_back
        out = self._format(call_frame, *args)
        return out

    def _format(self, call_frame, *args):
        prefix = call_or_value(self.prefix)

        call_node = Source.executing(call_frame).node
        if call_node is None:
            raise NoAvailableSourceError()
        context = self._format_context(call_frame, call_node)
        if not args:
            time = self._format_time()
            out = prefix + context + time
        else:
            if not self.include_context:
                context = ''
            out = self._format_args(
                call_frame, call_node, prefix, context, args)
        return out

    def _format_args(self, call_frame, call_node, prefix, context, args):
        source = Source.for_frame(call_frame)
        sanitized_arg_strs = [
            source.get_text_with_indentation(arg)
            for arg in call_node.args]
        pairs = list(zip(sanitized_arg_strs, args))
        out = self._construct_argument_output(prefix, context, pairs)
        return out

    def _construct_argument_output(self, prefix, context, pairs):
        def arg_prefix(arg):
            return '%s: ' % arg
        pairs = [(arg, self.arg_to_string_function(val)) for arg, val in pairs]
        # For cleaner output, if <arg> is a literal, such as 3, 'string', b'bytes, etc.
        # output only the value, not the argument and value,
        # since the argument and value will be identical or nearly identical.
        # For example: check('hello')
        #
        #   check| 'hello',
        #
        # instead of
        #
        #   check| "hello": 'hello'.
        #
        pair_strs = [
            val if is_literal(arg) else (arg_prefix(arg) + val)
            for arg, val in pairs]
        all_args_on_one_line = self._pairDelimiter.join(pair_strs)
        multiline_args = len(all_args_on_one_line.splitlines()) > 1
        context_delimiter = self.context_delimiter if context else ''
        all_pairs = prefix + context + context_delimiter + all_args_on_one_line
        first_line_too_long = len(all_pairs.splitlines()[
                                  0]) > self.lineWrapWidth
        if multiline_args or first_line_too_long:
            if context:
                lines = [prefix + context] + [
                    format_pair(len(prefix) * ' ', arg, value)
                    for arg, value in pairs
                ]
            else:
                arg_lines = [
                    format_pair('', arg, value)
                    for arg, value in pairs
                ]
                lines = indented_lines(prefix, '\n'.join(arg_lines))
        else:
            lines = [prefix + context +
                     context_delimiter + all_args_on_one_line]
        return '\n'.join(lines)

    def _format_context(self, call_frame, call_node):
        filename, line_number, parent_function = self._get_context(
            call_frame, call_node)
        if parent_function != '<module>':
            parent_function = '%s()' % parent_function
        context = '%s:%s in %s' % (filename, line_number, parent_function)
        return context

    def _format_time(self):
        now = datetime.now()
        formatted = now.strftime('%H:%M:%S.%f')[:-3]
        return ' at %s' % formatted

    def _get_context(self, call_frame, call_node):
        line_number = call_node.lineno
        frame_info = inspect.getframeinfo(call_frame)
        parent_function = frame_info.function

        filepath = (realpath if self.context_abs_path else basename)(
            frame_info.filename)
        return filepath, line_number, parent_function

    def enable(self):
        """
        Enables the class
        """
        self.enabled = True

    def disable(self):
        """
        Disnables the class
        """
        self.enabled = False

    def configure_output(self, prefix=_absent, output_function=_absent,
                         arg_to_string_function=_absent, include_context=_absent,
                         context_abs_path=_absent):
        """
        Configures the output
        """
        no_parameter_provided = all(
            v is _absent for k, v in locals().items() if k != 'self')
        if no_parameter_provided:
            raise TypeError('configure_output() missing at least one argument')
        if prefix is not _absent:
            self.prefix = prefix
        if output_function is not _absent:
            self.output_function = output_function
        if arg_to_string_function is not _absent:
            self.arg_to_string_function = arg_to_string_function
        if include_context is not _absent:
            self.include_context = include_context
        if context_abs_path is not _absent:
            self.context_abs_path = context_abs_path


check = PyCheckDebugger()

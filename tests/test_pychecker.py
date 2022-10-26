"""
pychecker — Never use print() to debug again

License: MIT
"""

import sys
import unittest
import functools
import pychecker
from contextlib import contextmanager
from os.path import basename, splitext, realpath
from pychecker import check, argument_to_string, stderr_print, NoAvailableSourceError

try:  # Python 2.x.
    from StringIO import StringIO
except ImportError:  # Python 3.x.
    from io import StringIO


TEST_PAIR_DELIMITER = '| '
MY_FILENAME = basename(__file__)
MY_FILEPATH = realpath(__file__)

a = 1
b = 2
c = 3


def noop(*args, **kwargs):
    return


def has_ansi_escape_codes(s):
    return '\x1b[' in s


class FakeTeletypeBuffer(StringIO):
    """
    Extend StringIO to act like a TTY so ANSI control codes aren't stripped
    when wrapped with colorama's wrap_stream().
    """

    def isatty(self):
        return True


@contextmanager
def disable_coloring():
    original_output_function = check.output_function
    check.configureOutput(outputFunction=stderr_print)
    yield
    check.configureOutput(outputFunction=original_output_function)


@contextmanager
def configure_pychecker_output(prefix=None, outputFunction=None,
                               argToStringFunction=None, includeContext=None,
                               contextAbsPath=None):
    old_prefix = check.prefix
    old_output_function = check.outputFunction
    old_arg_to_string_function = check.arg_to_string_function
    old_include_context = check.include_context
    old_context_abs_path = check.context_abs_path
    if prefix:
        check.configure_output(prefix=prefix)
    if outputFunction:
        check.configure_output(outputFunction=outputFunction)
    if argToStringFunction:
        check.configure_output(argToStringFunction=argToStringFunction)
    if includeContext:
        check.configure_output(includeContext=includeContext)
    if contextAbsPath:
        check.configure_output(contextAbsPath=contextAbsPath)
    yield
    check.configure_output(
        old_prefix, old_output_function, old_arg_to_string_function,
        old_include_context, old_context_abs_path)


@contextmanager
def capture_standard_streams():
    real_stdout = sys.stdout
    real_stderr = sys.stderr
    new_stdout = FakeTeletypeBuffer()
    new_stderr = FakeTeletypeBuffer()
    try:
        sys.stdout = new_stdout
        sys.stderr = new_stderr
        yield new_stdout, new_stderr
    finally:
        sys.stdout = real_stdout
        sys.stderr = real_stderr


def strip_prefix(line):
    if line.startswith(check.prefix):
        line = line.strip()[len(check.prefix):]
    return line


def line_is_context_and_time(line):
    line = strip_prefix(line)
    context, time = line.split(' at ')
    return (
        line_is_context(context) and
        len(time.split(':')) == 3 and
        len(time.split('.')) == 2)


def line_is_context(line):
    line = strip_prefix(line)
    source_location, function = line.split(' in ')
    filename, line_number = source_location.split(':')
    name, ext = splitext(filename)
    return (
        int(line_number) > 0 and
        ext in ['.py', '.pyc', '.pyo'] and
        name == splitext(MY_FILENAME)[0] and
        (function == '<module>' or function.endswith('()')))


def line_is_abs_path_context(line):
    line = strip_prefix(line)
    source_location, function = line.split(' in ')
    filepath, line_number = source_location.split(':')
    path, ext = splitext(filepath)
    return (
        int(line_number) > 0 and
        ext in ['.py', '.pyc', '.pyo'] and
        path == splitext(MY_FILEPATH)[0] and
        (function == '<module>' or function.endswith('()')))


def line_after_context(line, prefix):
    if line.startswith(prefix):
        line = line[len(prefix):]
    toks = line.split(' in ', 1)
    if len(toks) == 2:
        rest = toks[1].split(' ')
        line = ' '.join(rest[1:])
    return line


def parse_output_into_pairs(out, err, assertNumLines,
                            prefix=pychecker.DEFAULT_PREFIX):
    if isinstance(out, StringIO):
        out = out.getvalue()
    if isinstance(err, StringIO):
        err = err.getvalue()
    assert not out
    lines = err.splitlines()
    if assertNumLines:
        assert len(lines) == assertNumLines
    line_pairs = []
    for line in lines:
        line = line_after_context(line, prefix)
        if not line:
            line_pairs.append([])
            continue
        pair_strs = line.split(TEST_PAIR_DELIMITER)
        pairs = [tuple(s.split(':', 1)) for s in pair_strs]
        # Indented line of a multiline value
        if len(pairs[0]) == 1 and line.startswith(' '):
            arg, value = line_pairs[-1][-1]
            looks_like_a_string = value[0] in ["'", '"']
            prefix = (arg + ': ') + (' ' if looks_like_a_string else '')
            dedented = line[len(check.prefix) + len(prefix):]
            line_pairs[-1][-1] = (arg, value + '\n' + dedented)
        else:
            items = [
                (p[0].strip(), None) if len(p) == 1  # A value, like check(3)
                else (p[0].strip(), p[1].strip())  # A variable, like check(a)
                for p in pairs]
            line_pairs.append(items)
    return line_pairs


def foo():
    return 'foo'


class TestPyChecker(unittest.TestCase):
    def setUp(self):
        check._pair_delimiter = TEST_PAIR_DELIMITER

    def testMetadata(self):
        def is_non_empty_string(s):
            return isinstance(s, str) and s
        assert is_non_empty_string(pychecker.__title__)
        assert is_non_empty_string(pychecker.__version__)
        assert is_non_empty_string(pychecker.__license__)
        assert is_non_empty_string(pychecker.__author__)
        assert is_non_empty_string(pychecker.__contact__)
        assert is_non_empty_string(pychecker.__description__)
        assert is_non_empty_string(pychecker.__url__)

    def testWithoutArgs(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            check()
        assert line_is_context_and_time(err.getvalue())

    def testAsArgument(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            noop(check(a), check(b))
        pairs = parse_output_into_pairs(out, err, 2)
        assert pairs[0][0] == ('a', '1') and pairs[1][0] == ('b', '2')
        with disable_coloring(), capture_standard_streams() as (out, err):
            dic = {1: check(a)}  # noqa
            lst = [check(b), check()]  # noqa
        pairs = parse_output_into_pairs(out, err, 3)
        assert pairs[0][0] == ('a', '1')
        assert pairs[1][0] == ('b', '2')
        assert line_is_context_and_time(err.getvalue().splitlines()[-1])

    def testSingleArgument(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(a)
        assert parse_output_into_pairs(out, err, 1)[0][0] == ('a', '1')

    def testMultipleArguments(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(a, b)
        pairs = parse_output_into_pairs(out, err, 1)[0]
        assert pairs == [('a', '1'), ('b', '2')]

    def testNestedMultiline(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(
            )
        assert line_is_context_and_time(err.getvalue())
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(a,
                  'foo')
        pairs = parse_output_into_pairs(out, err, 1)[0]
        assert pairs == [('a', '1'), ("'foo'", None)]
        with disable_coloring(), capture_standard_streams() as (out, err):
            noop(noop(noop({1: check(
                noop())})))
        assert parse_output_into_pairs(out, err, 1)[0][0] == ('noop()', 'None')

    def testExpressionArguments(self):
        class AttrClass:
            attr = 'yep'
        d = {'d': {1: 'one'}, 'k': AttrClass}
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(d['d'][1])
        pair = parse_output_into_pairs(out, err, 1)[0][0]
        assert pair == ("d['d'][1]", "'one'")
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(d['k'].attr)
        pair = parse_output_into_pairs(out, err, 1)[0][0]
        assert pair == ("d['k'].attr", "'yep'")

    def testMultipleCallsOnSameLine(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(a)
            check(b, c)  # noqa
        pairs = parse_output_into_pairs(out, err, 2)
        assert pairs[0][0] == ('a', '1')
        assert pairs[1] == [('b', '2'), ('c', '3')]

    def testCallSurroundedByExpressions(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            noop()
            check(a)
            noop()  # noqa
        assert parse_output_into_pairs(out, err, 1)[0][0] == ('a', '1')

    def testComments(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            """Comment."""
            check()  # noqa
        assert line_is_context_and_time(err.getvalue())

    def testMethodArguments(self):
        class Foo:
            pass
        f = Foo()
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(foo())
        assert parse_output_into_pairs(
            out, err, 1)[0][0] == ('f.foo()', "'foo'")

    def testComplicated(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            noop()
            check()
            noop()
            check(a,  # noqa
               b, noop.__class__.__name__,  # noqa
               noop())
            noop()  # noqa
        pairs = parse_output_into_pairs(out, err, 2)
        assert line_is_context_and_time(err.getvalue().splitlines()[0])
        assert pairs[1] == [
            ('a', '1'), ('b', '2'), ('noop.__class__.__name__', "'function'"),
            ('noop ()', 'None')]

    def testReturnValue(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            assert check() is None
            assert check(1) == 1
            assert check(1, 2, 3) == (1, 2, 3)

    def testDifferentName(self):
        from pychecker import check as foo
        with disable_coloring(), capture_standard_streams() as (out, err):
            foo()
        assert line_is_context_and_time(err.getvalue())
        newname = foo
        with disable_coloring(), capture_standard_streams() as (out, err):
            newname(a)
        pair = parse_output_into_pairs(out, err, 1)[0][0]
        assert pair == ('a', '1')

    def testPrefixConfiguration(self):
        prefix = 'lolsup '
        with configure_pychecker_output(prefix, stderr_print):
            with disable_coloring(), capture_standard_streams() as (out, err):
                check(a)
        pair = parse_output_into_pairs(out, err, 1, prefix=prefix)[0][0]
        assert pair == ('a', '1')

        def prefix_function():
            return 'lolsup '

        with configure_pychecker_output(prefix=prefix_function):
            with disable_coloring(), capture_standard_streams() as (out, err):
                check(b)
        pair = parse_output_into_pairs(
            out, err, 1, prefix=prefix_function())[0][0]
        assert pair == ('b', '2')

    def testOutputFunction(self):
        lst = []

        def append_to(s):
            lst.append(s)

        with configure_pychecker_output(check.prefix, append_to):
            with capture_standard_streams() as (out, err):
                check(a)
        assert not out.getvalue() and not err.getvalue()
        with configure_pychecker_output(outputFunction=append_to):
            with capture_standard_streams() as (out, err):
                check(b)
        assert not out.getvalue() and not err.getvalue()
        pairs = parse_output_into_pairs(out, '\n'.join(lst), 2)
        assert pairs == [[('a', '1')], [('b', '2')]]

    def testEnableDisable(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            assert check(a) == 1
            assert check.enabled
            check.disable()
            assert not check.enabled
            assert check(b) == 2
            check.enable()
            assert check.enabled
            assert check(c) == 3
        pairs = parse_output_into_pairs(out, err, 2)
        assert pairs == [[('a', '1')], [('c', '3')]]

    def testArgToStringFunction(self):
        def hello(obj):
            return 'zwei'

        with configure_pychecker_output(argToStringFunction=hello):
            with disable_coloring(), capture_standard_streams() as (out, err):
                eins = 'ein'
                check(eins)
        pair = parse_output_into_pairs(out, err, 1)[0][0]
        assert pair == ('eins', 'zwei')

    def testSingledispatchArgument_to_string(self):
        def argument_to_string_tuple(obj):
            return "Dispatching tuple!"
        # Unsupported Python2
        if "singledispatch" not in dir(functools):
            for attr in ("register", "unregister"):
                with self.assertRaises(NotImplementedError):
                    getattr(argument_to_string, attr)(
                        tuple, argument_to_string_tuple
                    )
            return
        # Prepare input and output
        x = (1, 2)
        default_output = check.format(x)
        # Register
        argument_to_string.register(tuple, argument_to_string_tuple)
        assert tuple in argument_to_string.registry
        assert str.endswith(check.format(x), argument_to_string_tuple(x))
        # Unregister
        argument_to_string.unregister(tuple)
        assert tuple not in argument_to_string.registry
        assert check.format(x) == default_output

    def testSingleArgumentLongLineNotWrapped(self):
        # A single long line with one argument is not line wrapped
        long_str = '*' * (check.lineWrapWidth + 1)
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(long_str)
        pair = parse_output_into_pairs(out, err, 1)[0][0]
        assert len(err.getvalue()) > check.lineWrapWidth
        assert pair == ('long_str', check.argToStringFunction(long_str))

    def testMultipleArgumentsLongLineWrapped(self):
        # A single long line with multiple variables is line wrapped
        val = '*' * int(check.lineWrapWidth / 4)
        val_str = check.argToStringFunction(val)
        v1 = v2 = v3 = v4 = val
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(v1, v2, v3, v4)
        pairs = parse_output_into_pairs(out, err, 4)
        assert pairs == [[(k, val_str)] for k in ['v1', 'v2', 'v3', 'v4']]
        lines = err.getvalue().splitlines()
        assert (
            lines[0].startswith(check.prefix) and
            lines[1].startswith(' ' * len(check.prefix)) and
            lines[2].startswith(' ' * len(check.prefix)) and
            lines[3].startswith(' ' * len(check.prefix)))

    def testMultilineValueWrapped(self):
        # Multiline values are line wrapped
        multiline_str = 'line1\nline2'
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(multiline_str)
        pair = parse_output_into_pairs(out, err, 2)[0][0]
        assert pair == (
            'multiline_str', check.argToStringFunction(multiline_str))

    def testIncludeContextSingleLine(self):
        i = 3
        with configure_pychecker_output(includeContext=True):
            with disable_coloring(), capture_standard_streams() as (out, err):
                check(i)
        pair = parse_output_into_pairs(out, err, 1)[0][0]
        assert pair == ('i', '3')

    def testContextAbsPathSingleLine(self):
        i = 3
        with configure_pychecker_output(includeContext=True, contextAbsPath=True):
            with disable_coloring(), capture_standard_streams() as (out, err):
                check(i)
        # Output with absolute path can easily exceed line width, so no assert line num here
        pairs = parse_output_into_pairs(out, err, 0)
        assert [('i', '3')] in pairs

    def testValues(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(3, 'asdf', "asdf")
        pairs = parse_output_into_pairs(out, err, 1)
        assert pairs == [[('3', None), ("'asdf'", None), ("'asdf'", None)]]

    def testIncludeContextMultiLine(self):
        multiline_str = 'line1\nline2'
        with configure_pychecker_output(includeContext=True):
            with disable_coloring(), capture_standard_streams() as (out, err):
                check(multiline_str)
        first_line = err.getvalue().splitlines()[0]
        assert line_is_context(first_line)
        pair = parse_output_into_pairs(out, err, 3)[1][0]
        assert pair == (
            'multiline_str', check.argToStringFunction(multiline_str))

    def testContextAbsPathMultiLine(self):
        multiline_str = 'line1\nline2'
        with configure_pychecker_output(includeContext=True, contextAbsPath=True):
            with disable_coloring(), capture_standard_streams() as (out, err):
                check(multiline_str)
        first_line = err.getvalue().splitlines()[0]
        assert line_is_abs_path_context(first_line)
        pair = parse_output_into_pairs(out, err, 3)[1][0]
        assert pair == (
            'multiline_str', check.argToStringFunction(multiline_str))

    def testFormat(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            """comment"""
            noop()
            check('sup')  # noqa
            noop()  # noqa
        """comment"""
        noop()
        s = check.format('sup') # noqa
        noop()  # noqa
        assert s == err.getvalue().rstrip()

    def testMultilineInvocationWithComments(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            check(a, b)
        pairs = parse_output_into_pairs(out, err, 1)[0]
        assert pairs == [('a', '1'), ('b', '2')]

    def testNoSourceAvailable(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            eval('check()')
        assert NoAvailableSourceError.infoMessage in err.getvalue()

    def testSingleTupleArgument(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            check((a, b))
        pair = parse_output_into_pairs(out, err, 1)[0][0]
        self.assertEqual(pair, ('(a, b)', '(1, 2)'))

    def testMultilineContainerArgs(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            check((a, b))
            check([a, b])
            check((a, b), [list(range(15)), list(range(15))])
        self.assertEqual(err.getvalue().strip(), """
        check| (a, b): (1, 2)
        check| [a, b]: [1, 2]
        check| (a, b): (1, 2)
        [list(range(15)), list(range(15))]:
        [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]]
        """.strip())
        with disable_coloring(), capture_standard_streams() as (out, err):
            with configure_pychecker_output(includeContext=True):
                check((a, b), [list(range(15)), list(range(15))])
        lines = err.getvalue().strip().splitlines()
        self.assertRegexpMatches(
            lines[0],
            r'ic\| test_pychecker.py:\d+ in testMultilineContainerArgs\(\)',
        )
        self.assertEqual('\n'.join(lines[1:]), """\
        (a, b): (1, 2)
        [list(range(15)), list(range(15))]:
        [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]]""")

    def testMultipleTupleArguments(self):
        with disable_coloring(), capture_standard_streams() as (out, err):
            check((a, b), (b, a), a, b)
        pair = parse_output_into_pairs(out, err, 1)[0]
        self.assertEqual(pair, [
            ('(a, b)', '(1, 2)'), ('(b, a)', '(2, 1)'), ('a', '1'), ('b', '2')])

    def testColoring(self):
        with capture_standard_streams() as (out, err):
            # Output should be colored with ANSI control codes
            check({1: 'str'})
        assert has_ansi_escape_codes(err.getvalue())

    def testConfigureOutputWithNoParameters(self):
        with self.assertRaises(TypeError):
            check.configureOutput()

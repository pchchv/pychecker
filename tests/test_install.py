"""
pychecker — Never use print() to debug again

License: MIT
"""

import unittest
import pychecker
from test_pychecker import (disable_coloring, capture_standard_streams, parse_output_into_pairs)
from install_test_import import run


class TestPyCheckerInstall(unittest.TestCase):
    def testInstall(self):
        pychecker.install()
        with disable_coloring(), capture_standard_streams() as (out, err):
            run()
        assert parse_output_into_pairs(out, err, 1)[0][0] == ('x', '3')
        pychecker.uninstall()  # Clean up builtins

    def testUninstall(self):
        try:
            pychecker.uninstall()
        except AttributeError:  # Already uninstalled
            pass
        # NameError: global name 'check' is not defined
        with self.assertRaises(NameError):
            run()

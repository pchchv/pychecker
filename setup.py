"""
Running tests and publishing to PyPI
"""


import os
from pychecker import *
from os.path import dirname, join
from setuptools.command.test import test
from setuptools import Command


with open(join('pychecker', '__version__.py'), encoding="utf-8") as f:
    meta = f.read()


class Publish(Command):
    """Publish to PyPI with twine."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system('python setup.py sdist bdist_wheel')
        sdist = f'dist/pychecker-{meta["__version__"]}.tar.gz'
        wheel = f'dist/pychecker-{meta["__version__"]}-py2.py3-none-any.whl'
        rc = os.system(f'twine upload "{sdist}" "{wheel}"')
        sys.exit(rc)


class RunTests(test):
    """
    Run the unit tests
    """

    @staticmethod
    def run_tests():
        from unittest import TestLoader, TextTestRunner
        tests_dir = pjoin(dirname(__file__), 'tests')
        suite = TestLoader().discover(tests_dir)
        result = TextTestRunner().run(suite)
        sys.exit(0 if result.wasSuccessful() else -1)

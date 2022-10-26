"""
Running tests and publishing to PyPI
"""


import os
import sys
from os.path import join
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
        sdist = 'dist/pychecker-%s.tar.gz' % meta['__version__']
        wheel = 'dist/pychecker-%s-py2.py3-none-any.whl' % meta['__version__']
        rc = os.system('twine upload "%s" "%s"' % (sdist, wheel))
        sys.exit(rc)

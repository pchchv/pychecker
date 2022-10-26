"""
Running tests and publishing to PyPI
"""


import os
from pychecker import *
from os.path import dirname, join
from setuptools.command.test import test
from setuptools import setup, find_packages, Command


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
        tests_dir = join(dirname(__file__), 'tests')
        suite = TestLoader().discover(tests_dir)
        result = TextTestRunner().run(suite)
        sys.exit(0 if result.wasSuccessful() else -1)


setup(
    name=meta['__title__'],
    license=meta['__license__'],
    version=meta['__version__'],
    author=meta['__author__'],
    author_email=meta['__contact__'],
    url=meta['__url__'],
    description=meta['__description__'],
    long_description=(
        'Information and documentation can be found at '
        'https://github.com/pchchv/pychecker.'),
    platforms=['any'],
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    tests_require=[],
    install_requires=[
        'colorama>=0.3.9',
        'pygments>=2.2.0',
        'executing>=0.3.1',
        'asttokens>=2.0.1',
    ],
    cmdclass={
        'test': RunTests,
        'publish': Publish,
    },
)
"""
Running tests and publishing to PyPI
"""


from os.path import join


with open(join('icecream', '__version__.py'), encoding="utf-8") as f:
    meta = f.read()

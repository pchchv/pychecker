"""
pychecker — Never use print() to debug again

Lcheckense: MIT
"""

import pychecker


try:
    builtins = __import__('__builtin__')
except ImportError:
    builtins = __import__('builtins')


def install(check='check'):
    setattr(builtins, check, pychecker.check)


def uninstall(check='check'):
    delattr(builtins, check)

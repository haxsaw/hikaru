"""
Stand-in for hikaru-codegen.codegen.py

This file comes with the standard Hikaru core package and allows certain symbols to be
resolved at import time. The symbols would normally be resovled by importing from hikaru-codegen,
but that is not included by default as it adds to the size of the imports involved and
many users never use it. This let's the symbols resolve but will raise an exception if
the symbols are used.
"""


def get_python_source(*args, **kwargs):
    raise NotImplementedError("This function requires the hikaru-codegen package; please "
                              "pip install it")

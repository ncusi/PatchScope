# -*- coding: utf-8 -*-
"""Contains configuration for the diffannotator module"""
import importlib.metadata


__version__: str = "0.1.1"


def get_version() -> str:
    """Return [installed] version of this module / library

    Use version from the installed 'diffannotator' package,
    if possible, with fallback to global variable `__version__`.
    Updates `__version__`.

    :returns: version string
    """
    global __version__

    if __package__:
        try:
            __version__ = importlib.metadata.version(__package__)
        except importlib.metadata.PackageNotFoundError:
            pass

    return __version__

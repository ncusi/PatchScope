# -*- coding: utf-8 -*-
"""Contains configuration for the diffannotator module"""
import importlib.metadata
import re
from enum import Enum


__version__: str = "0.1.2"

# configure logging
logger = logging.getLogger(__name__)


class JSONFormat(Enum):
    V1 = "v1"
    V1_5 = "v1.5"
    V2 = "v2"


class JSONFormatExt(Enum):
    V1 = ".json"
    V1_5 = ".json"
    V2 = ".v2.json"


ext_to_ver: dict[str, JSONFormat] = {
    str(JSONFormatExt.V1):   JSONFormat.V1,
    str(JSONFormatExt.V1_5): JSONFormat.V1_5,  # later key "wins"
    str(JSONFormatExt.V2):   JSONFormat.V2,
}

secondary_suffixes = { ".v2" }
secondary_suffix_regexp = re.compile(r"^\.v[0-9]+$")


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

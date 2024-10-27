# -*- coding: utf-8 -*-
"""Contains configuration for the diffannotator module"""
import importlib.metadata
import logging
import re
from enum import Enum
from pathlib import Path
from typing import Optional


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
    JSONFormatExt.V1.value:   JSONFormat.V1,
    JSONFormatExt.V1_5.value: JSONFormat.V1_5,  # later key "wins"
    JSONFormatExt.V2.value:   JSONFormat.V2,
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


def guess_format_version(file_path: Path, warn_ambiguous: bool = False) -> Optional[JSONFormat]:
    suffixes_2_list = file_path.suffixes[-2:]
    suffixes_2_str = ''.join(suffixes_2_list)

    if not warn_ambiguous:
        if suffixes_2_str in ext_to_ver:
            return ext_to_ver[suffixes_2_str]
        elif not suffixes_2_list:
            return None
        elif suffixes_2_list[-1] == JSONFormatExt.V1_5.value:
            return JSONFormat.V1_5
        else:
            return None

    else:
        if len(suffixes_2_list) <= 1:
            if suffixes_2_str in ext_to_ver:
                return ext_to_ver[suffixes_2_str]
            else:
                return None
        if len(suffixes_2_list) == 2:
            if suffixes_2_str in ext_to_ver:
                return ext_to_ver[suffixes_2_str]
            elif suffixes_2_list[-1] != JSONFormatExt.V1_5.value:
                # no ambiguity: cannot be V1 or V1_5 (not a JSON format)
                return None
            elif secondary_suffix_regexp.match(suffixes_2_list[-2]):
                # no ambiguity: some unknown version
                return None
            else:
                logger.warning(f"Ambiguous annotation file format detected: '{file_path}'")
                return JSONFormat.V1_5

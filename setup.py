"""
If compatibility with legacy builds or versions of tools that don’t support
certain packaging standards (e.g. PEP 517 or PEP 660), a simple setup.py script
can be added to your project ^[1] (while keeping the configuration in pyproject.toml):

Notes:
    [1] pip may allow editable install only with pyproject.toml and setup.cfg.
        However, this behavior may not be consistent over various pip versions
        and other packaging-related tools (setup.py is more reliable on those scenarios).

Suggested by https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html
with addition from https://packaging.python.org/en/latest/guides/single-sourcing-package-version/
"""
import codecs
import os.path
from setuptools import setup

def read_file(rel_path: str) -> str:
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()

def get_version_from_file(rel_path: str) -> str:
    for line in read_file(rel_path).splitlines():
        if line.startswith('__version__'):
            delimiter = '"' if '"' in line else "'"
            return line.split(delimiter)[1]
    else:
        raise RuntimeError(f"Unable to find version string in '{rel_path}'.")

setup(
    version=get_version_from_file("src/diffannotator/config.py")
)

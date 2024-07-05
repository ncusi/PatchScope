"""
If compatibility with legacy builds or versions of tools that don’t support
certain packaging standards (e.g. PEP 517 or PEP 660), a simple setup.py script
can be added to your project ^[1] (while keeping the configuration in pyproject.toml):

Notes:
    [1] pip may allow editable install only with pyproject.toml and setup.cfg.
        However, this behavior may not be consistent over various pip versions
        and other packaging-related tools (setup.py is more reliable on those scenarios).

Suggested by https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html
"""
from setuptools import setup

setup()

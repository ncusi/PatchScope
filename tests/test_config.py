# -*- coding: utf-8 -*-
"""Test cases for 'src/diffannotator/config.py' common configuration module"""
import logging

# noinspection PyPackageRequirements
import pytest  # included in diffannotator[dev], which is defined in pypackage.toml
from pathlib import Path

from diffannotator.config import guess_format_version, JSONFormat


def test_guess_format_version(caplog: pytest.LogCaptureFixture):
    """Testing guess_format_version() function"""
    # for warn_ambiguous=False
    actual = guess_format_version(Path("README"), warn_ambiguous=False)
    expected = None
    assert actual == expected, "'README' detected as unknown, warn_ambiguous=False"

    actual = guess_format_version(Path("something.csv"), warn_ambiguous=False)
    expected = None
    assert actual == expected, "'something.csv' detected as unknown, warn_ambiguous=False"

    actual = guess_format_version(Path("something.json"), warn_ambiguous=False)
    expected = JSONFormat.V1_5
    assert actual == expected, "'something.json' detected as V1_5, warn_ambiguous=False"

    actual = guess_format_version(Path("something.some_ext.json"), warn_ambiguous=False)
    expected = JSONFormat.V1_5
    assert actual == expected, "'something.some_ext.json' detected as V1_5, warn_ambiguous=False"

    actual = guess_format_version(Path("something.v2.json"), warn_ambiguous=False)
    expected = JSONFormat.V2
    assert actual == expected, "'something.v2.json' detected as V2, warn_ambiguous=False"

    actual = guess_format_version(Path("something.v999.json"), warn_ambiguous=False)
    expected = JSONFormat.V1_5
    assert actual == expected, "'something.v999.json' ambiguously detected as V1_5, warn_ambiguous=False"

    # for warn_ambiguous=False
    caplog.set_level(logging.WARN)

    caplog.clear()
    actual = guess_format_version(Path("README"), warn_ambiguous=True)
    expected = None
    if caplog.text:
        print(caplog.text)
    assert actual == expected, "'README' detected as unknown, warn_ambiguous=True"
    assert len(caplog.records) == 0, "no warnings for 'README', warn_ambiguous=True"

    caplog.clear()
    actual = guess_format_version(Path("something.csv"), warn_ambiguous=True)
    expected = None
    if caplog.text:
        print(caplog.text)
    assert actual == expected, "'something.csv' detected as unknown, warn_ambiguous=True"
    assert len(caplog.records) == 0, "no warnings for 'something.csv', warn_ambiguous=True"

    caplog.clear()
    actual = guess_format_version(Path("something.json"), warn_ambiguous=True)
    expected = JSONFormat.V1_5
    if caplog.text:
        print(caplog.text)
    assert actual == expected, "'something.json' detected as V1_5, warn_ambiguous=True"
    assert len(caplog.records) == 0, "no warnings for 'something.json', warn_ambiguous=True"

    caplog.clear()
    actual = guess_format_version(Path("something.some_ext.json"), warn_ambiguous=True)
    expected = JSONFormat.V1_5
    assert actual == expected, "'something.some_ext.json' detected as V1_5, warn_ambiguous=True"
    assert (len(caplog.records) == 1
            and caplog.records[0].levelno == logging.WARN
            and caplog.records[0].name == 'diffannotator.config'), \
        "single warning for 'something.some_ext.json', warn_ambiguous=True"

    caplog.clear()
    actual = guess_format_version(Path("something.v2.json"), warn_ambiguous=True)
    expected = JSONFormat.V2
    if caplog.text:
        print(caplog.text)
    assert actual == expected, "'something.v2.json' detected as V2, warn_ambiguous=True"
    assert len(caplog.records) == 0, "no warnings for 'something.v2.json', warn_ambiguous=True"

    caplog.clear()
    actual = guess_format_version(Path("something.v999.json"), warn_ambiguous=True)
    expected = None
    if caplog.text:
        print(caplog.text)
    assert actual == expected, "'something.v999.json' detected as unknown, warn_ambiguous=True"
    assert len(caplog.records) == 0, "no warnings for 'something.v999.json', warn_ambiguous=True"

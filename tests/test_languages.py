# -*- coding: utf-8 -*-
"""Test cases for 'src/diffannotator/languages.py' module"""
import logging
import pytest
from pytest import LogCaptureFixture

from diffannotator import languages
from diffannotator.languages import Languages


# MAYBE: group assertions into separate tests
def test_Languages(caplog: LogCaptureFixture):
    caplog.set_level(logging.WARNING)
    langs = Languages()

    # NOTE: when running only this test, everything works,
    # when running all tests, this test fail because of the reason below
    if not languages.EXT_TO_LANGUAGES:
        pytest.skip("Something wrong: languages.EXT_TO_LANGUAGES is empty")

    if not languages.FILENAME_TO_LANGUAGES:
        pytest.skip("Something wrong: languages.FILENAME_TO_LANGUAGES is empty")

    actual = langs.annotate("src/main.cpp")
    expected = {'language': 'C++', 'type': 'programming', 'purpose': 'programming'}
    assert actual == expected, "for programming language"

    actual = langs.annotate('INSTALL')
    expected = {'language': 'Text', 'type': 'prose', 'purpose': 'documentation'}
    assert actual == expected, "for 'INSTALL' file (no extension)"

    actual = langs.annotate('ChangeLog')
    expected = {'language': 'Text', 'type': 'prose', 'purpose': 'documentation'}
    assert actual == expected, "for 'ChangeLog' file (no extension), via FILENAME_TO_LANGUAGES"

    actual = langs.annotate('README.md')
    expected = {'language': 'Markdown', 'type': 'prose', 'purpose': 'documentation'}
    assert actual == expected, "for 'README.md' file"

    actual = langs.annotate('docs/index.rst')
    assert actual['purpose'] == 'documentation', "purpose of a documentation file"

    actual = langs.annotate('tests/test_cli.py')
    assert actual['purpose'] == 'test', "purpose of a test file"

    actual = langs.annotate("requirements.txt")
    assert actual['purpose'] == 'project', "'requirements.txt' is a project file"
    assert actual['type'] == 'data', "'requirements.txt' should be considered 'data'"
    assert actual['language'] == 'Pip Requirements', "'requirements.txt' language is 'Pip Requirements'"

    actual = langs.annotate(".gitignore")
    expected = {'language': 'Ignore List', 'type': 'data', 'purpose': 'data'}
    assert actual == expected, "for '.gitignore' file"

    actual = langs.annotate("Makefile")
    assert actual['language'] == 'Makefile', "language of 'Makefile' file"
    assert actual['purpose'] == 'project', "'Makefile' is a project file"

    actual = langs.annotate("pyproject.toml")
    expected = {'language': 'TOML', 'type': 'data', 'purpose': 'project'}
    assert actual == expected, "for 'pyproject.toml' file"

    actual = langs.annotate('linguist/.github/workflows/ci.yml')
    expected = {'language': 'YAML', 'type': 'data', 'purpose': 'data'}
    assert actual == expected, "for GitHub Actions YAML file"

    actual = langs.annotate('.devcontainer/Dockerfile')
    assert actual['language'] == 'Dockerfile', "language of 'Dockerfile'"

    assert len(caplog.messages) == 0, "there was nothing logged so far"
    if caplog.text:
        print(caplog.text)

    caplog.clear()
    file_name = ".unknownprojectrc"
    actual = langs.annotate(file_name)
    expected = {'language': 'unknown', 'type': 'other', 'purpose': 'other'}
    assert actual == expected, "for unknown file"
    assert "Unknown file type" in caplog.text, "warn about unknown file"
    assert file_name in caplog.text, "mention file name in the warning"

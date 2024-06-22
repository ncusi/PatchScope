import logging
from pytest import LogCaptureFixture

from languages import Languages


# MAYBE: group assertions into separate tests
def test_Languages(caplog: LogCaptureFixture):
    caplog.set_level(logging.WARNING)
    languages = Languages()

    actual = languages.annotate("src/main.cpp")
    expected = {'language': 'C++', 'type': 'programming', 'purpose': 'programming'}
    assert actual == expected, "for programming language"

    actual = languages.annotate('INSTALL')
    expected = {'language': 'Text', 'type': 'prose', 'purpose': 'documentation'}
    assert actual == expected, "for INSTALL file (no extension)"

    actual = languages.annotate('README.md')
    expected = {'language': 'Markdown', 'type': 'prose', 'purpose': 'documentation'}
    assert actual == expected, "for README.md file"

    actual = languages.annotate('docs/index.rst')
    assert actual['purpose'] == 'documentation', "purpose of a documentation file"

    actual = languages.annotate('tests/test_cli.py')
    assert actual['purpose'] == 'test', "purpose of a test file"

    actual = languages.annotate("requirements.txt")
    assert actual['purpose'] == 'project', "purpose of a project file"
    # assert actual['type'] == 'data', "'requirements.txt' should be considered 'data'"
    # assert actual['language'] == 'Pip Requirements', "'requirements.txt' language is 'Pip Requirements'"

    caplog.clear()
    file_name = ".unknownprojectrc"
    actual = languages.annotate(file_name)
    expected = {'language': 'unknown', 'type': 'other', 'purpose': 'other'}
    assert actual == expected, "for unknown file"
    assert "Unknown file type" in caplog.text, "warn about unknown file"
    assert file_name in caplog.text, "mention file name in the warning"

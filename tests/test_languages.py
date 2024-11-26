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


# TODO?: Make `langs = Languages()` into a fixture
def test_languages_extra_cases_linux(caplog: LogCaptureFixture):
    caplog.set_level(logging.WARNING)
    langs = Languages()

    # NOTE: when running only this test, everything works,
    # when running all tests, this test fail because of the reason below
    if not languages.EXT_TO_LANGUAGES:
        pytest.skip("Something wrong: languages.EXT_TO_LANGUAGES is empty")

    if not languages.FILENAME_TO_LANGUAGES:
        pytest.skip("Something wrong: languages.FILENAME_TO_LANGUAGES is empty")

    # TODO: run cleanup at exit code with something that runs also on test failure
    #       like https://stackoverflow.com/a/52873379/,
    #       or create fixture with cleanup after yield

    languages.EXT_TO_LANGUAGES['.rs'] = ['Rust']
    actual = langs.annotate("rust/kernel/sync/condvar.rs")
    if caplog.text:
        print(caplog.text)

    expected = {'language': 'Rust', 'type': 'programming', 'purpose': 'programming'}
    assert actual == expected, \
        "resolved Rust programming language ('.rs' extension collision: ['RenderScript', 'Rust', 'XML'])"

    # there could have been similar test for 'scripts/Makefile.vmlinux_o'
    # maybe 'tools/lib/bpf/Build' should be treated as Makefile [fragment]?
    languages.FILENAME_TO_LANGUAGES['Makefile.lib'] = ['Makefile']
    languages.FILENAME_TO_LANGUAGES['Makefile.config'] = ['Makefile']
    languages.FILENAME_TO_LANGUAGES['Makefile.deps'] = ['Makefile']
    languages.FILENAME_TO_LANGUAGES['Makefile.perf'] = ['Makefile']  # kernel-specific
    languages.FILENAME_TO_LANGUAGES['Makefile.ubsan'] = ['Makefile']  # kernel-specific
    languages.PATTERN_TO_PURPOSE['Makefile.*'] = 'project'
    actual = langs.annotate("scripts/Makefile.lib")
    if caplog.text:
        print(caplog.text)

    expected = {'language': 'Makefile', 'type': 'programming', 'purpose': 'project'}
    assert actual == expected, \
        "Makefile.lib configured to be detected as 'Makefile', and as file with 'project' purpose"

    # Pygments recognizes this language, but GitHub Linguist does not
    languages.FILENAME_TO_LANGUAGES['Kconfig'] = ['Kconfig']
    languages.FILENAME_TO_LANGUAGES['Kconfig.debug'] = ['Kconfig']
    languages.PATTERN_TO_PURPOSE['Kconfig*'] = 'project'  # NOTE: should it be 'project'?
    actual = langs.annotate("arch/x86/Kconfig")  # and "mm/Kconfig.debug"
    if caplog.text:
        print(caplog.text)

    # should probably be type 'data' or 'prose', not 'other'
    # but GitHub Linguist's languages.yml does not include Kconfig
    expected = {'language': 'Kconfig', 'type': 'other', 'purpose': 'project'}
    assert actual == expected, \
        "Kconfig configured to be detected as 'Kconfig', and as file with 'project' purpose"

    # as of 2024.11.24, GitHub Linguist's languages.yml includes only ".s", ".ms"
    # extensions for 'Unix Assembly', also known as GAS, from GNU Assembler (gas)
    languages.EXT_TO_LANGUAGES['.S'] = ['Unix Assembly']
    actual = langs.annotate("arch/x86/kernel/acpi/wakeup_64.S")
    if caplog.text:
        print(caplog.text)

    expected = {'language': 'Unix Assembly', 'type': 'programming', 'purpose': 'programming'}
    assert actual == expected, \
        "*.S files configured to be detected as 'Unix Assembly' programming language"

    # see https://www.perplexity.ai/search/what-are-rules-files-in-linux-jYxo8Kn6R3CKfRpPTF5Oew
    languages.EXT_TO_LANGUAGES['.rules'] = ['Udev Rules File']
    actual = langs.annotate("drivers/gpu/drm/xe/xe_wa_oob.rules")
    if caplog.text:
        print(caplog.text)

    expected = {'language': languages.EXT_TO_LANGUAGES['.rules'][0]}
    assert actual['language'] == expected['language'], \
        f".rules files configured to be detected as {languages.EXT_TO_LANGUAGES['.rules'][0]!r} language"

    languages.FILENAME_TO_LANGUAGES['README'] = ['Text']
    languages.FILENAME_TO_LANGUAGES['CREDITS'] = ['Text']  # custom format
    languages.FILENAME_TO_LANGUAGES['MAINTAINERS'] = ['Text']  # custom format
    actual = langs.annotate("MAINTAINERS")
    if caplog.text:
        print(caplog.text)

    expected = {'language': 'Text', 'type': 'prose', 'purpose': 'documentation'}
    assert actual == expected, \
        "MAINTAINERS file configured to be a text file (type=prose, purpose=documentation)"

    # https://git-scm.com/docs/gitmailmap
    # GitHub Linguist's languages.yml includes 'Git Config' (also .gitmodules), 'Git Attributes',
    # and 'Git Revision List'/'Git Blame Ignore Revs',, but nothing for '.mailmap'
    languages.FILENAME_TO_LANGUAGES['.mailmap'] = ['Git Mailmap']
    languages.PATTERN_TO_PURPOSE['.mailmap'] = 'data'
    actual = langs.annotate('.mailmap')
    print(f".mailmap -> {actual=}")
    if caplog.text:
        print(caplog.text)

    expected = {'language': 'Git Mailmap', 'type': 'other', 'purpose': 'data'}
    assert actual == expected, \
        "'.mailmap' file is configured to be 'data', etc."

    # here there are multiple choice for *defconfig and 'config' format name:
    # - Unix/Linux config files (UnixConfigLexer)
    # - Shell (BashLexer)
    # noinspection PyUnusedLocal
    actual = langs.annotate("arch/x86/configs/i386_defconfig")
    #print(f"{actual=}")
    if caplog.text:
        print(caplog.text)
    caplog.clear()

    # https://www.devicetree.org/specifications/
    languages.EXT_TO_LANGUAGES['.dts'] = ['Device Tree Source']  # format name taken from file header
    languages.PATTERN_TO_PURPOSE['*.dts'] = 'data'
    # almost the same for 'arch/arm/boot/dts/renesas/r8a73a4.dtsi', for example
    # https://www.nxp.com/docs/en/application-note/AN5125.pdf
    # https://stackoverflow.com/questions/48420126/what-is-the-difference-between-dts-file-and-dtsi-file
    languages.EXT_TO_LANGUAGES['.dtsi'] = ['Device Tree Source include']  # format name taken from file header
    languages.PATTERN_TO_PURPOSE['*.dtsi'] = 'data'
    # almost the same for 'arch/arm64/boot/dts/xilinx/zynqmp-sck-kv-g-revB.dtso', for example
    # https://developer.toradex.com/software/linux-resources/device-tree/device-tree-overlays-overview/#file-formats
    # why different extensions: https://lore.kernel.org/all/20221024173434.32518-2-afd@ti.com/
    languages.EXT_TO_LANGUAGES['.dtso'] = ['Device Tree Source overlay']  # format name taken from file header
    languages.PATTERN_TO_PURPOSE['*.dtso'] = 'data'
    # noinspection PyUnusedLocal
    actual = langs.annotate('arch/arm/boot/dts/renesas/r8a73a4-ape6evm.dts')
    #print(f"{actual=}")
    if caplog.text:
        print(caplog.text)

    languages.PATTERN_TO_PURPOSE['Documentation/*'] = 'documentation'
    languages.PATTERN_TO_PURPOSE['Documentation/**'] = 'documentation'
    # noinspection PyUnusedLocal
    actual = langs.annotate('Documentation/ABI/testing/gpio-cdev')
    #print(f"{actual=}")
    if caplog.text:
        print(caplog.text)

    # expected failure
    #assert actual['purpose'] == 'documentation', \
    #    "files in 'Documentation/' directory are 'documentation' purpose files"

    # TODO: needs look at the she-bang line, or run GitHub Linguist on file contents
    # NOTE: all those files are from the Linux kernel repository
    #actual = langs.annotate('scripts/ver_linux')
    #expected = {'language': 'Awk', 'type': 'programming', 'purpose': 'programming'}

    #actual = langs.annotate('scripts/kernel-doc')
    #expected = {'language': 'Perl', 'type': 'programming', 'purpose': 'programming'}

    #actual = langs.annotate('scripts/show_delta')
    #expected = {'language': 'Python', 'type': 'programming', 'purpose': 'programming'}

    #actual = langs.annotate('scripts/mksysmap')
    #expected = {'language': 'sed', 'type': 'programming', 'purpose': 'programming'}

    #actual = langs.annotate('scripts/stackusage')
    #expected = {'language': 'Shell', 'type': 'programming', 'purpose': 'programming'}

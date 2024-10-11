# -*- coding: utf-8-unix -*-
"""Contains code to detect language of a file based on its file name

It uses the 'language.yml' ('src/diffannotator/languages.yml') taken from
the GitHub Linguist project, which is the library is used on GitHub.com
to detect blob languages, ignore binary or vendored files, suppress generated
files in diffs, and generate language breakdown graphs (written in Ruby, MIT license)
https://github.com/github-linguist/linguist

This module has currently much more limited scope: it tries to use the file name,
and does not try to check file contents, nor does it take user-provided
configuration included in '.gitattributes' file, like GitHub Linguist does
https://github.com/github-linguist/linguist/blob/master/docs/overrides.md#using-gitattributes

Overrides to the data extracted from 'languages.yml' are provided via
the following globl variables:

- `FILENAME_TO_LANGUAGES` - mapping from filenames (basenames) of files
  to single-element list of language corresponding to that name, for example
  FILENAME_TO_LANGUAGES['COPYING'] == 'Text'
- `EXT_TO_LANGUAGES` - mapping from file extension (including the dot '.')
  to single-element list of language corresponding to that name, for example
  EXT_TO_LANGUAGES['.md'] == ['Markdown']
- `PATTERN_TO_PURPOSE` - mapping from file wildcard / glob pattern
  to the purpose of the file (which can be used to determine line types),
  for example PATTERN_TO_PURPOSE['*.cmake'] == 'project'

**NOTE** that currently some of those rules are built in into the
`languages_exceptions()` function.

Example usage:
--------------
  >>> from diffannotator.languages import Languages
  >>> LANGUAGES = Languages()
  >>> LANGUAGES.annotate("src/main.cpp")
  {'language': 'C++', 'type': 'programming', 'purpose': 'programming'}

This module is used by the diff-annotate script, with sources in annotate.py
source code file.
"""
import logging
import os
from collections import defaultdict
from pathlib import Path, PurePath
from typing import List, TypeVar

import yaml

# configure logging
logger = logging.getLogger(__name__)

PathLike = TypeVar("PathLike", str, bytes, Path, os.PathLike)


# names without extensions to be considered text files
FILENAME_TO_LANGUAGES = {
    **{
        filename: ["Text"]
        for filename in [
            "AUTHORS",
            "COPYING",
            "ChangeLog",
            "INSTALL",
            "NEWS",
            "PACKAGERS",
            "README",
            "THANKS",
            "TODO",
        ]
    },
    "Makefile": ["Makefile"],
    "configure.ac": ["M4Sugar"],
}


EXT_TO_LANGUAGES = {
    ".as": ["ActionScript"],
    ".asm": ["ASM"],
    ".cfg": ["INI"],
    ".cs": ["C#"],
    ".h": ["C"],
    ".html": ["HTML"],
    ".json": ["JSON"],
    ".md": ["Markdown"],
    ".pl": ["Perl"],
    ".pm": ["Perl"],
    ".properties": ["INI"],
    ".sql": ["SQL"],
    ".t": ["Perl"],
    ".ts": ["TypeScript"],
    ".txt": ["Text"],
    ".yaml": ["YAML"],
    ".yml": ["YAML"],
}

PATTERN_TO_PURPOSE = {
    # NOTE: Currently the recursive wildcard “**” acts like non-recursive “*”
    # https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.match
    **{
        pattern: "project"
        for pattern in [
            "*.cmake",  # CMake (C++)
            ".nuspec",  # NuGet (C# / CLR)
            "BUILD",  # Bazel (Java, C++, Go,...)
            "CMakeLists.txt",  # CMake (C++)
            "Cargo.toml",  # Cargo (Rust)
            "Dockerfile",  # Docker
            "Gemfile",  # RubyGems (Ruby)
            "Makefile",  # make (C, C++,...)
            "Podfile",  # CocoaPods (Swift and Objective-C)
            "bower.json",  # Bower (JavaScript)
            "build.gradle",  # Gradle, with Groovy DSL (Java, Kotlin / JVM)
            "build.gradle.kts",  # Gradle, with Kotlin DSL (Java, Kotlin / JVM)
            "build.sbt",  # SBT (Scala / JVM)
            "buildfile",  # build2 (C, C++)
            "composer.json",  # Composer (PHP)
            "conanfile.py",  # Conan (C++)
            "conanfile.txt",  # Conan (C++)
            "go.mod",  # Go
            "info/index.json",  # Conda (Python)
            "ivy.xml",  # Ivy (Java / JVM)
            "manifest",  # generic
            "meson.build",  # Meson (C, C++, Objective-C, Java,...)
            "package.json",  # npm (Node.js)
            "pom.xml",  # Maven (Java / JVM)
            "project.clj",  # Leiningen (Clojure)
            "pyproject.toml",  # Python
            "requirements.txt",  # pip (Python)
            "setup.cfg",  # Python
            "vcpkg.json",  # vcpkg (C++)
        ]
    },
    **{
        pattern: "documentation"
        for pattern in [
            "doc",
            "docs",
            "documentation",
            "man",
        ]
    },
}


def languages_exceptions(path: str, lang: List[str]) -> List[str]:
    """Handle exceptions in determining language of a file

    :param path: file path in the repository
    :param lang: file language determined so far
    :return: single element list of languages
    """
    if "spark" in path.lower() and "Roff" in lang:
        return ["Text"]

    if "kconfig" in path.lower() and "Lex" in lang:
        return ["Lex"]

    if "HTML" in lang:
        return ["HTML"]

    if "Roff" in lang:
        return ["Roff"]

    if "M4" in lang:
        return ["M4"]

    return lang


class Languages(object):
    """Linguists file support with some simplification"""

    def __init__(self, languages_yaml: PathLike = "languages.yml"):
        super(Languages, self).__init__()
        self.yaml = Path(languages_yaml)

        # make it an absolute path, so that scripts work from any working directory
        if not self.yaml.exists() and not self.yaml.is_absolute():
            self.yaml = Path(__file__).resolve(strict=True).parent.joinpath(self.yaml)

        self._read()
        self._simplify()

    def _read(self):
        """Read, parse, and extract information from 'languages.yml'"""
        with open(self.yaml, "r") as stream:
            self.languages = yaml.safe_load(stream)

        self.ext_primary = defaultdict(list)
        self.ext_lang = defaultdict(list)
        self.filenames_lang = defaultdict(list)

        # reverse lookup
        for lang, v in self.languages.items():
            if "primary_extension" in v:
                for ext in v["primary_extension"]:
                    self.ext_primary[ext].append(lang)
            if "extensions" in v:
                for ext in v["extensions"]:
                    self.ext_lang[ext].append(lang)
            if "filenames" in v:
                for filename in v["filenames"]:
                    self.filenames_lang[filename].append(lang)

    def _simplify(self):
        """simplify languages assigned to file extensions"""
        for ext in EXT_TO_LANGUAGES:
            if ext in self.ext_primary:
                self.ext_primary[ext] = EXT_TO_LANGUAGES[ext]

            if ext in self.ext_lang:
                self.ext_lang[ext] = EXT_TO_LANGUAGES[ext]

    def _path2lang(self, file_path: str) -> str:
        """Convert path of file in repository to programming language of file"""
        # TODO: consider switching from Path.stem to Path.name (basename)
        filename, ext = Path(file_path).stem, Path(file_path).suffix  # os.file_path.splitext(file_path)
        basename = Path(file_path).name
        #print(f"{file_path=}: {filename=}, {ext=}, {basename=}")

        # NOTE: or dict(itertools.chain.from_iterable(d.items() for d in (d1, d2, d3)))
        # NOTE: FILENAME_TO_LANGUAGES overrides what's from Linguist 'languages.yml'
        filenames_lang = dict(self.filenames_lang, **FILENAME_TO_LANGUAGES)
        if basename in filenames_lang:
            ret = languages_exceptions(file_path, filenames_lang[basename])
            # Debug to catch filenames (basenames) with language collisions
            if len(ret) > 1:
                logger.warning(f"Filename collision in filenames_lang for '{file_path}': {ret}")

            #print(f"... filenames_to_languages: {ret}")
            return ret[0]

        # NOTE: EXT_TO_LANGUAGES overrides what's from Linguist 'languages.yml'
        #print(f"checking if {ext=} is in EXT_TO_LANGUAGES keys: {EXT_TO_LANGUAGES.keys()}")
        if ext in EXT_TO_LANGUAGES:
            #print(f"... ext_to_languages: {EXT_TO_LANGUAGES[ext]}")
            return EXT_TO_LANGUAGES[ext][0]

        if ext in self.ext_primary:
            ret = languages_exceptions(file_path, self.ext_primary[ext])
            # DEBUG to catch extensions with language collisions
            if len(ret) > 1:
                logger.warning(f"Extension collision in ext_primary for '{file_path}': {ret}")

            #print(f"... ext_primary: {ret}")
            return ret[0]

        if ext in self.ext_lang:
            ret = languages_exceptions(file_path, self.ext_lang[ext])
            # Debug to catch extensions with language collisions
            if len(ret) > 1:
                logger.warning(f"Extension collision in ext_lang for '{file_path}': {ret}")

            #print(f"... ext_lang: {ret}")
            return ret[0]

        # TODO: move those exceptions to languages_exceptions()
        if "/dev/null" in file_path:
            return "/dev/null"

        # DEBUG information
        logger.warning(f"Unknown file type for '{file_path}' ({filename}{ext})")

        #print(f"... unknown type for {file_path=}")
        return "unknown"

    @staticmethod
    def _path2purpose(path: str, filetype: str) -> str:
        """Parameter is a filepath and filetype. Returns file purpose as a string."""
        # everything that has test in filename -> test
        # TODO: should it consider only basename?
        if "test" in path.lower():
            return "test"

        path_pure = PurePath(path)
        for pattern, purpose in PATTERN_TO_PURPOSE.items():
            if path_pure.match(pattern):
                return purpose

        # let's assume that prose (i.e. txt, markdown, rst, etc.) is documentation
        if "prose" in filetype:
            return "documentation"

        # limit filetype to selected set of file types
        # from languages.yml: Either data, programming, markup, prose, or nil
        if filetype in ["programming", "data", "markup", "other"]:
            return filetype

        # default unknown
        return "unknown"

    def annotate(self, path: str) -> dict:
        """Annotate file with its primary language metadata

        :param path: file path in the repository
        :return: metadata about language, file type, and purpose of file
        """
        language = self._path2lang(path)

        # TODO: maybe convert to .get() with default value
        try:
            filetype = self.languages[language]["type"]
        except KeyError:
            filetype = "other"

        file_purpose = self._path2purpose(path, filetype)

        return {"language": language, "type": filetype, "purpose": file_purpose}

from collections import defaultdict
import logging
from pathlib import Path
from typing import List

import yaml


# configure logging
logger = logging.getLogger(__name__)

# check if any project management files are present
PROJECT_MANAGEMENT = [
    ".nuspec",
    "CMakeLists.txt",
    "Cargo.toml",
    "bower.json",
    "build.gradle",
    "build.sbt",
    "cmake",
    "composer.json",
    "conanfile.txt",
    "dockerfile",
    "go.mod",
    "info/index.json",
    "ivy.xml",
    "Makefile",
    "manifest",
    "meson.build",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "requirements.txt",
    "setup.cfg",
    "vcpkg.json",
    ]

# names without extensions to be considered text files
TEXT_FILES = [
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


FORCE_SIMPLIFY = {
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

DOCS_PATTERNS = [
    "doc",
    "docs",
    "documentation",
    "man",
]


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

    def __init__(self, yaml: Path = "languages.yml"):
        super(Languages, self).__init__()
        self.yaml = yaml

        self._read()
        self._simplify()

    def _read(self):
        """Read, parse, and extract information from 'languages.yml'"""
        with open(self.yaml, "r") as stream:
            self.languages = yaml.safe_load(stream)
            self.ext_primary = defaultdict(list)
            self.ext_lang = defaultdict(list)

        # reverse lookup
        for lang, v in self.languages.items():
            if "primary_extension" in v:
                for ext in v["primary_extension"]:
                    self.ext_primary[ext].append(lang)
            if "extensions" in v:
                for ext in v["extensions"]:
                    self.ext_lang[ext].append(lang)

    def _simplify(self):
        """simplify languages assigned to file extensions"""
        for fix in FORCE_SIMPLIFY:
            if fix in self.ext_primary:
                self.ext_primary[fix] = FORCE_SIMPLIFY[fix]

            if fix in self.ext_lang:
                self.ext_lang[fix] = FORCE_SIMPLIFY[fix]

    def _path2lang(self, file_path: str) -> str:
        """Convert path of file in repository to programming language of file"""
        # TODO: consider switching from Path.stem to Path.name (basename)
        filename, ext = Path(file_path).stem, Path(file_path).suffix  # os.file_path.splitext(file_path)
        if ".gitignore" in file_path:
            return "Ignore List"

        if ext in self.ext_primary:
            ret = languages_exceptions(file_path, self.ext_primary[ext])
            # DEBUG to catch extensions with language collisions
            if len(ret) > 1:
                logger.warning(f"Extension collision in ext_primary for '{file_path}': {ret}")

            return ret[0]

        if ext in self.ext_lang:
            ret = languages_exceptions(file_path, self.ext_lang[ext])
            # Debug to catch extensions with language collisions
            if len(ret) > 1:
                logger.warning(f"Extension collision in ext_lang for '{file_path}': {ret}")

            return ret[0]

        for f in TEXT_FILES:
            if f in file_path:
                return "Text"

        # TODO: move those exceptions to languages_exceptions()
        if "/dev/null" in file_path:
            return "/dev/null"

        if "Makefile" in file_path:
            return "Makefile"

        if "configure.ac" in file_path:
            return "M4Sugar"

        # DEBUG information
        logger.warning(f"Unknown file type for '{file_path}' ({filename} + {ext})")

        return "unknown"

    def _path2purpose(self, path: str, filetype: str) -> str:
        """Parameter is a filepath and filetype. Returns file purpose as a string."""
        # everything that has test in filename -> test
        # TODO: should it consider only basename?
        if "test" in path.lower():
            return "test"

        # any project management in filename -> project
        if any(pattern in path.lower() for pattern in PROJECT_MANAGEMENT):
            return "project"

        # any documentation in filename -> documentation
        if any(pattern in path.lower() for pattern in DOCS_PATTERNS):
            return "documentation"

        # let's assume that prose (i.e. txt, markdown, rst, etc.) is documentation
        if "prose" in filetype:
            return "documentation"

        # use filetype when matching types in list
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

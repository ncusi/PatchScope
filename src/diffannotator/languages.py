import os
from collections import defaultdict

import yaml

# check if any project management files are present
PROJECT_MANAGMENT = [
    "requirements.txt",
    "makefile",
    "cmake",
    "dockerfile",
    "requirements.txt",
    "setup.cfg",
    "info/index.json",
    "CMakeLists.txt",
    "meson.build",
    "conanfile.txt",
    "manifest",
    "CMakeLists.txt",
    "vcpkg.json",
    "pom.xml",
    "ivy.xml",
    "build.gradle",
    "build.sbt",
    "Cargo.toml",
    "go.mod",
    "package.json",
    "bower.json",
    ".nuspec",
    "composer.json",
    ]

FORCE_SIMPLIFY = {
    ".txt": ["Text"],
    ".json": ["JSON"],
    ".yml": ["YAML"],
    ".yaml": ["YAML"],
    ".md": ["Markdown"],
    ".html": ["HTML"],
    ".h": ["C"],
    ".cs": ["C#"],
    ".cfg": ["INI"],
    ".properties": ["INI"],
    ".pl": ["Perl"],
    ".t": ["Perl"],
    ".ts": ["TypeScript"],
    ".pm": ["Perl"],
    ".sql": ["SQL"],
    ".asm": ["ASM"],
    ".as": ["ActionScript"],
}

DOCS_PATTERNS = ["doc", "docs", "documentation", "man"]


def languages_exceptions(path, lang):
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

    def __init__(self, yaml="languages.yml"):
        super(Languages, self).__init__()
        self.yaml = yaml

        self._read()
        self._simplify()

    def _read(self):
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

    def _path2lang(self, path):
        filename, ext = os.path.splitext(path)
        if ".gitignore" in path:
            return "Ignore List"

        if ext in self.ext_primary:
            ret = languages_exceptions(path, self.ext_primary[ext])
            # Debug to catch extensions with language collisions
            if len(ret) > 1:
                print(">>> P ", path, ret)

            return ret[0]

        if ext in self.ext_lang:
            ret = languages_exceptions(path, self.ext_lang[ext])
            # Debug to catch extensions with language collisions
            if len(ret) > 1:
                print(">>> E", path, ret)

            return ret[0]

        TEXT_FILES = ["INSTALL", "AUTHORS", "ChangeLog", "COPYING", 
                      "NEWS", "PACKAGERS", "TODO", "THANKS", "README"]

        for f in TEXT_FILES:
            if f in path:
                return "Text"

        if "/dev/null" in path:
            return "/dev/null"

        if "Makefile" in path:
            return "Makefile"

        if "configure.ac" in path:
            return "M4Sugar"

        print(">>>", path, "+", filename, "-", ext)

        return "unknown"

    def _path2purpose(self, path, filetype):
        """Parameter is a filepath and filetype.
        Returns file purpose as a string."""


        # everything that has test in filename -> test
        if "test" in path.lower():
            return "test"

        # any project managment in filename -> project
        if any(pattern in path.lower() for pattern in PROJECT_MANAGMENT ):
            return "project"

        # any documentation in filename -> documentation
        if any(pattern in path.lower() for pattern in DOCS_PATTERNS):
            return "documentation"

        # let's assume that prose (ie. txt, markdown, rst, etc) is documentation
        if "prose" in filetype:
            return "documentation"

        # use filetype when matching types in list
        if filetype in ["programming", "data", "markup", "other"]:
            return filetype

        # default unknown
        return "unknown"

    def annotate(self, path):
        language = self._path2lang(path)

        try:
            filetype = self.languages[language]["type"]
        except KeyError:
            filetype = "other"

        filepurpose = self._path2purpose(path, filetype)

        return {"language": language, "type": filetype, "purpose": filepurpose}

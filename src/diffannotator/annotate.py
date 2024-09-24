#!/usr/bin/env python

import collections.abc
from collections import defaultdict, deque, namedtuple
import importlib.metadata
import inspect
import json
import logging
import os
from pathlib import Path
import re
import sys
import time
import traceback
from textwrap import dedent
from typing import List, Dict, Tuple, TypeVar, Optional, Union, Iterator, Literal
from typing import Iterable, Generator, Callable  # should be imported from collections.abc

from pygments.token import Token
import unidiff
import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
import typer
from typing_extensions import Annotated  # in typing since Python 3.9
import yaml

from .generate_patches import GitRepo
from . import languages
from .languages import Languages
from .lexer import Lexer

# optional dependencies
try:
    # noinspection PyPackageRequirements,PyUnresolvedReferences
    import linguist
    # noinspection PyPackageRequirements
    from linguist.libs.language import Language as LinguistLanguage
    has_pylinguist = True

except ImportError:
    class LinguistLanguage:
        """Dummy of the linguist.libs.language.Language enough to satisfy linter"""
        FakeLanguage = namedtuple('FakeLanguage', ['name', 'type'])

        @classmethod
        def find_by_filename(cls, _):
            return [cls.FakeLanguage('unknown', 'unknown')]

    has_pylinguist = False


class LanguagesFromLinguist:
    def __init__(self):
        super(LanguagesFromLinguist, self).__init__()

    def annotate(self, path: str) -> dict:
        """Annotate file with its primary / first language metadata

        :param path: file path in the repository
        :return: metadata about language, file type, and purpose of file
        """
        languages = LinguistLanguage.find_by_filename(path)
        language = languages[0]

        language_name = language.name
        file_type = language.type
        file_purpose = Languages._path2purpose(path, file_type)

        return {
            "language": language_name,
            "type": file_type,
            "purpose": file_purpose,
        }


__version__ = "0.1.0"

T = TypeVar('T')
PathLike = TypeVar("PathLike", str, bytes, Path, os.PathLike)
LineCallback = Callable[[Iterable[Tuple]], str]
OptionalLineCallback = Optional[LineCallback]

PURPOSE_TO_ANNOTATION = {"documentation": "documentation"}
"""Defines when purpose of the file is propagated to line annotation, without parsing"""
TRANSLATION_TABLE = str.maketrans("", "", "*/\\\t\n")

# configure logging
logger = logging.getLogger(__name__)

LANGUAGES = Languages()
LEXER = Lexer()


def line_ends_idx(text: str) -> List[int]:
    """Return position+1 for each newline in text

    This way each line can be extracted with text[pos[i-1]:pos[i]].

    >>> example_text = "123\\n56\\n"
    >>> line_ends_idx(example_text)
    [4, 7]
    >>> example_text[0:4]
    '123\\n'
    >>> example_text[4:7]
    '56\\n'

    :param text: str to process
    :return: list of positions after end of line characters
    """
    return [i for i, ch in enumerate(text, start=1)
            if ch == '\n']


def split_multiline_lex_tokens(tokens_unprocessed: Iterable[T]) -> Generator[T, None, None]:
    """Split multiline tokens into individual lines

    :param tokens_unprocessed: Result of calling `get_tokens_unprocessed(text)`
        method on a `pygments.lexer.Lexer` instance.  This is an iterable
        of (index, token_type, value) tuples, where index is the starting
        position of the token within the input text.

    :return: An iterable of (index, token_type, value) tuples, where `index`
        is the starting position of `value` in the input text, and each
        `value` contains at most one newline.
    """
    for index, token_type, text_fragment in tokens_unprocessed:
        lines = text_fragment.splitlines(keepends=True)

        if len(lines) <= 1:
            # no need for splitting, return original
            yield index, token_type, text_fragment
        else:
            # split into lines, updating the index
            running_count = 0
            for line in lines:
                yield index+running_count, token_type, line
                running_count += len(line)


def group_tokens_by_line(code: str, tokens: Iterable[T]) -> Dict[int, List[T]]:
    """Group tokens by line in code

    For each line in the source `code`, find all `tokens` that belong
    to that line, and group tokens by line.  **Note** that `tokens` must
    be result of parsing `code`.

    :param code: Source code text that was parsed into tokens
    :param tokens: An iterable of (index, token_type, value) tuples,
        preferably with `value` split into individual lines with the
        help of `split_multiline_lex_tokens` function.
    :return: mapping from line number in `code` to list of tokens
        in that line
    """
    tokens_deque = deque(tokens)
    idx_code = line_ends_idx(code)

    line_tokens = defaultdict(list)
    for no, idx in enumerate(idx_code):
        while tokens_deque:
            token = tokens_deque.popleft()
            if token[0] < idx:
                line_tokens[no].append(token)
            else:
                tokens_deque.appendleft(token)
                break

    return line_tokens


def front_fill_gaps(data: Dict[int, T]) -> Dict[int, T]:
    """Fill any gaps in `data` keys with previous value

    >>> front_fill_gaps({1: '1', 3: '3'})
    {1: '1', 2: '1', 3: '3'}

    :param data: Input data - dictionary with int keys
    :return: Front filled input data
    """
    if not data:
        return {}

    # Find the minimum and maximum keys
    min_key = min(data.keys())
    max_key = max(data.keys())

    # Create a new dictionary to store the result
    filled_dict = {}

    # Initialize the previous value
    previous_value = None

    # Iterate through the range of keys
    for key in range(min_key, max_key + 1):
        if key in data:
            previous_value = data[key]
        filled_dict[key] = previous_value

    return filled_dict


def deep_update(d: dict, u: collections.abc.Mapping) -> dict:
    """Update nested dictionary of varying depth

    Update dict `d` with the contents of dict `u`, without overwriting
    deeply nested levels in input dictionary `d`.  **Note** that this
    would also extend `d` with new keys from `u`.

    :param d: dict to update
    :param u: data to update with
    :return: updated input dict
    """
    # modified from https://stackoverflow.com/a/3233356/46058
    # see also https://github.com/pydantic/pydantic/blob/v2.7.4/pydantic/_internal/_utils.py#L103
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        elif isinstance(v, collections.abc.MutableSequence):
            list_value = d.get(k, [])
            list_value.extend(v)
            d[k] = list_value
        else:
            d[k] = v

    return d


def clean_text(text: str) -> str:
    ret = text.translate(TRANSLATION_TABLE)
    ret = re.sub(pattern=r'\s+', repl=' ', string=ret)
    return ret


def line_is_comment(tokens_list: Iterable[Tuple]) -> bool:
    """Given results of parsing line, find if it is comment

    :param tokens_list: An iterable of (index, token_type, text_fragment) tuples,
        supposedly from parsing some line of source code text
    :return: Whether set of tokens in `tokens_list` can be all
        considered to be a comment
    """
    can_be_comment = False
    cannot_be_comment = False

    for _, token_type, text_fragment in tokens_list:
        if token_type in Token.Comment:
            can_be_comment = True
        elif token_type in Token.Text.Whitespace:
            # white space in line is also ok
            can_be_comment = True
        elif token_type in Token.Text and text_fragment.isspace():
            # white space in line is also ok
            can_be_comment = True
        else:
            # other tokens
            cannot_be_comment = True
            break

    return can_be_comment and not cannot_be_comment


class AnnotatedPatchedFile:
    """Annotations for diff for a single file in a patch

    It includes metadata about the programming language associated with
    the changed/patched file.

    Note that major part of the annotation process is performed on demand,
    during the `process()` method call.

    Fixes some problems with `unidiff.PatchedFile`

    :ivar patched_file: original `unidiff.PatchedFile` to be annotated
    :ivar source_file: name of source file (pre-image name),
        without the "a/" prefix from diff / patch
    :ivar target_file: name of target file (post-image name),
        without the "b/" prefix from diff / patch
    :ivar patch_data: gathers patch files and changed patch lines
        annotations; mapping from file name to gathered data
    """
    # NOTE: similar signature to line_is_comment, but returning str
    # TODO: store this type as TypeVar to avoid code duplication
    line_callback: OptionalLineCallback = None

    @staticmethod
    def make_line_callback(code_str: str) -> OptionalLineCallback:
        """Create line callback function from text of its body

        Example of creating a no-op callback:
        >>> AnnotatedPatchedFile.line_callback = AnnotatedPatchedFile.make_line_callback("return None")

        :param code_str: text of the function body code
        :return: callback function or None
        """
        if not code_str:
            return None

        match = re.match(pattern=r"def\s+(?P<func_name>\w+)"
                                 r"\((?P<param>\w+)(?P<type_info>\s*:\s*[^)]*?)?\)"
                                 r"\s*(?P<rtype_info>->\s*[^:]*?\s*)?:\s*$",
                         string=code_str, flags=re.MULTILINE)
        if match:
            # or .info(), if it were not provided extra debugging data
            logger.debug("Found function definition in callback code string:", match.groupdict())

            callback_name = match.group('func_name')
            callback_code_str = code_str
        else:
            # or .info(), if it were not provided full text of the callback body
            logger.debug("Using provided code string as body of callback function", code_str)

            callback_name = "_line_callback"
            callback_code_str = (f"def {callback_name}(tokens):\n" +
                                 "  " + "\n  ".join(code_str.splitlines()) + "\n")
        # TODO?: wrap with try: ... except SyntaxError: ...
        exec(callback_code_str, globals())
        return locals().get(callback_name,
                            globals().get(callback_name,
                                          None))

    def __init__(self, patched_file: unidiff.PatchedFile):
        """Initialize AnnotatedPatchedFile with PatchedFile

        Retrieve pre-image and post-image names of the changed file
        (cleaning them up by removing the "a/" or "B/" prefixes, if
        needed; unidiff does that for .path getter, if it is modern
        enough).

        TODO: handle c-quoted filenames, e.g. '"przyk\305\202ad"'
        for 'przykład'.

        Retrieves information about programming language and purpose
        of the file based solely on the pathname of a source and of
        a target file, using the :mod:`languages` module.

        :param patched_file: patched file data parsed from unified diff
        """
        self.patch_data: Dict[str, Dict] = defaultdict(lambda: defaultdict(list))

        # save original diffutils.PatchedFile
        self.patched_file: unidiff.PatchedFile = patched_file

        # get the names and drop "a/" and "b/"
        self.source_file: str = patched_file.source_file
        self.target_file: str = patched_file.target_file

        if self.source_file[:2] == "a/":
            self.source_file = patched_file.source_file[2:]
        if self.target_file[:2] == "b/":
            self.target_file = patched_file.target_file[2:]

        # add language metadata (based on filename only!)
        source_meta_dict = LANGUAGES.annotate(self.source_file)
        self.patch_data[self.source_file].update(source_meta_dict)

        if self.source_file != self.target_file:
            target_meta_dict = LANGUAGES.annotate(self.target_file)
            self.patch_data[self.target_file].update(target_meta_dict)

        # place to hold pre-image and post-image, if available
        self.source: Optional[str] = None
        self.target: Optional[str] = None
        # cache to hold the result of lexing pre-image/post-image
        self.source_tokens: Optional[Dict[int, List[tuple]]] = None
        self.target_tokens: Optional[Dict[int, List[tuple]]] = None

    # builder pattern
    def add_sources(self, src: str, dst: str) -> 'AnnotatedPatchedFile':
        """Add pre-image and post-image of a file at given diff

        **NOTE:** Modifies self, and returns modified object.

        Example:

        >>> from diffannotator.annotate import AnnotatedPatchedFile
        >>> import unidiff
        >>> patch_path = 'tests/test_dataset_structured/keras-10/patches/c1c4afe60b1355a6c0e83577791a0423f37a3324.diff'
        >>> patch_set = unidiff.PatchSet.from_filename(patch_path, encoding="utf-8")
        >>> patched_file = AnnotatedPatchedFile(patch_set[0]).add_sources("a", "b")
        >>> patched_file.source
        'a'
        >>> patched_file.target
        'b'

        :param src: pre-image contents of patched file
        :param dst: post-image contents of patched file
        :return: changed object, to enable flow/builder pattern
        """
        self.source = src
        self.target = dst

        return self

    def add_sources_from_files(self,
                               src_file: Path,
                               dst_file: Path) -> 'AnnotatedPatchedFile':
        """Read pre-image and post-image for patched file at given diff

        **NOTE:** Modifies self, adding contents of files, and returns modified
        object.

        Example:

        >>> from diffannotator.annotate import AnnotatedPatchedFile
        >>> import unidiff
        >>> from pathlib import Path
        >>> patch_path = 'tests/test_dataset_structured/keras-10/patches/c1c4afe60b1355a6c0e83577791a0423f37a3324.diff'
        >>> patch_set = unidiff.PatchSet.from_filename(patch_path, encoding="utf-8")
        >>> patched_file = AnnotatedPatchedFile(patch_set[0])
        >>> files_path = Path('tests/test_dataset_structured/keras-10/files')
        >>> src_path = files_path / 'a' / Path(patched_file.source_file).name
        >>> dst_path = files_path / 'b' / Path(patched_file.target_file).name
        >>> patched_file_with_sources = patched_file.add_sources_from_files(src_file=src_path, dst_file=dst_path)
        >>> patched_file_with_sources.source.splitlines()[2]
        'from __future__ import absolute_import'

        :param src_file: path to pre-image contents of patched file
        :param dst_file: path to post-image contents of patched file
        :return: changed object
        """
        return self.add_sources(
            src_file.read_text(encoding="utf-8"),
            dst_file.read_text(encoding="utf-8")
        )

    def image_for_type(self, line_type: Literal['-','+']) -> Optional[str]:
        """Return pre-image for '-', post-image for '+', if available

        :param line_type: denotes line type, e.g. line.line_type from unidiff
        :return: pre-image or post-image, or None if pre/post-images are not set
        """
        if line_type == unidiff.LINE_TYPE_REMOVED:  # '-'
            return self.source
        elif line_type == unidiff.LINE_TYPE_ADDED:  # '+'
            return self.target
        else:
            raise ValueError(f"value must be '-' or '+', got {line_type!r}")

    def tokens_for_type(self, line_type: Literal['-','+']) -> Optional[Dict[int, List[tuple]]]:
        """Run lexer on a pre-image or post-image contents, if available

        Returns (cached) result of lexing pre-image for `line_type` '-',
        and of post-image for line type '+'.

        The pre-image and post-image contents of patched file should / can
        be provided with the help of `add_sources()` or `add_sources_from_files()`
        methods.

        :param line_type: denotes line type, e.g. line.line_type from unidiff;
            must be one of '+' or '-'.
        :return: post-processed result of lexing, split into lines,
            if there is pre-/post-image file contents available.
        """
        # return cached value, if available
        if line_type == unidiff.LINE_TYPE_REMOVED:  # '-'
            if self.source_tokens is not None:
                return self.source_tokens
            contents = self.source
            file_path = self.source_file
        elif line_type == unidiff.LINE_TYPE_ADDED:  # '+'
            if self.target_tokens is not None:
                return self.target_tokens
            contents = self.target
            file_path = self.target_file
        else:
            raise ValueError(f"value must be '-' or '+', got {line_type!r}")

        # return None if source code is not available for lexing
        if contents is None:
            return None

        # lex selected contents (same as in main process() method)
        tokens_list = LEXER.lex(file_path, contents)
        tokens_split = split_multiline_lex_tokens(tokens_list)
        tokens_group = group_tokens_by_line(contents, tokens_split)
        # just in case, it should not be needed
        tokens_group = front_fill_gaps(tokens_group)

        # save/cache computed data
        if line_type == unidiff.LINE_TYPE_REMOVED:  # '-'
            self.source_tokens = tokens_group
        elif line_type == unidiff.LINE_TYPE_ADDED:  # '+'
            self.target_tokens = tokens_group

        # return computed result
        return tokens_group

    def tokens_range_for_type(self, line_type: Literal['-','+'],
                              start_line: int, length: int) -> Optional[Dict[int, List[tuple]]]:
        """Lexing results for given range of lines, or None if no pre-/post-image

        The pre-image and post-image contents of patched file should / can
        be provided with the help of `add_sources()` or `add_sources_from_files()`
        methods.

        The result is mapping from line number of the pre- or post-image
        contents, counting from 1 (the same as diff and unidiff), to the list
        of tokens corresponding to the line in question.

        :param line_type: denotes line type, e.g. line.line_type from unidiff;
            must be one of '-' (unidiff.LINE_TYPE_REMOVED) or '+' (unidiff.LINE_TYPE_ADDED).
        :param start_line: starting line number in file, counting from 1
        :param length: number of lines to return results for,
            starting from `start_line`
        :return: post-processed result of lexing, split into lines,
            if there is pre-/post-image file contents available;
            None if there is no pre-/post-image contents attached.
        """
        tokens_list = self.tokens_for_type(line_type=line_type)
        if tokens_list is None:
            return None

        # Iterable might be not subscriptable, that's why there is list() here
        # TODO: check if it is correct (0-based vs 1-based subscripting)
        return {
            line_no+1: line_tokens
            for line_no, line_tokens in tokens_list.items()
            if line_no+1 in range(start_line, (start_line + length))
        }

    def hunk_tokens_for_type(self, line_type: Literal['-','+'],
                             hunk: unidiff.Hunk) -> Optional[Dict[int, List[tuple]]]:
        """Lexing results for removed ('-')/added ('+') lines in hunk, if possible

        The pre-image and post-image contents of patched file should / can
        be provided with the help of `add_sources()` or `add_sources_from_files()`
        methods.  If this contents is not provided, this method returns None.

        The result is mapping from line number of the pre- or post-image
        contents, counting from 1 (the same as diff and unidiff), to the list
        of tokens corresponding to the line in question.

        :param line_type: denotes line type, e.g. line.line_type from unidiff;
            must be one of '-' (unidiff.LINE_TYPE_REMOVED) or '+' (unidiff.LINE_TYPE_ADDED).
        :param hunk: block of changes in fragment of diff corresponding
            to changed file
        :return: post-processed result of lexing, split into lines,
            if there is pre-/post-image file contents available;
            None if there is no pre-/post-image contents attached.
        """
        tokens_list = self.tokens_for_type(line_type=line_type)
        if tokens_list is None:
            return None

        result = {}
        for line in hunk:
            if line.line_type != line_type:
                continue
            # NOTE: first line of file is line number 1, not 0, according to (uni)diff
            # but self.tokens_for_type(line_type) returns 0-based indexing
            line_no = line.source_line_no if line_type == unidiff.LINE_TYPE_REMOVED else line.target_line_no
            # first line is 1; first element has index 0
            result[line_no] = tokens_list[line_no - 1]

        return result

    def process(self):
        for hunk in self.patched_file:
            hunk_data = AnnotatedHunk(self, hunk).process()
            deep_update(self.patch_data, hunk_data)

        return self.patch_data


class AnnotatedHunk:
    """Annotations for diff for a single hunk in a patch

    It parses pre-image and post-image of a hunk using Pygments, and assigns
    the type of "code" or "documentation" for each changed line.

    Note that major part of the annotation process is performed on demand,
    during the `process()` method call.

    :ivar patched_file: `AnnotatedPatchedFile` this `AnnotatedHunk` belongs to
    :ivar hunk: source `unidiff.Hunk` (modified blocks of a file) to annotate
    :ivar patch_data: place to gather annotated hunk data
    """
    def __init__(self, patched_file: AnnotatedPatchedFile, hunk: unidiff.Hunk):
        """Initialize AnnotatedHunk with AnnotatedPatchedFile and Hunk

        The `patched_file` is used to examine file purpose, and possibly
        annotate lines according to `PURPOSE_TO_ANNOTATION` mapping.
        For example each changed line in a changed file which purpose is
        "documentation" is also marked as having "documentation" type.

        :param patched_file: changed file the hunk belongs to
        :param hunk: diff hunk to annotate
        """
        self.patched_file = patched_file
        self.hunk = hunk

        self.patch_data = defaultdict(lambda: defaultdict(list))

    def tokens_for_type(self, line_type: Literal['-','+']) -> Optional[Dict[int, List[tuple]]]:
        """Lexing results for removed ('-')/added ('+') lines in hunk, if possible

        Passes work to `AnnotatedPatchedFile.hunk_tokens_for_type` method
        for a patched file this hunk belongs to.

        :param line_type: line_type: denotes line type, e.g. line.line_type from unidiff;
            must be one of '-' (unidiff.LINE_TYPE_REMOVED) or '+' (unidiff.LINE_TYPE_ADDED).
        :return: post-processed result of lexing, split into lines,
            if there is pre-/post-image file contents available;
            None if there is no pre-/post-image contents attached.
        """
        return self.patched_file.hunk_tokens_for_type(line_type, self.hunk)

    def process(self):
        """Process associated patch hunk, annotating changes

        Returns single-element mapping from filename to pre- and post-image
        line annotations.  The pre-image line annotations use "-" as key,
        while post-image use "+".  For each line, there is currently gathered
        the following data:

        - "id": line number in the hunk itself (it is not line number in pre-image
          for "-" lines, or line image in post-image for "+" lines); this numbering
          counts context lines, which are currently ignored.
        - "type": "documentation" or "code", or the value mapped from the file purpose
          by the `PURPOSE_TO_ANNOTATION` global variable, or the value provided by the
          `AnnotatedPatchedFile.line_callback` function; comments and docstrings
          counts as "documentation", and so do every line of documentation file
        - "purpose": file purpose
        - "tokens": list of tokens from Pygments lexer (`get_tokens_unprocessed()`)

        If file purpose is in `PURPOSE_TO_ANNOTATION`, then line annotation that
        corresponds to that file purpose in this mapping is used for all lines
        of the hunk as "type".

        Updates and returns the `self.patch_data` field.

        :return: annotated patch data, mapping from changed file name
            to '+'/'-', to annotated line info (from post-image or pre-image)
        :rtype: dict[str, dict[str, dict]
        """
        # choose file name to be used to select file type and lexer
        if self.patched_file.source_file == "/dev/null":
            file_path = self.patched_file.target_file
        else:
            # NOTE: only one of source_file and target_file can be "/dev/null"
            file_path = self.patched_file.source_file

        file_purpose = self.patched_file.patch_data[file_path]["purpose"]

        if file_purpose in PURPOSE_TO_ANNOTATION:
            for line_idx, line in enumerate(self.hunk):
                self.add_line_annotation(line_idx,
                                         self.patched_file.source_file,
                                         self.patched_file.target_file,
                                         line.line_type,
                                         PURPOSE_TO_ANNOTATION[file_purpose],
                                         file_purpose,
                                         [(0, Token.Text, line.value), ])

            return self.patch_data

        # lex pre-image and post-image, separately
        for line_type in {unidiff.LINE_TYPE_ADDED, unidiff.LINE_TYPE_REMOVED}:
            # TODO: use NamedTuple, or TypedDict, or dataclass
            line_data = [{
                'value': line.value,
                'hunk_line_no': i,
                'line_type': line.line_type,
            } for i, line in enumerate(self.hunk)
                # unexpectedly, there is no need to check for unidiff.LINE_TYPE_EMPTY
                if line.line_type in {line_type, unidiff.LINE_TYPE_CONTEXT}]

            source = ''.join([line['value'] for line in line_data])

            tokens_list = LEXER.lex(file_path, source)
            tokens_split = split_multiline_lex_tokens(tokens_list)
            tokens_group = group_tokens_by_line(source, tokens_split)
            # just in case, it should not be needed
            tokens_group = front_fill_gaps(tokens_group)

            for i, line_tokens in tokens_group.items():
                line_info = line_data[i]

                line_annotation: Optional[str] = None
                if AnnotatedPatchedFile.line_callback is not None:
                    line_annotation = AnnotatedPatchedFile.line_callback(line_tokens)
                if line_annotation is None:
                    line_annotation = 'documentation' if line_is_comment(line_tokens) else 'code'

                self.add_line_annotation(
                    line_no=line_info['hunk_line_no'],
                    source_file=self.patched_file.source_file,
                    target_file=self.patched_file.target_file,
                    change_type=line_info['line_type'],
                    line_annotation=line_annotation,
                    purpose=file_purpose,
                    tokens=line_tokens
                )

        return self.patch_data

    def add_line_annotation(self, line_no: int, source_file: str, target_file: str,
                            change_type: str, line_annotation: str, purpose: str,
                            tokens: List[Tuple]) -> None:
        """Add line annotations for a given line in a hunk

        :param line_no: line number in a diff hunk body
        :param source_file: name of changed file in pre-image of diff,
            before changes
        :param target_file: name of changed file in post-image of diff,
            after changes
        :param change_type: one of `LINE_TYPE_*` constants from `unidiff.constants`
        :param line_annotation: type of line ("code", "documentation",...)
        :param purpose: purpose of file ("project", "programming", "documentation",
            "data", "markup", "other",...)
        :param tokens: result of `pygments.lexer.Lexer.get_tokens_unprocessed()`
        """
        data = {
            'id': line_no,
            'type': line_annotation,
            'purpose': purpose,
            'tokens': tokens
        }

        # only changed lines are annotated, context lines are not interesting
        if change_type == unidiff.LINE_TYPE_ADDED:
            self.patch_data[target_file]["+"].append(data)
        elif change_type == unidiff.LINE_TYPE_REMOVED:
            self.patch_data[source_file]["-"].append(data)


def annotate_single_diff(diff_path: PathLike, missing_ok: bool = False) -> dict:
    """Annotate single unified diff patch file at given path

    :param diff_path: patch filename
    :param missing_ok: if false (the default), raise exception if `diff_path`
        does not exist, or cannot be read.
    :return: annotation data
    """
    patch_annotations = {}

    try:
        patch_set = unidiff.PatchSet.from_filename(diff_path, encoding="utf-8")

    except FileNotFoundError as ex:
        # TODO?: use logger, log either warning or error
        print(f"No such patch file: '{diff_path}'", file=sys.stderr)

        if not missing_ok:
            raise ex
        return {}

    except PermissionError as ex:
        if Path(diff_path).exists() and Path(diff_path).is_dir():
            print(f"Path points to directory, not patch file: '{diff_path}'")
        else:
            print(f"Permission denied to read patch file '{diff_path}'")

        if not missing_ok:
            raise ex
        return {}

    except Exception as ex:
        print(f"Error parsing patch file '{diff_path}': {ex!r}")
        # raise ex
        return {}  # explicitly return empty dict on parse error

    try:
        for i, patched_file in enumerate(patch_set, start=1):
            annotated_patch_file = AnnotatedPatchedFile(patched_file)
            patch_annotations.update(annotated_patch_file.process())

    except Exception as ex:
        print(f"Error processing patch file '{diff_path}': {ex!r}")
        traceback.print_tb(ex.__traceback__)
        # raise ex

    return patch_annotations


class Bug:
    """Represents a single bug in a dataset, or a set of related patches

    :ivar patches: mapping from some kind of identifiers to annotated patches;
        the identifier might be the pathname of patch file, or the commit id
    :vartype patches: dict[str, dict]
    :cvar DEFAULT_PATCHES_DIR: default value for `patches_dir` parameter
        in `Bug.from_dataset()` static method (class property)
    :cvar DEFAULT_ANNOTATIONS_DIR:  default value for `annotations_dir` parameter
        in `Bug.from_dataset()` static method (class property)
    :ivar read_dir: path to the directory patches were read from, or None
    :ivar save_dir: path to default directory where annotated data should
        be saved (if `save()` method is called without `annotate_dir`), or None
    :ivar relative_save_dir: bug_id / annotations_dir, i.e. subdirectory
        where to save annotation data, relative to `annotate_dir` parameter
        in `save()` method; **available only** if the Bug object was created
        with `from_dataset()`
    """
    DEFAULT_PATCHES_DIR: str = "patches"
    DEFAULT_ANNOTATIONS_DIR: str = "annotation"

    def __init__(self, patches_data: dict, *,
                 read_dir: Optional[PathLike] = None,
                 save_dir: Optional[PathLike] = None):
        """Constructor for class representing a single Bug

        You better use alternative constructors instead:

        - `Bug.from_dataset` - from patch files in a directory (a dataset)
        - `Bug.from_patchset` - from patch id and unidiff.PatchSet

        :param patches_data: annotation data, from annotating a patch
            or a series of patches (e.g. from `annotate_single_diff()`);
            a mapping from patch id (e.g. filename of a patch file)
            to the result of annotating said patch
        :param read_dir: path to the directory patches were read from, or None
        :param save_dir: path to default directory where annotated data should
            be saved, or None
        """
        self.read_dir: Optional[Path] = Path(read_dir) \
            if read_dir is not None else None
        self.save_dir: Optional[Path] = Path(save_dir) \
            if save_dir is not None else None

        self.patches: dict[str, dict] = patches_data

    @classmethod
    def from_dataset(cls, dataset_dir: PathLike, bug_id: str, *,
                     patches_dir: str = DEFAULT_PATCHES_DIR,
                     annotations_dir: str = DEFAULT_ANNOTATIONS_DIR,
                     fan_out: bool = False) -> 'Bug':
        """Create Bug object from patch files for given bug in given dataset

        Assumes that patch files have '*.diff' extension, and that they are
        in the `dataset_dir` / `bug_id` / `patches_dir` subdirectory (if `patches_dir`
        is an empty string, this is just `dataset_dir` / `bug_id`).

        :param dataset_dir: path to the dataset (parent directory to
            the directory with patch files)
        :param bug_id: bug id (name of directory with patch files)
        :param patches_dir: name of subdirectory with patch files, if any;
            patches are assumed to be in dataset_dir / bug_id / patches_dir directory;
            use empty string ("") to not use subdirectory
        :param annotations_dir: name of subdirectory where annotated data will be saved;
            in case the `save()` method is invoked without providing `annotate_path`
            parameter, the data is saved in dataset_dir / bug_id / annotations_dir
            subdirectory; use empty string ("") to not use subdirectory
        :param fan_out: the dataset uses stores patches in fan-out subdirectories,
            like the ones generated by 'diff-generate --use-fanout', that is patches
            are assumed to be in dataset_dir / bug_id / patches_dir / fanout_subdir
        :return: Bug object instance
        """
        read_dir = Path(dataset_dir).joinpath(bug_id, patches_dir)
        save_dir = Path(dataset_dir).joinpath(bug_id, annotations_dir)  # default for .save()

        # sanity checking
        if not read_dir.exists():
            # TODO: use logger, log error
            print(f"Error during Bug constructor: '{read_dir}' path does not exist")
        elif not read_dir.is_dir():
            # TODO: use logger, log error
            print(f"Error during Bug constructor: '{read_dir}' is not a directory")

        obj = Bug({}, read_dir=read_dir, save_dir=save_dir)
        if fan_out:
            obj.patches = obj._get_patches_from_dir_with_fanout(patches_dir=read_dir)
        else:
            obj.patches = obj._get_patches_from_dir(patches_dir=read_dir)
        obj.relative_save_dir = Path(bug_id).joinpath(annotations_dir)  # for .save()

        return obj

    @classmethod
    def from_patchset(cls, patch_id: Union[str, None], patch_set: unidiff.PatchSet) -> 'Bug':
        """Create Bug object from unidiff.PatchSet

        If `patch_id` is None, then it tries to use the 'commit_id' attribute
        of `patch_set`; if this attribute does not exist, it constructs artificial
        `patch_id` (currently based on repr(patch_set), but that might change).

        :param patch_id: identifies source of the `patch_set`
        :param patch_set: changes to annotate
        :return: Bug object instance
        """
        patch_annotations = {}
        i = 0
        try:
            # based on annotate_single_diff() function code
            for i, patched_file in enumerate(patch_set, start=1):
                annotated_patch_file = AnnotatedPatchedFile(patched_file)
                patch_annotations.update(annotated_patch_file.process())

        except Exception as ex:
            print(f"Error processing PatchSet {patch_set!r} at {i} patched file: {ex!r}")
            traceback.print_tb(ex.__traceback__)
            # raise ex

        if patch_id is None:
            patch_id = getattr(patch_set, 'commit_id', repr(patch_set))

        return Bug({patch_id: patch_annotations})

    def _get_patch(self, patch_file: PathLike) -> dict:
        """Get and annotate a single patch

        :param patch_file: basename of a patch
        :return: annotated patch data
        """
        patch_path = self.read_dir.joinpath(patch_file)

        # Skip diffs between multiple versions
        if "..." in str(patch_path):
            # TODO: log a warning
            return {}

        return annotate_single_diff(patch_path)

    def _get_patches_from_dir(self, patches_dir: PathLike,
                              fan_out: bool = False) -> dict[str, dict]:
        """Get and annotate set of patches from given directory

        :param patches_dir: directory with patches
        :param fan_out: the dataset uses stores patches in fan-out subdirectories,
            like the ones generated by 'diff-generate --use-fanout', that is patches
            are assumed to be in dataset_dir / bug_id / patches_dir / fanout_subdir
        :return: mapping from patch filename (patch source)
            to annotated patch data
        """
        patches_data = {}

        for patch_file in patches_dir.glob('*.diff'):
            if fan_out:
                patch_data = self._get_patch('/'.join(patch_file.parts[-2:]))
            else:
                patch_data = self._get_patch(patch_file.name)
            patches_data[patch_file.name] = patch_data

        return patches_data

    def _get_patches_from_dir_with_fanout(self, patches_dir: PathLike) -> dict[str, dict]:
        """Get and annotate set of patches from given directory, with fan-out

        Fan-out means that individual patches (diffs), instead of being
        stored directly in the `patches_dir` directory, are instead
        stored in subdirectories of said directory, 1 level deeper.

        :param patches_dir: directory with patches
        :return: mapping from patch filename (patch source),
            relative to `patches_dir` (as string), to annotated patch data
        """
        patches_data = {}

        # DEBUG
        #print(f"getting patches from patches_dir={patches_dir} with fanout")
        for subdir in patches_dir.iterdir():
            # DEBUG
            #print(f"- in {subdir.name} subdirectory: {subdir}")
            if subdir.is_dir():
                subdir_data = self._get_patches_from_dir(subdir, fan_out=True)
                # DEBUG
                #print(f"  got subdir_data with {len(subdir_data)} element(s)")
                patches_data.update(
                    { f"{subdir.name}/{filename}": data
                      for filename, data in subdir_data.items() }
                )

        return patches_data

    def save(self, annotate_dir: Optional[PathLike] = None, fan_out: bool = False):
        """Save annotated patches in JSON format

        :param annotate_dir: Separate dir to save annotations, optional.
            If not set, `self.save_dir` is used as a base path.
        :param fan_out: Save annotated data in a fan-out directory,
            named after first 2 hexdigits of patch_id; the rest is used
            for the basename; splits patch_id.
        """
        if annotate_dir is not None:
            base_path = Path(annotate_dir)

            # use `self.relative_save_dir` if available
            relative_save_dir = getattr(self, 'relative_save_dir', '')
            base_path = base_path.joinpath(relative_save_dir)
        else:
            base_path = self.save_dir

        if base_path is None:
            raise ValueError("For this Bug, annotate_dir parameter must be provided to .save()")

        # ensure that base_path exists in filesystem
        base_path.mkdir(parents=True, exist_ok=True)

        # save annotated patches data
        for patch_id, patch_data in self.patches.items():
            if fan_out:
                base_path.joinpath(patch_id[:2]).mkdir(exist_ok=True)
                offset = int('/' in patch_id)  #: for '12345' and '12/345' to both split into '12' / '345'
                out_path = base_path / Path(patch_id[:2], patch_id[2+offset:]).with_suffix('.json')
            else:
                out_path = base_path / Path(patch_id).with_suffix('.json')

            with out_path.open('w') as out_f:
                json.dump(patch_data, out_f)


# TODO?: Convert BugDataset to using @dataclass
class BugDataset:
    """Bugs dataset class

    :ivar bug_ids: list of bug identifiers (directories with patch files)
        contained in a given `dataset_dir`, or list of PatchSet extracted
        from Git repo - that can be turned into annotated patch data with
        `get_bug()` method.
    :ivar _dataset_path: path to the dataset directory (with directories with patch files);
        present only when creating `BugDataset` object from dataset directory.
    :ivar _patches: mapping from patch id to `unidiff.PatchSet` (unparsed);
        present only when creating `BugDataset` object from Git repo commits.
    """

    def __init__(self, bug_ids: List[str],
                 dataset_path: Optional[PathLike] = None,
                 patches_dict: Optional[Dict[str, unidiff.PatchSet]] = None,
                 patches_dir: str = Bug.DEFAULT_PATCHES_DIR,
                 annotations_dir: str = Bug.DEFAULT_ANNOTATIONS_DIR,
                 fan_out: bool = False):
        """Constructor of bug dataset.

        You better use alternative constructors instead:

        - `BugDataset.from_directory` - from patch files in subdirectories \
          (bugs) of a given directory (a dataset)
        - `BugDataset.from_repo` - from selected commits in a Git repo

        :param bug_ids: set of bug ids
        :param dataset_path: path to the dataset, if BugDataset was created
            from dataset directory via `BugDataset.from_directory`
        :param patches_dict: mapping from patch id to patch / patchset
        :param patches_dir: name of subdirectory with patch files, if any;
            patches are assumed to be in dataset_dir / bug_id / patches_dir directory;
            use empty string ("") to not use subdirectory;
            makes sense only if `dataset_path` is not None
        :param annotations_dir: name of subdirectory where annotated data will be saved;
            in case the `save()` method is invoked without providing `annotate_path`
            parameter, the data is saved in dataset_dir / bug_id / annotations_dir
            subdirectory; use empty string ("") to not use subdirectory;
            makes sense only if `dataset_path` is not None
        :param fan_out: assume that patches are stored in fan-out subdirectories,
            like the ones generated by 'diff-generate --use-fanout', that is patches
            are assumed to be in dataset_dir / bug_id / patches_dir / fanout_subdir;
            makes sense only if `dataset_path` is not None
        """
        self.bug_ids = bug_ids
        # identifies type of BugDataset
        # TODO: do a sanity check - exactly one should be not None,
        #       or both should be None and bug_ids should be empty
        self._dataset_path = dataset_path
        self._patches = patches_dict
        # TODO: warn if patches_dir, annotations_dir or fan_out
        #       are used with non None patches_dict
        self._patches_dir = patches_dir
        self._annotations_dir = annotations_dir
        self._fan_out = fan_out

    @classmethod
    def from_directory(cls, dataset_dir: PathLike,
                       patches_dir: str = Bug.DEFAULT_PATCHES_DIR,
                       annotations_dir: str = Bug.DEFAULT_ANNOTATIONS_DIR,
                       fan_out: bool = False) -> 'BugDataset':
        """Create BugDataset object from directory with directories with patch files

        :param dataset_dir: path to the dataset
        :param patches_dir: name of subdirectory with patch files, if any;
            patches are assumed to be in dataset_dir / bug_id / patches_dir directory;
            use empty string ("") to not use subdirectory
        :param annotations_dir: name of subdirectory where annotated data will be saved;
            in case the `save()` method is invoked without providing `annotate_path`
            parameter, the data is saved in dataset_dir / bug_id / annotations_dir
            subdirectory; use empty string ("") to not use subdirectory
        :param fan_out: assume that patches are stored in fan-out subdirectories,
            like the ones generated by 'diff-generate --use-fanout', that is patches
            are assumed to be in dataset_dir / bug_id / patches_dir / fanout_subdir
        :return: BugDataset object instance
        """
        dataset_path = Path(dataset_dir)

        try:
            return BugDataset([str(d.name) for d in dataset_path.iterdir()
                               if d.is_dir()],
                              dataset_path=dataset_path,
                              patches_dir=patches_dir,
                              annotations_dir=annotations_dir,
                              fan_out=fan_out)

        # TODO: use a more specific exception class
        except Exception as ex:
            print(f"Error in BugDataset.from_directory('{dataset_path}'): {ex}")
            return BugDataset([])

    @classmethod
    def from_repo(cls,
                  repo: Union[GitRepo, PathLike],
                  revision_range: Union[str, Iterable[str]] = 'HEAD') -> 'BugDataset':
        """Create BugDataset object from selected commits in a Git repo

        :param repo: GitRepo, or path to Git repository
        :param revision_range: arguments to pass to `git log --patch`, see
            https://git-scm.com/docs/git-log; by default generates patches
            for all commits from the HEAD
        :return: BugDataset object instance
        """
        # wrap in GitRepo, if necessary
        if not isinstance(repo, GitRepo):
            # TODO: do sanity check: does `repo` path exist, does it look like repo?
            repo = GitRepo(repo)

        # TODO: catch and handle exceptions
        patches = repo.log_p(revision_range=revision_range, wrap=True)
        if inspect.isgenerator(patches):
            # evaluate generator, because BugDataset constructor expects list
            patches = list(patches)

        commit_patches = {getattr(patch_set, "commit_id", f"idx-{i}"): patch_set
                          for i, patch_set in enumerate(patches)}
        obj = BugDataset(bug_ids=list(commit_patches), patches_dict=commit_patches)
        obj._git_repo = repo  # for debug and info

        return obj

    def get_bug(self, bug_id: str) -> Bug:
        """Return specified bug

        :param bug_id: identifier of a bug in this dataset
        :returns: Bug instance
        """
        if self._dataset_path is not None:
            return Bug.from_dataset(self._dataset_path, bug_id,
                                    patches_dir=self._patches_dir,
                                    annotations_dir=self._annotations_dir,
                                    fan_out=self._fan_out)

        elif self._patches is not None:
            patch_set = self._patches[bug_id]
            return Bug.from_patchset(bug_id, patch_set)

        # TODO: log an error
        print(f"{self!r}: could not get bug with {bug_id=}")
        return Bug({})

    def iter_bugs(self) -> Iterator[Bug]:
        """Generate all bugs in the dataset, in annotated form

        Generator function, returning Bug after Bug from iteration
        to iteration.

        :return: bugs in the dataset
        """
        for bug_id in self.bug_ids:
            yield self.get_bug(bug_id)

    def __repr__(self):
        return f"{BugDataset.__qualname__}(bug_ids={self.bug_ids!r}, "\
               f"dataset_path={self._dataset_path!r}, patches_dict={self._patches!r})"

    # NOTE: alternative would be inheriting from `list`,
    # like many classes in the 'unidiff' library do
    def __iter__(self):
        """Iterate over bugs ids in the dataset"""
        return self.bug_ids.__iter__()

    def __len__(self) -> int:
        """Number of bugs in the dataset"""
        return len(self.bug_ids)

    def __getitem__(self, idx: int) -> str:
        """Get identifier of idx-th bug in the dataset"""
        return self.bug_ids[idx]

    def __contains__(self, item: str) -> bool:
        """Is bug with given id contained in the dataset?"""
        return item in self.bug_ids


# =========================================================================

app = typer.Typer(no_args_is_help=True, add_completion=False)


def get_version() -> str:
    """Return version of this script

    Use version from the 'diffannotator' package this script is from,
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


def version_callback(value: bool):
    if value:
        # TODO: extract the name from file docstring or variable
        typer.echo(f"Diff Annotator version: {get_version()}")
        raise typer.Exit()


def to_simple_mapping_callback(ctx: typer.Context, param: typer.CallbackParam,
                               values: Optional[List[str]],
                               mapping: Dict[str, str],
                               allow_simplified: bool = False):
    """Update given to simple `mapping` with '<key>:<value>'s

    If `allow_simplified` is true, and there is no ':' (colon) separating
    key from value, add the original both as key and as value.  This means
    that using '<value>' adds {<value>: <value>} mapping.

    If `allow_simplified` is false, and there is no ':' (colon) separating
    key from value, it ignores the value (with warning).

    On empty string it resets the whole mapping.

    :param ctx: Context object with additional data about the current
        execution of your program
    :param param: the specific Click Parameter object with information
        about the current parameter (argument or option)
    :param values: list of values to parse
    :param mapping: mapping to change
    :param allow_simplified: whether <value> means <value>:<value>,
        or just gets ignored
    :return: list of values, or empty list
    """
    # ctx.resilient_parsing will be True when handling completion
    if ctx.resilient_parsing:
        # this call is for handling command line completions, return early
        return []
    if values is None:
        return []

    # TODO: add logging
    for colon_separated_pair in values:
        if not colon_separated_pair or colon_separated_pair in {'""', "''"}:
            mapping.clear()
        elif ':' in colon_separated_pair:
            key, val = colon_separated_pair.split(sep=':', maxsplit=1)
            mapping[key] = val
        else:
            if allow_simplified:
                mapping[colon_separated_pair] = colon_separated_pair
            else:
                # TODO: use logging
                quotes = '\'"'  # work around limitations of f-strings in older Python
                print(f"Warning: {param.get_error_hint(ctx).strip(quotes)}="
                      f"{colon_separated_pair} ignored, no colon (:)")

    return values


def purpose_to_annotation_callback(ctx: typer.Context, param: typer.CallbackParam,
                                   values: Optional[List[str]]) -> List[str]:
    """Update purpose to annotation mapping with '<key>:<value>'s"""
    return to_simple_mapping_callback(ctx, param, values,
                                      mapping=PURPOSE_TO_ANNOTATION,
                                      allow_simplified=True)


def pattern_to_purpose_callback(ctx: typer.Context, param: typer.CallbackParam,
                                values: Optional[List[str]]) -> List[str]:
    """Update pattern to purpose mapping with '<key>:<value>'s"""
    return to_simple_mapping_callback(ctx, param, values,
                                      mapping=languages.PATTERN_TO_PURPOSE,
                                      allow_simplified=False)


# TODO: reduce code duplication (there is some similar code in purpose_to_annotation_callback)
def to_language_mapping_callback(ctx: typer.Context, param: typer.CallbackParam,
                                 values: Optional[List[str]],
                                 mapping: Dict[str, List[str]]) -> List[str]:
    """To create callback for providing to language mapping with '<key>:<value>'s

    If there is no ':' (colon) separating key from value,
    it ignores the value.

    On empty string it resets the whole mapping.

    Assumes that values in mapping are lists (following GitHub Linguist's
    languages.yml), and that getting value for a key that exists in the
    mapping replaces the whole list.

    :param ctx: Context object with additional data about the current
        execution of your program
    :param param: the specific Click Parameter object with information
        about the current parameter (argument or option)
    :param values: list of values to parse
    :param mapping: mapping to change
    """
    # ctx.resilient_parsing will be True when handling completion
    if ctx.resilient_parsing:
        # handling command line completions
        return []
    if values is None:
        return []

    # TODO: add logging
    for colon_separated_pair in values:
        if not colon_separated_pair or colon_separated_pair in {'""', "''"}:
            mapping.clear()
        elif ':' in colon_separated_pair:
            key, val = colon_separated_pair.split(sep=':', maxsplit=1)
            if key in mapping:
                # TODO: use logging
                print(f"Warning: changing mapping for {key} from {mapping[key]} to {[val]}")
            mapping[key] = [val]
        else:
            # TODO: use logging
            quotes = '\'"'  # work around limitations of f-strings in older Python
            print(f"Warning: {param.get_error_hint(ctx).strip(quotes)}={colon_separated_pair} ignored, no colon (:)")

    return values


def extension_to_language_callback(ctx: typer.Context, param: typer.CallbackParam,
                                   values: Optional[List[str]]) -> List[str]:
    """Update extension to language mapping with '<key>:<value>'s"""
    return to_language_mapping_callback(ctx, param, values,
                                        mapping=languages.EXT_TO_LANGUAGES)


def filename_to_language_callback(ctx: typer.Context, param: typer.CallbackParam,
                                  values: Optional[List[str]]) -> List[str]:
    """Update filename to language mapping with '<key>:<value>'s"""
    return to_language_mapping_callback(ctx, param, values,
                                        mapping=languages.FILENAME_TO_LANGUAGES)


def parse_line_callback(code_str: Optional[str]) -> Optional[LineCallback]:
    if code_str is None:
        return None

    # code_str might be the name of the file with the code
    maybe_path: Optional[Path] = Path(code_str)
    try:
        if maybe_path.is_file():
            code_str = maybe_path.read_text(encoding='utf-8')
        else:
            maybe_path = None
    except OSError:
        # there was an error trying to open file, perhaps invalid pathname
        maybe_path = None

    # code_str now contains the code as a string
    # maybe_path is not None only if code_str was retrieved from file

    # sanity check
    if 'return ' not in code_str:
        print("Error: there is no 'return' statement in --line-callback value")
        if maybe_path is not None:
            print(f"retrieved from '{maybe_path}' file")
        print(code_str)
        raise typer.Exit(code=1)

    try:
        line_callback = AnnotatedPatchedFile.make_line_callback(code_str)
    except SyntaxError as err:
        print("Error: there was syntax error in --line-callback value")
        if maybe_path is not None:
            print(f"retrieved from '{maybe_path}' file")
        print(code_str)

        raise err

    return line_callback


# implementing options common to all subcommands
@app.callback()
def common(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", "-V",
                     help="Output version information and exit.",
                     callback=version_callback, is_eager=True)
    ] = False,
    use_pylinguist: Annotated[
        bool,
        typer.Option(
            "--use-pylinguist",
            help="Use Python clone of github/linguist, if available."
        )
    ] = False,
    update_languages: Annotated[
        bool,
        typer.Option(help="Use own version of 'languages.yml'"),
    ] = True,
    ext_to_language: Annotated[
        Optional[List[str]],
        typer.Option(
            help="Mapping from extension to file language. Empty value resets mapping.",
            metavar="EXT:LANGUAGE",
            # uses callback instead of parser because of
            # AssertionError: List types with complex sub-types are not currently supported
            # see https://github.com/tiangolo/typer/issues/387
            callback=extension_to_language_callback,
        )
    ] = None,
    filename_to_language: Annotated[
        Optional[List[str]],
        typer.Option(
            help="Mapping from filename to file language. Empty value resets mapping.",
            metavar="FILENAME:LANGUAGE",
            callback=filename_to_language_callback,
        )
    ] = None,
    purpose_to_annotation: Annotated[
        Optional[List[str]],
        typer.Option(
            help="Mapping from file purpose to line annotation. Empty value resets mapping.",
            metavar="PURPOSE:ANNOTATION",
            # uses callback instead of parser because of
            # AssertionError: List types with complex sub-types are not currently supported
            # see https://github.com/tiangolo/typer/issues/387
            callback=purpose_to_annotation_callback,
        )
    ] = None,
    pattern_to_purpose: Annotated[
        Optional[List[str]],
        typer.Option(
            help="Mapping from pattern to match file path, to that file purpose. Empty value resets mapping.",
            metavar="PATTERN:PURPOSE",
            callback=pattern_to_purpose_callback,
        )
    ] = None,
    line_callback: Annotated[
        Optional[Callable[[Iterable[Tuple]], str]],
        typer.Option(
            help="Body for `line_callback(tokens)` callback function." + \
                 "  See documentation and examples.",
            metavar="CALLBACK",  # or "CODE|FILE"
            parser=parse_line_callback
        )
    ] = None
):
    global LANGUAGES
    # if anything is printed by this function, it needs to utilize context
    # to not break installed shell completion for the command
    # see https://typer.tiangolo.com/tutorial/options/callback-and-context/#fix-completion-using-the-context
    if ctx.resilient_parsing:
        return

    if version:  # this should never happen, because version_callback() exits the app
        print(f"Diff Annotator version: {get_version()}")
    if use_pylinguist:
        if has_pylinguist:
            print('Detecting languages from file name using Python clone of GitHub Linguist.')

            if update_languages:
                if isinstance(LANGUAGES, Languages):
                    languages_file = LANGUAGES.yaml
                else:
                    languages_file = Languages().yaml

                orig_size = Path(linguist.libs.language.LANGUAGES_PATH).stat().st_size
                updated_size = languages_file.stat().st_size
                print(f"Updating 'languages.yml' from version with {orig_size} bytes "
                      f"to version with {updated_size} bytes.")
                linguist.libs.language.LANGUAGES_PATH = languages_file
                linguist.libs.language.LANGUAGES = yaml.load(open(languages_file), Loader=yaml.FullLoader)

            LANGUAGES = LanguagesFromLinguist()
        else:
            print(dedent("""\
            The 'linguist' package is not installed.

            Use either
                python -m pip install --editable .[pylinguist]
                python -m pip install diffannotator[pylinguist]
            or
                python -m pip install git+https://github.com/retanoj/linguist@master

            NOTE that 'linguist' package requires 'charlockholmes' package,
            which in turn requires 'libmagic-dev' and 'libicu-dev' libraries.
            """))
            # TODO: use common enum for exit codes
            raise typer.Exit(code=1)

    if not update_languages and not use_pylinguist:
        print("Ignoring '--no-update-languages' option without '--use-pylinguist'")

    if ext_to_language is not None:
        if not languages.EXT_TO_LANGUAGES:
            print("Cleared mapping from file extension to programming language")
        else:
            print("Using modified mapping from file extension to programming language:")
        for ext, langs in languages.EXT_TO_LANGUAGES.items():
            # make sure that extension begins with a dot
            if not ext[0] == '.':
                # delete "<extension>", replace with ".<extension>"
                del languages.EXT_TO_LANGUAGES[ext]
                ext = f".{ext}"
                languages.EXT_TO_LANGUAGES[ext] = langs  # here `val` is a list

            # don't need to print `langs` as list, if there is only one element on it
            if len(langs) == 1:
                print(f"\t*{ext} is {langs[0]}")
            else:
                print(f"\t*{ext} in {langs}")

    # slight code duplication with previous block
    if filename_to_language is not None:
        if not languages.FILENAME_TO_LANGUAGES:
            print("Cleared mapping from filename to programming language")
        else:
            print("Using modified mapping from filename to programming language:")
        for filename, langs in languages.FILENAME_TO_LANGUAGES.items():
            # don't need to print `langs` as list, if there is only one element on it
            if len(langs) == 1:
                print(f"\t{filename} is {langs[0]}")
            else:
                print(f"\t{filename} in {langs}")

    if purpose_to_annotation is not None:
        print("Using modified mapping from file purpose to line annotation:")
        for purpose, annotation in PURPOSE_TO_ANNOTATION.items():
            print(f"\t{purpose}\t=>\t{annotation}")

    if pattern_to_purpose is not None:
        if not languages.PATTERN_TO_PURPOSE:
            print("Cleared modified mapping, defining file purpose based on pathname pattern.")
        else:
            print("Using modified mapping, defining file purpose based on pathname pattern:")

        warn_globstar = False
        for pattern, purpose in languages.PATTERN_TO_PURPOSE.items():
            print(f"\t{pattern} has purpose {purpose}")
            if '**' in pattern:
                warn_globstar = True

        if warn_globstar:
            print("Warning: the recursive wildcard “**” is not supported in patterns\n"
                  "         (it acts like non-recursive “*”.)")

    if line_callback is not None:
        print("Using custom line callback to perform line annotation")
        AnnotatedPatchedFile.line_callback = line_callback


@app.command()
def dataset(
    datasets: Annotated[
        List[Path],
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,  # to save results
        )
    ],
    output_prefix: Annotated[
        Optional[Path],
        typer.Option(
            file_okay=False,
            dir_okay=True,
            help="Where to save files with annotation data.",
        )
    ] = None,
    patches_dir: Annotated[
        str,
        typer.Option(
            metavar="DIR_NAME",
            help="Subdirectory with patches; use '' to do without such"
        )
    ] = Bug.DEFAULT_PATCHES_DIR,
    annotations_dir: Annotated[
        str,
        typer.Option(
            metavar="DIR_NAME",
            help="Subdirectory to write annotations to; use '' to do without such"
        )
    ] = Bug.DEFAULT_ANNOTATIONS_DIR,
    uses_fanout: Annotated[
        bool,
        typer.Option(
            help="Dataset was generated with fan-out"
        )
    ] = False,
) -> None:
    """Annotate all bugs in provided DATASETS

    Each DATASET is expected to be existing directory with the following
    structure, by default:

        <dataset_directory>/<bug_directory>/patches/<patch_file>.diff

    You can change the `/patches/` part with --patches-dir option.
    For example with --patches-dir='' the script would expect data
    to have the following structure:

        <dataset_directory>/<bug_directory>/<patch_file>.diff

    Each DATASET can consist of many BUGs, each BUG should include patch
    to annotate as *.diff file in 'patches/' subdirectory (or in subdirectory
    you provide via --patches-dir option).
    """
    for dataset_dir in datasets:
        print(f"Processing dataset in directory '{dataset_dir}'{' with fanout' if uses_fanout else ''}")
        bugs = BugDataset.from_directory(dataset_dir,
                                         patches_dir=patches_dir,
                                         annotations_dir=annotations_dir,
                                         fan_out=uses_fanout)

        output_path: Optional[Path] = None
        if output_prefix is not None:
            if dataset_dir.is_absolute():
                output_path = output_prefix.joinpath(dataset_dir.name)
            else:
                output_path = output_prefix.joinpath(dataset_dir)
            # ensure that directory exists
            output_path.mkdir(parents=True, exist_ok=True)

        print(f"Annotating patches and saving annotated data, for {len(bugs)} bugs")
        with logging_redirect_tqdm():
            for bug_id in tqdm.tqdm(bugs, desc='bug'):
                # NOTE: Uses default path if annotate_path is None
                bugs.get_bug(bug_id).save(annotate_dir=output_path)


@app.command()
def patch(patch_file: Annotated[Path, typer.Argument(exists=True, dir_okay=False,
                                                     help="unified diff file to annotate")],
          result_json: Annotated[Path, typer.Argument(dir_okay=False,
                                                      help="JSON file to write annotation to")]):
    """Annotate a single PATCH_FILE, writing results to RESULT_JSON"""
    print(f"Annotating '{patch_file}' file (expecting *.diff file)")
    result = annotate_single_diff(patch_file)

    if not result_json.parent.exists():
        print(f"Ensuring that '{result_json.parent}' directory exists")
        result_json.parent.mkdir(parents=True, exist_ok=True)

    print(f"Saving results to '{result_json}' JSON file")
    with result_json.open(mode='w') as result_f:
        json.dump(result, result_f, indent=4)


# TODO: reduce code duplication between this and generate_patches.py::main()
@app.command(
    # all unknown params will be considered arguments to `git log -p`
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def from_repo(
    repo_path: Annotated[
        Path,
        typer.Argument(
            exists=True,      # repository must exist
            file_okay=False,  # dropping corner case: gitdir file
            dir_okay=True,    # ordinarily Git repo is a directory
            readable=True,
            help="Path to git repository.",
        )
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            file_okay=False,  # cannot be ordinary file, if exists
            dir_okay=True,    # if exists, must be a directory
            help="Where to save generated annotated data.",
        )
    ],
    # TODO: find a way to add these to synopsis and list of arguments in help
    log_args: Annotated[
        typer.Context,
        typer.Argument(help="Arguments passed to `git log -p`", metavar="LOG_OPTIONS"),
    ],
    use_fanout: Annotated[
        bool,
        typer.Option(
            help="Use fan-out when saving annotation data"
        )
    ] = False,
    bugsinpy_layout: Annotated[
        bool,
        typer.Option(
            help="Create layout like the one in BugsInPy"
        )
    ] = False,
    annotations_dir: Annotated[
        str,
        typer.Option(
            metavar="DIR_NAME",
            help="Subdirectory to write annotations to; use '' to do without such"
        )
    ] = Bug.DEFAULT_ANNOTATIONS_DIR,
) -> None:
    """Create annotation data for commits from local Git repository

    You can add additional options and parameters, which will be passed to
    the `git log -p` command.  With those options and arguments you
    can specify which commits to operate on (defaults to all commits).\n
    See https://git-scm.com/docs/git-log or `man git-log` (or `git log -help`).

    When no <revision-range> is specified, it defaults to HEAD (i.e. the whole
    history leading to the current commit). origin..HEAD specifies all the
    commits reachable from the current commit (i.e. HEAD), but not from origin.
    For a complete list of ways to spell <revision-range>, see the
    "Specifying Ranges" section of the gitrevisions(7) manpage:\n
    https://git-scm.com/docs/gitrevisions#_specifying_revisions

    Note that --use-fanout and --bugsinpy-layout are mutually exclusive.
    """
    # sanity checks for options
    if use_fanout and bugsinpy_layout:
        print("Options --use-fanout and --bugsinpy-layout are mutually exclusive")
        raise typer.Exit(code=2)

    if annotations_dir != Bug.DEFAULT_ANNOTATIONS_DIR and not bugsinpy_layout:
        print(f"ignoring the value of --annotations-dir={annotations_dir}")
        print(f"no --bugsinpy-layout option present")

    # create GitRepo 'helper' object
    repo = GitRepo(repo_path)

    # ensure that output directory exists
    print(f"Ensuring that output directory '{output_dir}' exists")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating patches from local Git repo '{repo_path}'\n"
          f"  using `git log -p {' '.join([repr(arg) for arg in log_args.args])}`")
    beg_time = time.perf_counter()
    bugs = BugDataset.from_repo(repo, revision_range=log_args.args)
    end_time = time.perf_counter()
    print(f"  took {end_time - beg_time:0.4f} seconds")

    print(f"Annotating commits and saving annotated data, for {len(bugs)} commits")
    with logging_redirect_tqdm():
        for bug_id in tqdm.tqdm(bugs, desc='commits'):
            if bugsinpy_layout:
                bugs.get_bug(bug_id).save(annotate_dir=output_dir.joinpath(bug_id,
                                                                           annotations_dir))
            else:
                bugs.get_bug(bug_id).save(annotate_dir=output_dir, fan_out=use_fanout)


if __name__ == "__main__":
    app()

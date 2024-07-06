#!/usr/bin/env python

import collections.abc
from collections import defaultdict, deque
import json
import os
from pathlib import Path
import re
import traceback
from typing import List, Dict, Tuple, TypeVar, Optional
from typing import Iterable, Generator, Callable  # should be imported from collections.abc

from pygments.token import Token
import unidiff
import tqdm
import typer
from typing_extensions import Annotated  # in typing since Python 3.9

from .languages import Languages, FORCE_SIMPLIFY
from .lexer import Lexer


__version__ = "0.1.0"

T = TypeVar('T')
PathLike = TypeVar("PathLike", str, bytes, Path, os.PathLike)
LineCallback = Callable[[Iterable[Tuple]], str]
OptionalLineCallback = Optional[LineCallback]

PURPOSE_TO_ANNOTATION = {"documentation": "documentation"}
"""Defines when purpose of the file is propagated to line annotation, without parsing"""
TRANSLATION_TABLE = str.maketrans("", "", "*/\\\t\n")

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
            # TODO: replace commented out `print` with logging
            #print(f"{match.groupdict()=}")

            callback_name = match.group('func_name')
            callback_code_str = code_str
        else:
            # TODO: replace commented out `print` with logging
            #print(f"{code_str=}")

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
        self.patch_data = defaultdict(lambda: defaultdict(list))

        # save original diffutils.PatchedFile
        self.patched_file = patched_file

        # get the names and drop "a/" and "b/"
        self.source_file = patched_file.source_file
        self.target_file = patched_file.target_file

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

    def process(self):
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

    def add_line_annotation(self, line_no, source_file, target_file, change_type,
                            line_annotation, purpose, tokens):
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


def annotate_single_diff(diff_path: PathLike) -> dict:
    """Annotate single unified diff patch file at given path

    :param diff_path: patch filename
    :return: annotation data
    """
    patch_annotations = {}

    try:
        patch_set = unidiff.PatchSet.from_filename(diff_path, encoding="utf-8")
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
    """Represents single bug in dataset"""
    PATCHES_DIR = "patches"
    ANNOTATIONS_DIR = "annotation"

    def __init__(self, dataset_dir: PathLike, bug_id: str):
        """Constructor for class representing single Bug

        :dataset: path to the dataset
        :bug: bug id
        """
        self._dataset: Path = Path(dataset_dir)
        self._bug: str = bug_id
        self._path: Path = self._dataset.joinpath(self._bug, self.PATCHES_DIR)

        self.patches: dict = self._get_patches()
        self.changes: list = []

    def _get_patch(self, patch_file: PathLike) -> dict:
        """Get and annotate a single patch

        :param patch_file: basename of a patch
        :return: annotated patch data
        """
        patch_path = self._path.joinpath(patch_file)

        # Skip diffs between multiple versions
        if "..." in str(patch_path):
            return {}

        return annotate_single_diff(patch_path)

    def _get_patches(self) -> dict:
        patches_data = {}

        for patch_file in self._path.glob('*.diff'):
            patch_data = self._get_patch(patch_file.name)
            patches_data[patch_file.name] = patch_data

        return patches_data

    def save(self, annotate_path: Optional[PathLike] = None):
        """Save annotated patches in JSON format

        :param annotate_path: Separate dir to save annotations, optional.
            If not set, dataset path is used as a base path.
        """
        if annotate_path is not None:
            base_path = Path(annotate_path).joinpath(self._bug, self.ANNOTATIONS_DIR)
        else:
            base_path = self._dataset.joinpath(self._bug, self.ANNOTATIONS_DIR)

        # ensure that base_path exists in filesystem
        base_path.mkdir(parents=True, exist_ok=True)

        # save annotated patches data
        for patch_file, patch_data in self.patches.items():
            out_path = base_path / Path(patch_file).with_suffix('.json')

            with out_path.open('w') as out_f:
                json.dump(patch_data, out_f)


class BugDataset:
    """Bugs dataset class"""

    def __init__(self, dataset_dir: PathLike):
        """Constructor of bug dataset.

        :param dataset_dir: path to the dataset
        """
        self._path = Path(dataset_dir)
        self.bugs: List[str] = []

        try:
            self.bugs = [str(d.name) for d in self._path.iterdir()
                         if d.is_dir()]
        except Exception as ex:
            print(f"Error in BugDataset for '{self._path}': {ex}")

    def get_bug(self, bug_id: str) -> Bug:
        """Return specified bug

        :param bug_id: identifier of a bug in this dataset
        :returns: Bug instance
        """
        return Bug(self._path, bug_id)

    # NOTE: alternative would be inheriting from `list`,
    # like many classes in the 'unidiff' library do
    def __iter__(self):
        """Iterate over bugs ids in the dataset"""
        return self.bugs.__iter__()

    def __len__(self) -> int:
        """Number of bugs in the dataset"""
        return len(self.bugs)

    def __getitem__(self, idx: int) -> str:
        """Get idx-th bug in the dataset"""
        return self.bugs[idx]

    def __contains__(self, item: str) -> bool:
        """Is bug with given id contained in the dataset?"""
        return item in self.bugs


app = typer.Typer(no_args_is_help=True, add_completion=False)


def version_callback(value: bool):
    if value:
        # TODO: extract the name from file docstring or variable
        typer.echo(f"Diff Annotator version: {__version__}")
        raise typer.Exit()


def purpose_to_annotation_callback(values: Optional[List[str]]):
    """Update purpose to annotation mapping with '<key>:<value>'s

    If there is no ':' (colon) separating key from value, add
    the original both as key and as value.  This means that
    using '<value>' adds {<value>: <value>} mapping.

    On empty string it resets the whole mapping.

    :param values: list of values to parse
    """
    global PURPOSE_TO_ANNOTATION

    if values is None:
        return []

    # TODO: add logging
    for colon_separated_pair in values:
        if not colon_separated_pair or colon_separated_pair in {'""', "''"}:
            PURPOSE_TO_ANNOTATION = {}
        elif ':' in colon_separated_pair:
            key, val = colon_separated_pair.split(sep=':', maxsplit=1)
            PURPOSE_TO_ANNOTATION[key] = val
        else:
            PURPOSE_TO_ANNOTATION[colon_separated_pair] = colon_separated_pair

    return values


# TODO: reduce code duplication
def extension_to_language_callback(values: Optional[List[str]]):
    """Update extension to language mapping with '<key>:<value>'s

    If there is no ':' (colon) separating key from value,
    it ignores the value.

    On empty string it resets the whole mapping.

    :param values: list of values to parse
    """
    global FORCE_SIMPLIFY  # imported from the 'languages' module

    if values is None:
        return []

    # TODO: add logging
    for colon_separated_pair in values:
        if not colon_separated_pair or colon_separated_pair in {'""', "''"}:
            FORCE_SIMPLIFY = {}
        elif ':' in colon_separated_pair:
            key, val = colon_separated_pair.split(sep=':', maxsplit=1)
            if not key[0] == '.':
                key = f".{key}"
            FORCE_SIMPLIFY[key] = [val]
        else:
            # TODO: use logging
            print(f"Warning: --force-simplify={colon_separated_pair} ignored")

    return values


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
    # if anything is printed by this function, it needs to utilize context
    # to not break installed shell completion for the command
    # see https://typer.tiangolo.com/tutorial/options/callback-and-context/#fix-completion-using-the-context
    if ctx.resilient_parsing:
        return

    if version:  # this should never happen, because version_callback() exits the app
        print(f"Diff Annotator version: {__version__}")
    if ext_to_language is not None:
        print("Using modified mapping from file extension to programming language:")
        for key, val in FORCE_SIMPLIFY.items():
            if len(val) == 1:
                print(f"\t{key} is {val[0]}")
            else:
                print(f"\t{key} is {val}")
    if purpose_to_annotation is not None:
        print("Using modified mapping from file purpose to line annotation:")
        for key, val in PURPOSE_TO_ANNOTATION.items():
            print(f"\t{key}\t=>\t{val}")
    if line_callback is not None:
        print("Using custom line callback to perform line annotation")
        AnnotatedPatchedFile.line_callback = line_callback


@app.command()
def dataset(datasets: Annotated[
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
            ] = None):
    """Annotate all bugs in provided DATASETS

    Each DATASET is expected to be existing directory with the following
    structure:

        <dataset_directory>/<bug_directory>/patches/<patch_file>.diff

    Each DATASET can consist of many BUGs, each BUG should include patch
    to annotate as *.diff file in 'patches/' subdirectory.
    """
    for dataset_dir in datasets:
        print(f"Dataset {dataset_dir}")
        bugs = BugDataset(dataset_dir)

        output_path: Optional[Path] = None
        if output_prefix is not None:
            if dataset_dir.is_absolute():
                output_path = output_prefix.joinpath(dataset_dir.name)
            else:
                output_path = output_prefix.joinpath(dataset_dir)
            # ensure that directory exists
            output_path.mkdir(parents=True, exist_ok=True)

        for bug in tqdm.tqdm(bugs):
            # NOTE: Uses default path if annotate_path is None
            bugs.get_bug(bug).save(annotate_path=output_path)


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


if __name__ == "__main__":
    app()

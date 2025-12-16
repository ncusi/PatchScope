# -*- coding: utf-8-unix -*-
"""Utilities to get data out of git repositories.

This file defines a base class, `GitRepo`, which uses straight-up
calling git commands, and needs Git to be installed.

Usage:
------
Example usage:
  >>> from diffannotator.utils.git import GitRepo
  >>> files = GitRepo('path/to/git/repo').list_files('HEAD')  # 'HEAD' is the default
  ...     ...

This implementation / backend retrieves data by calling `git` via
`subprocess.Popen` or `subprocess.run`, and parsing the output.

WARNING: at the time this backend does not have error handling implemented;
it would simply return empty result, without any notification about the
error (like incorrect repository path, or incorrect commit)!!!
"""
import functools
import logging
import os
import re
import subprocess
import weakref
from collections import defaultdict
from contextlib import contextmanager
from enum import Enum, StrEnum
from io import StringIO, BufferedReader, TextIOWrapper
from operator import attrgetter
from pathlib import Path
from typing import Optional, Union, TypeVar, Literal, overload, NamedTuple, TextIO
from collections.abc import Iterable, Iterator

import unidiff
from unidiff import PatchSet, DEFAULT_ENCODING
from unidiff.patch import Line as PatchLine
from unidiff.patch import PatchedFile


# support logging
logger = logging.getLogger(__name__)

# TODO: move to __init__.py (it is common to all scripts)
PathLike = TypeVar("PathLike", str, bytes, Path, os.PathLike)

ENCODING_ERRORS= 'backslashreplace'


class DiffSide(Enum):
    """Enum to be used for `side` parameter of `GitRepo.list_changed_files`"""
    PRE = 'pre'
    POST = 'post'
    A = 'pre'
    B = 'post'


class StartLogFrom(Enum):
    """Enum to be used for special cases for starting point of 'git log'"""
    CURRENT = 'HEAD'
    HEAD = 'HEAD'  # alias
    ALL = '--all'


class AuthorStat(NamedTuple):
    """Parsed result of 'git shortlog -c -s'"""
    author: str  #: author name (commit authorship info)
    count: int = 0  #: number of commits per author


class ChangeSet(PatchSet):
    """Commit changes, together with commit data

    Note that changeset can come from a commit, or from a diff
    between two different commits (tree-ish)
    """
    RE_DIFF_GIT_HEADER_GENERIC = re.compile(
        pattern=r'^diff --git [^\t\n]+ [^\t\n]+',
        flags=re.MULTILINE
    )
    RE_ALL_SHA1_FULL = re.compile(r'^[0-9a-f]{40}$')
    # TODO: support SHA-256 object names
    # https://git-scm.com/docs/hash-function-transition

    def __init__(self, patch_source: Union[StringIO, TextIO, str], commit_id: str,
                 prev: Optional[str] = None, newline: Optional[str] = '\n',
                 *args, **kwargs):
        """ChangeSet class constructor

        Parameters
        ----------
        patch_source
            patch source to be parsed by PatchSet (parent class)
        commit_id
            oid of the "after" commit (tree-ish) for the change
        prev
            previous state, when ChangeSet is generated with .unidiff(),
            or `None` it the change corresponds to a commit (assumed
            first-parent)
        newline
            determines how to parse newline characters from the stream,
            and how the stream was opened (one of None i.e. universal
            newline, '', '\\n', '\\r', and '\\r\\n' - same as `open`)
        *args
            passed to PatchSet constructor
        **kwargs
            passed to PatchSet constructor (recommended); PatchSet uses
            `encoding` (str) and `metadata_only` (bool)

            if `encoding` is `None`, assume we are reading Unicode
            data, when `metadata_only` is `True`, only perform a minimal
            metadata parsing (i.e. hunks without content) which is
            around 2.5-6 times faster; it will still validate the diff
            metadata consistency and get counts
        """
        # with universal newline you don't need to do translation, because it is already done
        # with '\n' as newline you don't need to do translation, because it has correct EOLs
        # this means that `newline` can be '\r' or '\r\n'
        if newline is not None and newline != '\n':
            # TODO: create a proper wrapper around io.StringIO.readline()
            if isinstance(patch_source, StringIO):
                patch_source = patch_source.getvalue()
            elif isinstance(patch_source, TextIOWrapper):
                patch_source = patch_source.read()
            patch_source = StringIO(patch_source.replace(newline, '\n'))

        super().__init__(patch_source, *args, **kwargs)
        self.commit_id = commit_id
        self.prev = prev

        # retrieve commit metadata from patch, if possible
        self.commit_metadata: Optional[dict] = None
        if prev is None or prev.endswith("^"):
            if isinstance(patch_source, StringIO):
                patch_source.seek(0)
                patch_text = patch_source.getvalue()
            elif isinstance(patch_source, TextIOWrapper):
                patch_source.seek(0)
                patch_text = patch_source.read()
            else:
                patch_text = patch_source
            match = re.search(self.RE_DIFF_GIT_HEADER_GENERIC,
                              patch_text)
            if match:
                pos = match.start()
                commit_text = patch_text[:pos]
                # -1 is to remove newline from empty line separating commit text from diff
                self.commit_metadata = _parse_commit_text(commit_text[:-1],
                                                          with_parents_line=False)

    # override
    @classmethod
    def from_filename(cls, filename: Union[str, Path], encoding: str = DEFAULT_ENCODING,
                      errors: Optional[str] = ENCODING_ERRORS, newline: Optional[str] = '\n') -> 'ChangeSet':
        """Return a ChangeSet instance given a diff filename.

        Parameters
        ----------
        filename
            path to a diff file with the patch to parse
        encoding
            the name of the encoding used to decode or encode the diff
            file
        errors
            specifies how encoding and decoding errors are to be handled
            (one of None, 'strict', 'ignore', 'replace',
            'backslashreplace', or 'surrogateescape' - same as `open`)
        newline
            determines how to parse newline characters from the stream
            (one of None, '', '\\n', '\\r', and '\\r\\n' - same as `open`)

        Returns
        -------
        ChangeSet
            instance of ChangeSet class
        """
        # NOTE: unconditional `file_path = Path(filename)` would also work
        if isinstance(filename, Path):
            file_path = filename
        else:
            file_path = Path(filename)

        # try to extract commit_id from basename of the file, for example
        # from filename == 'e54746bdf7d5c831eabe4dcea76a7626f1de73df.diff'
        commit_id = ''
        base_name = file_path.stem
        if re.fullmatch(cls.RE_ALL_SHA1_FULL, base_name):
            commit_id = base_name

        # slightly modified contents of PatchSet.from_filename() alternate constructor
        with file_path.open(mode='r', encoding=encoding, errors=errors, newline=newline) as fp:
            obj = cls(fp, commit_id=commit_id, newline=newline)  # PatchSet.from_filename() has type mismatch

        # adjust commit_id if we were able to retrieve commit metadata from file
        if commit_id != '' and obj.commit_metadata is not None:
            obj.commit_id = obj.commit_metadata['id']

        return obj

    # TODO: patch unidiff.PatchedFile or create subclass from it instead


RE_DIFF_GIT_EXTENDED_HEADER_INDEX_MODE = re.compile(
    # e.g. 'index 7898192..6178079 100644'
    pattern=r'^index (?P<sha_src>[0-9a-f]+)\.\.(?P<sha_dst>[0-9a-f]+) (?P<mode>[0-9]{6})',
    flags=re.MULTILINE,
)
RE_DIFF_GIT_EXTENDED_HEADER_MODE = re.compile(
    # e.g. 'new mode 100644' or 'old mode 100755', or 'new file mode 100644'
    pattern=r'^(?P<side>new|old) (?:file )?mode (?P<mode>[0-9]{6})',
    flags=re.MULTILINE,
)


class GitFileMode(StrEnum):
    """Enumeration of file modes in git diff

    To be used to compare the result of `get_patched_file_mode()` function
    against, to check whether the file is a regular file, an executable file,
    a symlink, or a submodule.
    """
    REGULAR = '100644'
    NORMAL = '100644'
    EXECUTABLE = '100755'
    SYMLINK = '120000'
    SUBMODULE = '160000'


def get_patched_file_mode(patched_file: PatchedFile,
                          side: DiffSide = DiffSide.POST) -> str|None:
    """Extract pre- or post-image mode of a changed file from git diff, if possible

    This function examines the extended git diff header of a given PatchedFile
    in a PatchSet or ChangeSet created out of a git patch, in order to extract
    the mode of the pre- or post-image of a changed file (according to the `side`
    argument).

    If there is not enough information in the header (for example if PatchSet
    was created from unified diff, and not from git diff), it returns None.

    Parameters
    ----------
    patched_file
        unidiff.patch.PatchedFile element of unidiff.PatchSet or of ChangeSet,
        i.e., the result of parsing of a patch (of a unified diff) with unidiff
        library.
    side
        enum that select whether to return pre- or post-image mode.

    Returns
    -------
    str | None
        Extended file mode in octal: '100644' for normal files, '100755' for
        executable files (`git add --chmod=+x`), '120000' for symlink,
        and '160000' for submodule, or `None` if there is not enough information
        to determine the `patched_file` mode.
    """
    if not patched_file.patch_info:
        return None

    for line in patched_file.patch_info:
        match = re.match(pattern=RE_DIFF_GIT_EXTENDED_HEADER_MODE, string=line)
        if match:
            if side == DiffSide.PRE and match.group('side') == 'old':
                return match.group('mode')
            elif side == DiffSide.POST and match.group('side') == 'new':
                return match.group('mode')

        match = re.match(pattern=RE_DIFF_GIT_EXTENDED_HEADER_INDEX_MODE, string=line)
        if match:
            return match.group('mode')

    return None


def _parse_authorship_info(authorship_line: str,
                           field_name: str = 'author') -> dict[str, Union[str, int]]:
    """Parse author/committer info, and extract individual parts

    Extract author or committer 'name', 'email', creation time of changes
    or commit as 'timestamp', and timezone information ('tz_info') from
    authorship line, for example:

        Jakub Narębski <jnareb@mat.umk.pl> 1702424295 +0100

    Requires raw format; it does not parse any other datetime format
    than UNIX timestamp.

    Parameters
    ----------
    authorship_line : str
        string with authorship info to parse
    field_name : str
        name of field to store 'name'+'email' (for example "Jakub
        Narębski <jnareb@mat.umk.pl>"), should be either 'author' or
        'committer'.

    Returns
    -------
    dict[str, str | int]
        dict with parsed authorship information
    """
    # trick from https://stackoverflow.com/a/279597/
    if not hasattr(_parse_authorship_info, 'regexp'):
        # runs only once
        _parse_authorship_info.regexp = re.compile(r'^((.*) <(.*)>) ([0-9]+) ([-+][0-9]{4})$')

    m = _parse_authorship_info.regexp.match(authorship_line)
    authorship_info = {
        field_name: m.group(1),
        'name': m.group(2),
        'email': m.group(3),
        'timestamp': int(m.group(4)),
        'tz_info': m.group(5),
    }

    return authorship_info


def _parse_commit_text(commit_text: str, with_parents_line: bool = True,
                       indented_body: bool = True) -> Optional[dict[str, Union[str, dict, list[str]]]]:
    """Helper function for GitRepo.get_commit_metadata()

    The default values of `with_parents_line` and `indented_body` parameters
    are selected for parsing output of 'git rev-list --parents --header'
    (that is used by GitRepo.get_commit_metadata()).

    Parameters
    ----------
    commit_text : str
        text to parse
    with_parents_line : bool
        whether first line of `commit_text` is '<commit id> [<parent
        id>...]' line
    indented_body : bool
        whether commit message text is prefixed (indented) with 4
        spaces: '    '

    Returns
    -------
    dict[str, str | list[str] | dict] or None
        commit metadata extracted from parsed `commit_text`
    """
    # based on `parse_commit_text` from gitweb/gitweb.perl in git project
    # NOTE: cannot use .splitlines() here
    if '\r\n' in commit_text:
        # in case commit_text came from a patch file with CRLF line endings
        commit_text = commit_text.replace('\r\n', '\n')
    commit_lines = commit_text.split('\n')[:-1]  # remove trailing '' after last '\n'

    if not commit_lines:
        return None

    commit_data = {'parents': []}  # each commit has 0 or more parents

    if with_parents_line:
        parents_data = commit_lines.pop(0).split(' ')
        commit_data['id'] = parents_data[0]
        commit_data['parents'] = parents_data[1:]

    # commit metadata
    line_no = 0
    in_gpgsig = False
    for (idx, line) in enumerate(commit_lines):
        if in_gpgsig:
            if line == ' -----END PGP SIGNATURE-----':
                in_gpgsig = False
            continue

        if line == '':
            line_no = idx
            break

        if 'id' not in commit_data and line.startswith('commit '):
            commit_data['id'] = line[len('commit '):]
        if line.startswith('tree '):
            commit_data['tree'] = line[len('tree '):]
        if not with_parents_line and line.startswith('parent'):
            commit_data['parents'].append(line[len('parent '):])
        for field in ('author', 'committer'):
            if line.startswith(f'{field} '):
                commit_data[field] = _parse_authorship_info(line[len(f'{field} '):], field)
        if line.startswith('gpgsig '):
            in_gpgsig = True

    # commit message
    commit_data['message'] = ''
    for line in commit_lines[line_no+1:]:
        if indented_body:
            line = line[4:]  # strip starting 4 spaces: 's/^    //'

        commit_data['message'] += line + '\n'

    return commit_data


def _parse_blame_porcelain(blame_text: str) -> tuple[dict, list]:
    """Parse 'git blame --porcelain' output and extract information

    In the porcelain format, each line is output after a header; the header
    at the minimum has the first line which has:
     - 40-byte SHA-1 of the commit the line is attributed to;
     - the line number of the line in the original file;
     - the line number of the line in the final file;
     - on a line that starts a group of lines from a different commit
       than the previous one, the number of lines in this group.
       On subsequent lines this field is absent.

    This header line is followed by the following information at least once
    for each commit:
     - the author name ("author"), email ("author-mail"), time ("author-time"),
       and time zone ("author-tz"); similarly for committer.
     - the filename ("filename") in the commit that the line is attributed to.
     - the first line of the commit log message ("summary").

    Additionally, the following information may be present:
     - "previous" line with 40-byte SHA-1 of commit previous to the one that
       the line is attributed to, if there is any (this is parent commit for
       normal blame, and child commit for reverse blame), and the filename
       in this 'previous' commit

    Note that without '--line-porcelain' information about specific commit
    is provided only once.

    Parameters
    ----------
    blame_text : str
        standard output from running the 'git blame --porcelain
        [--reverse]' command

    Returns
    -------
    (dict, list)
        information about commits (dict) and information about lines
        (list)
    """
    # trick from https://stackoverflow.com/a/279597/
    if not hasattr(_parse_blame_porcelain, 'regexp'):
        # runs only once
        _parse_blame_porcelain.regexp = re.compile(r'^(?P<sha1>[0-9a-f]{40}) (?P<orig>[0-9]+) (?P<final>[0-9]+)')

    # https://git-scm.com/docs/git-blame#_the_porcelain_format
    blame_lines = blame_text.splitlines()
    if not blame_lines:
        # TODO: return NamedTuple
        return {}, []

    curr_commit = None
    curr_line = {}
    commits_data = {}
    line_data = []

    for line in blame_lines:
        if not line:  # empty line, shouldn't happen
            continue

        if match := _parse_blame_porcelain.regexp.match(line):
            curr_commit = match.group('sha1')
            curr_line = {
                'commit': curr_commit,
                'original': match.group('orig'),
                'final': match.group('final')
            }
            if curr_commit in commits_data:
                curr_line['original_filename'] = decode_c_quoted_str(commits_data[curr_commit]['filename'])

                # TODO: move extracting 'previous_filename' here, unquote if needed

        elif line.startswith('\t'):  # TAB
            # the contents of the actual line
            curr_line['line'] = line[1:]  # remove leading TAB
            line_data.append(curr_line)

        else:
            # other header
            if curr_commit not in commits_data:
                commits_data[curr_commit] = {}
            try:
                # e.g. 'author A U Thor'
                key, value = line.split(' ', maxsplit=1)
            except ValueError:
                # e.g. 'boundary'
                key, value = (line, True)
            commits_data[curr_commit][key] = value
            # add 'filename' as 'original_filename' to line info
            if key == 'filename':
                commits_data[curr_commit][key] = decode_c_quoted_str(value)
                curr_line['original_filename'] = decode_c_quoted_str(value)

    return commits_data, line_data


def parse_shortlog_count(shortlog_lines: list[Union[str, bytes]]) -> list[AuthorStat]:
    """Parse the result of GitRepo.list_authors_shortlog() method

    Parameters
    ----------
    shortlog_lines : str or bytes
        result of list_authors_shortlog()

    Returns
    -------
    list[AuthorStat]
        list of parsed statistics, number of commits per author
    """
    result = []
    for line in shortlog_lines:
        count, author = line.split('\t' if isinstance(line, str) else b'\t', maxsplit=1)
        count = int(count.strip())
        result.append(AuthorStat(author, count))

    return result


def select_core_authors(authors_stats: list[AuthorStat],
                        perc: float = 0.8) -> tuple[list[AuthorStat], float]:
    """Select sorted list of core authors from `authors_list`

    Core authors are defined (like in World of Code) as those authors with
    the greatest contribution count whose contribution sum up to more than
    given `perc` fraction of contributions from all authors.  Usually
    number of contributions comes from 'git shortlog', and counts commits.

    This function returns a tuple.  First element is list of `AuthorStat`
    named tuples, sorted by `count` field in decreasing order, so that their
    contribution is minimal that covers `perc` fraction of all commits.
    If there is tie at the last element, all tied authors are included.
    Second element is actual fraction of all commits that selected authors'
    contributions covers.

    We have len(result[0]) <= len(authors_stats), and perc <= result[1].

    Parameters
    ----------
    authors_stats:
        all authors and their contribution statistics,
        for example result of feeding the result of list_authors_shortlog()
        method fed to parse_shortlog_count() function
    perc:
        fraction threshold for considering author a core author,
        assumed to be 0.0 <= `perc` <= 1.0 (not checked!)

    Returns
    -------
    list[AuthorStat], float
        list of core authors, and cumulative fraction of contributions
        of returned authors
    """
    authors_stats.sort(key=attrgetter('count'), reverse=True)
    total_commits = sum([auth.count
                         for auth in authors_stats])

    result = []
    idx = 0
    running_total = 0
    for idx, auth in enumerate(authors_stats):
        result.append(auth)
        running_total += auth.count
        if running_total > perc*total_commits:
            break

    # handle ex aequo situation (draw / tie)
    last_count = authors_stats[idx].count
    for auth in authors_stats[idx+1:]:
        if auth.count == last_count:
            running_total += auth.count
            result.append(auth)
        else:
            break

    return result, running_total/total_commits


def changes_survival_perc(lines_survival: dict[str, list[dict]]) -> tuple[int, int]:
    """Count fraction of surviving lines from GitRepo.changes_survival() output

    Parameters
    ----------
    lines_survival:
        the second element in tuple returned by `GitRepo.changes_survival()`
        method

    Returns
    -------
    (int, int)
        number of surviving lines and total number of lines
    """
    lines_total = 0
    lines_survived = 0
    for _, lines_info in lines_survival.items():
        lines_total += len(lines_info)
        lines_survived += sum(1 for line_data in lines_info
                              if 'previous' not in line_data)

    return lines_survived, lines_total


def decode_c_quoted_str(text: str) -> str:
    """C-style name unquoting

    See unquote_c_style() function in 'quote.c' file in git/git source code
    https://github.com/git/git/blob/master/quote.c#L401

    This is subset of escape sequences supported by C and C++
    https://learn.microsoft.com/en-us/cpp/c-language/escape-sequences

    Parameters
    ----------
    text : str
        string which may be c-quoted

    Returns
    -------
    str
        decoded string
    """
    # TODO?: Make it a global variable
    escape_dict = {
        'a': '\a',  # Bell (alert)
        'b': '\b',  # Backspace
        'f': '\f',  # Form feed
        'n': '\n',  # New line
        'r': '\r',  # Carriage return
        't': '\t',  # Horizontal tab
        'v': '\v',  # Vertical tab
    }

    quoted = text.startswith('"') and text.endswith('"')
    if quoted:
        text = text[1:-1]  # remove quotes

        buf = bytearray()
        escaped = False  # TODO?: switch to state = 'NORMAL', 'ESCAPE', 'ESCAPE_OCTAL'
        oct_str = ''

        for ch in text:
            if not escaped:
                if ch != '\\':
                    buf.append(ord(ch))
                else:
                    escaped = True
                    oct_str = ''
            else:
                if ch in ('"', '\\'):
                    buf.append(ord(ch))
                    escaped = False
                elif ch in escape_dict:
                    buf.append(ord(escape_dict[ch]))
                    escaped = False
                elif '0' <= ch <= '7':  # octal values with first digit over 4 overflow
                    oct_str += ch
                    if len(oct_str) == 3:
                        byte = int(oct_str, base=8)  # byte in octal notation
                        if byte > 256:
                            raise ValueError(f'Invalid octal escape sequence \\{oct_str} in "{text}"')
                        buf.append(byte)
                        escaped = False
                        oct_str = ''
                else:
                    raise ValueError(f'Unexpected character \'{ch}\' in escape sequence when parsing "{text}"')

        if escaped:
            raise ValueError(f'Unfinished escape sequence when parsing "{text}"')

        text = buf.decode(errors=ENCODING_ERRORS)

    return text


def maybe_close_subprocess(process: Optional[subprocess.Popen]) -> None:
    """Closes a subprocess safely to avoid resource warnings and resource starvation

    This function ensures the safe termination of a subprocess by properly closing its
    standard input and output streams, waiting for it to exit, and forcefully
    killing it if necessary. It is designed to handle `git cat-file --batch-command`
    and similar persistent subprocesses.

    It is designed to be used as a ` weakref.finalize ` callback.

    Parameters
    ----------
    process
        The subprocess instance to close. If None, the function does nothing.
    """
    if process is None:
        return

    # closing stdin and stdout should end the persistent `git cat-file` process
    process.stdout.close()  # to avoid ResourceWarning: unclosed file <_io.BufferedReader name=3>
    process.stdin.close()  # just in case, see above
    process.wait()  # to avoid ResourceWarning: subprocess NNN is still running
    process.kill()  # just in case


class GitRepo:
    """Class representing Git repository, for performing operations on

    Attributes
    ----------
    repo : Path
        stores Path to the Git repository
    """
    path_encoding = 'utf8'
    default_file_encoding = 'utf8'
    log_encoding = 'utf8'
    fallback_encoding = 'latin1'  # must be 8-bit encoding
    encoding_errors = ENCODING_ERRORS
    # see 346245a1bb ("hard-code the empty tree object", 2008-02-13)
    # https://github.com/git/git/commit/346245a1bb6272dd370ba2f7b9bf86d3df5fed9a
    # https://github.com/git/git/commit/e1ccd7e2b1cae8d7dab4686cddbd923fb6c46953
    empty_tree_sha1 = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'

    def __init__(self, repo_dir: PathLike):
        """Constructor for `GitRepo` class

        Parameters
        ----------
        repo_dir
            path to the Git repository
        """
        # TODO: check that `git_directory` is a path to git repository
        # TODO: remember absolute path (it is safer)
        self.repo = Path(repo_dir)
        self._cat_file: Optional[subprocess.Popen] = None
        self._finalizer = weakref.finalize(self, maybe_close_subprocess, self._cat_file)

    def __repr__(self):
        class_name = type(self).__name__
        return f"{class_name}(repo_dir={self.repo!r})"

    def __str__(self):
        return f"{self.repo!s}"

    @classmethod
    def clone_repository(cls,
                         repository: PathLike,
                         directory: Optional[PathLike] = None,
                         working_dir: Optional[PathLike] = None,
                         reference_local_repository: Optional[PathLike] = None,
                         dissociate: bool = False,
                         make_path_absolute: bool = False) -> Union['GitRepo', None]:
        """Clone a repository into a new directory, return cloned GitRepo

        If there is non-empty directory preventing from cloning the repository,
        the method assumes that it is because the repository was already cloned;
        in this case it returns that directory as `GitRepo`.

        Parameters
        ----------
        repository
            The (possibly remote) repository to clone from, usually a
            URL (ssh, git, http, or https) or a local path.
        directory
            The name of a new directory to clone into, optional. The
            "human-ish" part of the source repository is used if
            `directory` is not provided (if it is `None`).
        working_dir
            The directory where to run the `git-clone https://git-
            scm.com/docs/git-clone` operation; otherwise current working
            directory is used.  The value of this parameter does not
            matter if `directory` is provided,
        reference_local_repository
            Use `reference_local_repository` to avoid network transfer,
            and to reduce local storage costs
        dissociate
            whether to dissociate with `reference_local_repository`,
            used only if `reference_local_repository` is not None
        make_path_absolute
            Ensure that returned `GitRepo` uses absolute path

        Returns
        -------
        Optional[GitRepo]
            Cloned repository as `GitRepo` if operation was successful,
            otherwise `None`.
        """
        # TODO: make it @classmethod (to be able to use in constructor)
        def _to_repo_path(a_path: str) -> PathLike:
            if make_path_absolute:
                if Path(a_path).is_absolute():
                    return a_path
                else:
                    return Path(working_dir or '').joinpath(a_path).absolute()

            return a_path

        args = ['git']
        if working_dir is not None:
            args.extend(['-C', str(working_dir)])
        if reference_local_repository:
            args.extend([
                'clone', f'--reference-if-able={reference_local_repository}'
            ])
            if dissociate:
                args.append('--dissociate')
            args.append(repository)
        else:
            args.extend([
                'clone', repository
            ])
        if directory is not None:
            args.append(str(directory))

        # https://serverfault.com/questions/544156/git-clone-fail-instead-of-prompting-for-credentials
        env = {
            'GIT_TERMINAL_PROMPT': '0',
            'GIT_SSH_COMMAND': 'ssh -oBatchMode=yes',
            'GIT_ASKPASS': 'echo',
            'SSH_ASKPASS': 'echo',
            'GCM_INTERACTIVE': 'never',
        }

        result = subprocess.run(args, capture_output=True, env=env)
        if result.returncode == 128:
            # TODO: log a warning about the problem
            #print(f"{result.stderr=}")
            # try again without environment variables, in case of firewall problem like
            # fatal: unable to access 'https://github.com/githubtraining/hellogitworld.git/':
            #        getaddrinfo() thread failed to start
            result = subprocess.run(args, capture_output=True)

        # we are interested only in the directory where the repository was cloned into
        # that's why we are using GitRepo.path_encoding (instead of 'utf8', for example)

        if result.returncode == 128:
            # repository was already cloned
            for line in result.stderr.decode(GitRepo.path_encoding).splitlines():
                match = re.match(r"fatal: destination path '(.*)' already exists and is not an empty directory.", line)
                if match:
                    return GitRepo(_to_repo_path(match.group(1)))

            # could not find where repository is
            return None

        elif result.returncode != 0:
            # other error
            return None

        for line in result.stderr.decode(GitRepo.path_encoding).splitlines():
            match = re.match(r"Cloning into '(.*)'...", line)
            if match:
                return GitRepo(_to_repo_path(match.group(1)))

        return None

    def checkout_revision(self, commit: str) -> None:
        """Check out given commit in a given repository

        This would usually (and for some cases always) result in
        'detached HEAD' situation, that is HEAD reference pointing
        directly to a commit, and not being on any named branch.

        This function is called for its effects and does return nothing.

        Notes
        -----
        Changes the repository, and therefore requires write access
        to the repository.

        Parameters
        ----------
        commit:
            The commit to check out in given repository.
        """
        cmd = [
            'git', '-C', self.repo, 'checkout', '-q', commit,
        ]
        # we are interested in effects of the command, not its output
        subprocess.run(cmd, stdout=subprocess.DEVNULL, check=True)

    @property
    def batch_command(self) -> subprocess.Popen:
        """Persistent connection to `git cat-file --batch-command --buffer`

        In `--batch-command` mode, `git cat-file` will read commands from stdin,
        one per line, and print information based on the command given.  Namely,
        the 'info' command followed by an object will print information about
        the object the same way `--batch-check` would, and the 'contents' command
        followed by an object prints contents in the same way `--batch` would.

        Because the `--buffer` option is used, you can send multiple commands
        in a batch, and you must end the input with the 'flush' command.
        This is more efficient when running 'info' or 'object' commands
        on large number of objects.

        TODO: make the use of `--buffer` option configurable (make it method, not property).

        Returns
        -------
        subprocess.Popen
            Persistent (cached) connection to the `git cat-file`
            in the `--batch-command` mode, buffered (because of `--buffer`),
            see https://git-scm.com/docs/git-cat-file
        """
        ## DEBUG
        print(f"{self}.batch_command: ", end="")
        if self._cat_file is not None:
            ## DEBUG
            print(f"returning cached connection {self._cat_file!r}")
            return self._cat_file

        self._cat_file = subprocess.Popen(
            [
                'git', '-C', str(self.repo),
                'cat-file', '--batch-command', '--buffer',
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # silence errors, e.g., "error: short object ID dedf is ambiguous"
            text=True,
            bufsize=1,  # line buffered
        )
        ## DEBUG
        print(f"created new connection {self._cat_file!r}")
        return self._cat_file

    def close_batch_command(self) -> None:
        """Close persistent connection to `git cat-file --batch-command --buffer`

        Note that any access to the `.batch_command` property will re-create
        the connection by starting a new persistent ` git cat-file ` process.
        The `.are_valid_objects()` and `.filter_valid_commits()` methods
        access the `.batch_command` property internally, so they would do
        the same.
        """
        self._finalizer()
        self._cat_file = None

    def format_patch(self,
                     output_dir: Optional[PathLike] = None,
                     revision_range: Union[str, Iterable[str]] = ('-1', 'HEAD')) -> str:
        """Generate patches out of specified revisions, saving them as individual files

        Parameters
        ----------
        output_dir
            output directory for patches; if not set (the default), save
            patches in the current working directory
        revision_range
            arguments to pass to `git format-patch`,
            see https://git-scm.com/docs/git-format-patch;
            by default generates single patch from the HEAD

        Returns
        -------
        str
            output from the `git format-patch` process
        """
        # NOTE: it should be ':param \*args' or ':param \\*args', but for the bug in PyCharm
        cmd = [
            'git', '-C', str(self.repo),
            'format-patch'
        ]
        if output_dir is not None:
            cmd.extend([
                '--output-directory', str(output_dir)
            ])
        if isinstance(revision_range, str):
            cmd.append(revision_range)
        else:
            cmd.extend(revision_range)

        # NOTE: specifying `encoding` or `errors` turns on `text` == `universal_newlines`
        # and you cannot say `text=False` and/or `universal_newlines=False` to turn it off
        # The output of the `git format-patch` command can contain embedded `\r` (CR)
        process = subprocess.run(cmd,
                                 capture_output=True, check=True)
        # MAYBE: better checks for process.returncode, and examine process.stderr
        if process.returncode == 0:
            return process.stdout.decode(encoding='utf-8', errors=self.encoding_errors)
        else:
            return process.stderr.decode(encoding='utf-8', errors=self.encoding_errors)

    def list_files(self, commit: str = 'HEAD') -> list[str]:
        """Retrieve list of files at given revision in a repository

        Parameters
        ----------
        commit : str
            The commit for which to list all files.  Defaults to 'HEAD',
            that is the current commit

        Returns
        -------
        list[str]
            List of full path names of all files in the repository.
        """
        args = [
            'git', '-C', str(self.repo), 'ls-tree',
            '-r', '--name-only', '--full-tree', '-z',
            commit
        ]
        # TODO: consider replacing with subprocess.run()
        process = subprocess.Popen(args, stdout=subprocess.PIPE)
        result = process.stdout.read() \
                     .decode(GitRepo.path_encoding) \
                     .split('\0')[:-1]
        process.stdout.close()  # to avoid ResourceWarning: unclosed file <_io.BufferedReader name=3>
        process.wait()  # to avoid ResourceWarning: subprocess NNN is still running
        # TODO: add error checking
        return result

    def list_changed_files(self, commit: str = 'HEAD',
                           side: DiffSide = DiffSide.POST) -> list[str]:
        """Retrieve list of files changed at given revision in repo

        NOTE: not tested for merge commits, especially "evil merges"
        with respect to file names.

        Parameters
        ----------
        commit : str
            The commit for which to list changes.  Defaults to 'HEAD',
            that is the current commit.  The changes are relative to
            commit^, that is the previous commit (first parent of the
            given commit).
        side : DiffSide
            Whether to use names of files in post-image (after changes)
            with side=DiffSide.POST, or pre-image names (before changes)
            with side=DiffSide.PRE.  Renames are detected by Git.

        Returns
        -------
        list[str]
            full path names of files changed in `commit`.
        """
        if side == DiffSide.PRE:
            changes_status = self.diff_file_status(commit)
            return [
                pre for (pre, _) in changes_status.keys()
                if pre is not None  # TODO: check how deleted files work with side=DiffSide.POST
            ]

        if side != DiffSide.POST:
            raise NotImplementedError(f"GitRepo.list_changed_files: unsupported side={side} parameter")

        # --no-commit-id is needed for 1-argument git-diff-tree
        cmd = [
            'git', '-C', self.repo, 'diff-tree', '-M',
            '-r', '--name-only', '--no-commit-id', '-z',
            commit
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        result = process.stdout.read() \
                     .decode(GitRepo.path_encoding) \
                     .split('\0')[:-1]
        process.stdout.close()  # to avoid ResourceWarning: unclosed file <_io.BufferedReader name=3>
        process.wait()  # to avoid ResourceWarning: subprocess NNN is still running

        return result

    def diff_file_status(self, commit: str = 'HEAD',
                         prev: Optional[str] = None,
                         silence_errors: bool = True) -> dict[tuple[str, str], str]:
        """Retrieve the status of file changes at the given revision in the repo

        It returns in a structured way information equivalent to the one
        from calling 'git diff --name-status -r'.

        Example output:
            {
                (None, 'added_file'): 'A',
                ('file_to_be_deleted', None): 'D',
                ('mode_changed', 'mode_changed'): 'M',
                ('modified', 'modified'): 'M',
                ('to_be_renamed', 'renamed'): 'R'
            }

        Parameters
        ----------
        commit
            The commit for which to list changes for. Defaults to
            'HEAD', that is the current commit.
        prev
            The commit for which to list changes from. If not set, then
            changes are relative to the parent of the `commit`
            parameter, which means 'commit^'.
        silence_errors
            Redirect stderr to /dev/null (e.g., about 'commit^' not existing)

        Returns
        -------
        dict[tuple[str,str],str]
            Information about the status of each change. Returns a
            mapping (a dictionary), where the key is the pair (tuple) of
            pre-image and post-image pathname, and the value is a single
            letter denoting the status / type of the change.

            For new (added) files the pre-image path is `None`, and for deleted
            files the post-image path is `None`.

            Possible status letters are:
             - 'A': addition of a file,
             - 'C': copy of a file into a new one (not for all implementations),
             - 'D': deletion of a file,
             - 'M': modification of the contents or mode of a file,
             - 'R': renaming of a file,
             - 'T': change in the type of the file (untested).

        """
        if prev is None:
            # NOTE: this means first-parent changes for merge commits
            prev = commit + '^'
            # TODO: check if prev exists, and if not, use `prev = '--root'` (as an option)

        cmd = [
            'git', '-C', self.repo, 'diff-tree', '--no-commit-id',
            # turn on renames [with '-M' or '-C'];
            # note that parsing is a bit easier without '-z', assuming that filenames are sane
            # increase the inexact rename detection limit
            '--find-renames', '-l5000', '--name-status', '-r',
            prev, commit
        ]
        if silence_errors:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        else:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        lines = process.stdout.read().decode(GitRepo.path_encoding).splitlines()
        result = {}
        for line in lines:
            if line[0] == 'R' or line[0] == 'C':
                status, old, new = line.split("\t")
                old = decode_c_quoted_str(old)
                new = decode_c_quoted_str(new)
                result[(old, new)] = status[0]  # no similarity info
            else:
                status, path = line.split("\t")
                path = decode_c_quoted_str(path)
                if status == 'A':
                    result[(None, path)] = status
                elif status == 'D':
                    result[(path, None)] = status
                else:
                    result[(path, path)] = status

        process.stdout.close()  # to avoid ResourceWarning: unclosed file <_io.BufferedReader name=3>
        process.wait()  # to avoid ResourceWarning: subprocess NNN is still running

        return result

    def changed_lines_extents(self, commit: str = 'HEAD',
                              prev: Optional[str] = None,
                              side: DiffSide = DiffSide.POST) -> tuple[dict[str, list[tuple[int, int]]],
                                                                       dict[str, list[PatchLine]],
                                                                       PatchSet]:
        """List target line numbers of changed files as extents, for each changed file

        For each changed file that appears in `side` side of the diff between
        given commits, it returns list of `side` line numbers (e.g. target line
        numbers for post=DiffSide.POST).

        Line numbers are returned compressed as extents, that is list of
        tuples of start and end range.  For example, if target line numbers
        would be [1, 2, 3, 7, 10, 11], then their extent list would be
        [(1, 3), (7, 7), (10, 11)].

        To make it easier to mesh with other parts of computation, and to
        avoid reparsing diffs, also return parsed patch lines (diff lines).

        Uses :func:`GitRepo.unidiff` to parse git diff between `prev` and `commit`.

        Used by :func:`GitRepo.changes_survival`.

        Parameters
        ----------
        commit : str
            later (second) of two commits to compare, defaults to
            'HEAD', that is the current commit
        prev : str, optional
            earlier (first) of two commits to compare,
            defaults to None, which means comparing to parent of `commit`
        side : DiffSide
            Whether to use names of files in post-image (after changes)
            with side=DiffSide.POST, or pre-image names (before changes)
            with side=DiffSide.PRE.  Renames are detected by Git.
            Defaults to DiffSide.POST, which is currently the only value
            supported.

        Returns
        -------
        (dict[str, list[tuple[int, int]]], dict[str, list[PatchLine]], PatchSet)
            two dicts, with changed files names as keys, first with
            information about change lines extents, second with parsed
            change lines (only for added lines), and unidiff.PatchSet
            to avoid recomputing diffs
        """
        # TODO: implement also for DiffSide.PRE
        if side != DiffSide.POST:
            raise NotImplementedError(f"GitRepo.changed_lines_extents: unsupported side={side} parameter")

        patch = self.unidiff(commit=commit, prev=prev)
        file_ranges = {}
        file_diff_lines_added = defaultdict(list)
        for patched_file in patch:
            if patched_file.is_removed_file:  # no post-image for removed files
                continue
            line_ranges = []
            for hunk in patched_file:
                (range_beg, range_end) = (None, None)
                for line in hunk:
                    # we are interested only in ranges of added lines (in post-image)
                    if line.is_added:
                        if range_beg is None:  # first added line in line range
                            range_beg = line.target_line_no
                        range_end = line.target_line_no

                        file_diff_lines_added[decode_c_quoted_str(patched_file.path)].append(
                            line
                        )

                    else:  # deleted line, context line, or "No newline at end of file" line
                        if range_beg is not None:
                            line_ranges.append((range_beg, range_end))
                            range_beg = None

                # if diff ends with added line
                if range_beg is not None:
                    line_ranges.append((range_beg, range_end))

            file_ranges[decode_c_quoted_str(patched_file.path)] = line_ranges

        return file_ranges, file_diff_lines_added, patch

    @overload
    def unidiff(self, commit: str = ..., prev: Optional[str] = ..., wrap: Literal[True] = ...) -> ChangeSet:
        ...

    @overload
    def unidiff(self, commit: str = ..., prev: Optional[str] = ..., *, wrap: Literal[False]) -> Union[str, bytes]:
        ...

    @overload
    def unidiff(self, commit: str = ..., prev: Optional[str] = ..., wrap: bool = ...) -> Union[str, bytes, ChangeSet]:
        ...

    def unidiff(self, commit='HEAD', prev=None, wrap=True):
        """Return unified diff between `commit` and `prev`

        If `prev` is None (which is the default), return diff between the
        `commit` and its first parent, or between the `commit` and the empty
        tree if `commit` does not have any parents (if it is a root commit).

        If `wrap` is True (which is the default), wrap the result in
        unidiff.PatchSet to make it easier to extract information from
        the diff.  Otherwise, return diff as plain text.

        Parameters
        ----------
        commit : str
            later (second) of two commits to compare, defaults to
            'HEAD', that is the current commit
        prev : str or None
            earlier (first) of two commits to compare, defaults to None,
            which means comparing to parent of `commit`
        wrap : bool
            whether to wrap the result in PatchSet

        Returns
        -------
        str | bytes | ChangeSet
            the changes between two arbitrary commits, `prev` and
            `commit`
        """
        if prev is None:
            try:
                # NOTE: this means first-parent changes for merge commits
                return self.unidiff(commit=commit, prev=commit + '^', wrap=wrap)
            except subprocess.CalledProcessError:
                # commit^ does not exist for a root commits (for first commits)
                return self.unidiff(commit=commit, prev=self.empty_tree_sha1, wrap=wrap)

        cmd = [
            'git', '-C', self.repo,
            'diff', '--find-renames', '--find-copies', '--find-copies-harder',
            prev, commit
        ]
        process = subprocess.run(cmd,
                                 capture_output=True, check=True)
        try:
            diff_output = process.stdout.decode(self.default_file_encoding)
        except UnicodeDecodeError:
            # unidiff.PatchSet can only handle strings
            diff_output = process.stdout.decode(self.fallback_encoding)

        if wrap:
            return ChangeSet(diff_output, self.to_oid(commit),
                             prev=prev)
        else:
            return diff_output

    @overload
    def log_p(self, revision_range: Union[str, Iterable[str]] = ..., wrap: Literal[True] = ...) \
            -> Iterator[ChangeSet]:
        ...

    @overload
    def log_p(self, revision_range: Union[str, Iterable[str]] = ..., wrap: Literal[False] = ...) \
            -> Iterator[str]:
        ...

    @overload
    def log_p(self, revision_range: Union[str, Iterable[str]] = ..., wrap: bool = ...) \
            -> Union[Iterator[str], Iterator[ChangeSet]]:
        ...

    def log_p(self, revision_range=('-1', 'HEAD'), wrap=True):
        """Generate commits with unified diffs for a given `revision_range`

        If `revision_range` is not provided, it generates single most recent
        commit on the current branch.

        The `wrap` parameter controls the output format.  If true (the
        default), generate series of `unidiff.PatchSet` for commits changes.
        If false, generate series of raw commit + unified diff of commit
        changes (as `str`).  This is similar to how `unidiff()` method works.

        Parameters
        ----------
        revision_range
            arguments to pass to `git log --patch`, see https://git-
            scm.com/docs/git-log; by default generates single patch from
            the HEAD
        wrap
            whether to wrap the result in PatchSet / ChangeSet

        Yields
        ------
        ChangeSet | str
            the changes for given `revision_range`
        """
        def commit_with_patch(_commit_id: str, _commit_data: StringIO) -> ChangeSet:
            """Helper to create ChangeSet with from _commit_data stream"""
            _commit_data.seek(0)  # rewind to beginning for reading by the PatchSet constructor
            return ChangeSet(_commit_data, _commit_id)

        cmd = [
            'git', '-C', str(self.repo),
            # NOTE: `git rev-list` does not support --patch option
            'log', '--format=raw', '--diff-merges=first-parent', '--patch', '-z',  # log options
            '--find-renames', '--find-copies', '--find-copies-harder',  # diff options
        ]
        if isinstance(revision_range, str):
            cmd.append(revision_range)
        else:
            cmd.extend(revision_range)

        ## DEBUG (TODO: switch to logger.debug())
        #print(f"{cmd=}")

        # NOTE: specifying `encoding` or `errors` turns on `text` == `universal_newlines`
        # and you cannot say `text=False` and/or `universal_newlines=False` to turn it off
        # The output of the `git log -p` command can contain embedded `\r` (CR)
        process = subprocess.Popen(
            cmd,
            #bufsize=1,  # line buffered
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # TODO: consider capturing stderr
        )

        commit_data = StringIO()
        commit_id: Optional[str] = None
        # if we are waiting on the process, readline can return empty line
        # if the process ends, we can still have lines in buffer
        while (log_p_line_raw := process.stdout.readline()) or process.poll() is None:
            log_p_line = log_p_line_raw.decode(
                encoding='utf-8',
                errors=self.encoding_errors,
            )
            if log_p_line:
                if not commit_id and log_p_line[0] != '\0':
                    # first line in output
                    commit_id = log_p_line.strip()[7:]  # strip "commit "

                if log_p_line[0] == '\0':
                    # end of old commit, start of new commit
                    ## DEBUG (TODO: switch to logger.debug())
                    #print(f"new commit: {log_p_line[1:]}", end="")
                    # return old commit data
                    if wrap:
                        yield commit_with_patch(commit_id, commit_data)
                    else:
                        yield commit_data.getvalue()
                    # start gathering data for a new commit
                    commit_data.truncate(0)
                    # strip the '\0' separator
                    log_p_line = log_p_line[1:]
                    commit_id = log_p_line.strip()[7:]  # strip "commit "

                # gather next line of commit data
                commit_data.write(log_p_line)

        if commit_data.tell() > 0:
            # there is gathered data from the last commit
            ## DEBUG (TODO: switch to logger.debug())
            #print("last commit")
            if wrap:
                yield commit_with_patch(commit_id, commit_data)
            else:
                yield commit_data.getvalue()

        return_code = process.wait()
        if return_code != 0:
            print(f"Error running 'git log' for {self.repo.name} repo, error code = {return_code}")
            print(f"- repository path: '{self.repo}'")
            print(f"- command: {' '.join(cmd)}")

    def _file_contents_process(self, commit: str, path: str) -> subprocess.Popen[bytes]:
        cmd = [
            'git', '-C', self.repo, 'show',  # or 'git', '-C', self.repo, 'cat-file', 'blob',
            # assumed that 'commit' is sane
            f'{commit}:{path}'
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

        return process

    def file_contents(self, commit: str, path: str, encoding: Optional[str] = None) -> str:
        """Retrieve contents of given file at given revision / tree

        Parameters
        ----------
        commit : str
            The commit for which to return file contents.
        path : str
            Path to a file, relative to the top-level of the repository
        encoding : str or None
            Encoding of the file (optional)

        Returns
        -------
        str
            Contents of the file with given path at given revision
        """
        if encoding is None:
            encoding = GitRepo.default_file_encoding

        process = self._file_contents_process(commit, path)
        result = process.stdout.read().decode(encoding=encoding, errors=self.encoding_errors)
        # NOTE: does not handle errors correctly yet
        process.stdout.close()  # to avoid ResourceWarning: unclosed file <_io.BufferedReader name=3>
        process.wait()  # to avoid ResourceWarning: subprocess NNN is still running

        return result

    @contextmanager
    def open_file(self, commit: str, path: str) -> BufferedReader:
        """Open given file at given revision / tree as binary file

        Works as a context manager, like `pathlib.Path.open()`:

            >>> with GitRepo('/path/to/repo').open_file('v1', 'example_file') as fpb:
            ...     contents = fpb.read().decode('utf8')
            ...

        Parameters
        ----------
        commit : str
            The commit for which to return file contents.
        path : str
            Path to a file, relative to the top-level of the repository

        Returns
        -------
        io.BufferedReader
            file object, opened in binary mode
        """
        process = self._file_contents_process(commit, path)
        try:
            yield process.stdout
        finally:
            # NOTE: does not handle errors correctly yet
            process.stdout.close()  # to avoid ResourceWarning: unclosed file <_io.BufferedReader name=3>
            process.wait()  # to avoid ResourceWarning: subprocess NNN is still running

    def list_tags(self) -> list[str]:
        """Retrieve list of all tags in the repository

        Returns
        -------
        list[str]
            List of all tags in the repository.
        """
        cmd = ['git', '-C', self.repo, 'tag', '--list']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        # NOTE: f.readlines() might be not the best solution
        tags = [line.decode(GitRepo.path_encoding).rstrip()
                for line in process.stdout.readlines()]

        process.stdout.close()  # to avoid ResourceWarning: unclosed file <_io.BufferedReader name=3>
        process.wait()  # to avoid ResourceWarning: subprocess NNN is still running

        return tags

    def create_tag(self, tag_name: str, commit: str = 'HEAD') -> None:
        """Create lightweight tag (refs/tags/* ref) to the given commit

        NOTE: does not support annotated tags for now; among others it
        would require deciding on tagger identity (at least for some
        backends).

        Parameters
        ----------
        tag_name : str
            Name of tag to be created. Should follow `git check-ref-
            format` rules for name; see https://git-scm.com/docs/git-
            check-ref-format ; for example they cannot contain space '
            ', tilde '~', caret '^', or colon ':'.  Those rules are NOT
            checked.
        commit : str
            Revision to be tagged.  Defaults to 'HEAD'.

        Returns
        -------
        None
        """
        cmd = [
            'git', '-C', self.repo, 'tag', tag_name, commit,
        ]
        # we are interested in effects of the command, not its output
        subprocess.run(cmd, stdout=subprocess.DEVNULL, check=True)

    def get_commit_metadata(self, commit: str = 'HEAD') -> dict[str, Union[str, dict, list]]:
        """Retrieve metadata about given commit

        Parameters
        ----------
        commit : str
            The commit to examine. Defaults to 'HEAD', that is the
            current (most recent) commit.

        Returns
        -------
        dict
            Information about selected parts of commit metadata, the
            following format:

            {
                'id': 'f8ffd4067d1f1b902ae06c52db4867f57a424f38',
                'parents': ['fe4a622e5202cd990c8ec853d56e25922f263243'],
                'tree': '5347fe7b8606e7a164ab5cd355ee5d86c99796c0'
                'author': {
                    'author': 'A U Thor <author@example.com>',
                    'name': 'A U Thor',
                    'email': 'author@example.com',
                    'timestamp': 1112912053,
                    'tz_info': '-0600',
                },
                'committer': {
                    'committer': 'C O Mitter <committer@example.com>'
                    'name': 'C O Mitter',
                    'email': 'committer@example.com',
                    'timestamp': 1693598847,
                    'tz_info': '+0200',
                },
                'message': 'Commit summary\n\nOptional longer description\n',
            }

            TODO: use dataclass for result (for computed fields)

        """
        # NOTE: using low level git 'plumbing' command means 'utf8' encoding is not assured
        # same as in `parse_commit` in gitweb/gitweb.perl in https://github.com/git/git
        # https://github.com/git/git/blob/3525f1dbc18ae36ca9c671e807d6aac2ac432600/gitweb/gitweb.perl#L3591C5-L3591C17
        cmd = [
            'git', '-C', self.repo, 'rev-list',
            '--parents', '--header', '--max-count=1', commit,
            '--'
        ]
        process = subprocess.run(cmd, capture_output=True, check=True)
        return _parse_commit_text(
            process.stdout.decode(GitRepo.log_encoding, errors=self.encoding_errors),
            # next parameters depend on the git command used
            with_parents_line=True, indented_body=True
        )

    def find_commit_by_timestamp(self, timestamp: Union[str, int], start_commit: str = 'HEAD') -> str:
        """Find first commit in repository older than given date

        Parameters
        ----------
        timestamp: int or str
            Date in UNIX epoch format, also known as timestamp format.
            Returned commit would be older than this date.
        start_commit : str
            The commit from which to start walking through commits,
            trying to find the one we want.  Defaults to 'HEAD'

        Returns
        -------
        str
            Full SHA-1 identifier of found commit.

            WARNING: there is currently no support for error handling,
            among others for not finding any commit that fulfills
            the condition.  At least it is not tested.
        """
        cmd = [
            'git', '-C', self.repo, 'rev-list',
            f'--min-age={timestamp}', '-1',
            start_commit
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        # this should be US-ASCII hexadecimal identifier
        result = process.stdout.read().decode('latin1').strip()
        # NOTE: does not handle errors correctly yet

        process.stdout.close()  # to avoid ResourceWarning: unclosed file <_io.BufferedReader name=3>
        process.wait()  # to avoid ResourceWarning: subprocess NNN is still running

        return result

    def to_oid(self, obj: str) -> Union[str, None]:
        """Convert object reference to object identifier

        Returns None if object `obj` is not present in the repository

        Parameters
        ----------
        obj : str
            object reference, for example "HEAD" or "main^", see e.g.
            https://git-scm.com/docs/gitrevisions

        Returns
        -------
        str or None
            SHA-1 identifier of object, or None if object is not found
        """
        cmd = [
            'git', '-C', self.repo,
            'rev-parse', '--verify', '--end-of-options', obj
        ]
        try:
            # emits SHA-1 identifier if object is found in the repo; otherwise, errors out
            process = subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError:
            return None

        # SHA-1 is ASCII only
        return process.stdout.decode('latin1').strip()

    def is_valid_commit(self, commit: str) -> bool:
        """Check if `commit` is present in the repository as a commit

        Parameters
        ----------
        commit : str
            reference to a commit, for example "HEAD" or "main", or
            "fc6db4e600d633d6fc206217e70641bbb78cbc53^"

        Returns
        -------
        bool
            whether `commit` is a valid commit in repo
        """
        return self.to_oid(str(commit) + '^{commit}') is not None

    def are_valid_objects(self, objects: Iterable[str],
                          object_type: Optional[str] = "commit",
                          single_use: bool = False) -> list[None|bool]:
        """Check which of given `objects` are present in the repository

        You can ensure that `objects` not only exist but are of a specific
        type ("commit" by default); setting `object_type` to None turns off
        this check.

        Parameters
        ----------
        objects
            List of object identifiers to check.  Often used with a list
            of commit identifiers (SHA-1, branches, or tags).

        object_type
            One of "commit", "tree", "blob", "tag", or None.
            If not None, the type is used to restrict the type of object:
            only objects of given `object_type` are considered valid,
            which means that the object must exist and be of a specified type.

        single_use
            If True, do not keep the connection to `git cat-file --batch-command`
            open, but close it automatically.

        Returns
        -------
        list[None|bool]
            For each element of `objects`, returns True if this object exists
            (and, if `object_type` is not None, is of the specified type),
            False if this object does not exist, and None if given object identifier
            is ambiguous.
        """
        proc = self.batch_command

        # write commands, batched
        for obj in objects:
            if object_type is not None:
                proc.stdin.write(f'info {obj}^{{{object_type}}}\n')
            else:
                proc.stdin.write(f'info {obj}\n')

        proc.stdin.write('flush\n')
        proc.stdin.flush()

        # read results
        results = []
        for _ in objects:
            line = proc.stdout.readline()
            info = line.rstrip('\n').split(sep=' ', maxsplit=1)[1]

            if info == 'missing':
                results.append(False)
            elif info == 'ambiguous':
                results.append(None)
            else:
                results.append(True)

        if single_use:
            self.close_batch_command()

        return results

    def filter_valid_commits(self, commits: Iterable[str],
                             to_oid: bool = False,
                             single_use: bool = False) -> Iterable[str]:
        """Filter out invalid commits from the given list of commits

        Commit is considered invalid if it does not exist in the repository,
        or is not a commit.

        Parameters
        ----------
        commits
             A list of commit identifiers to check
        to_oid
            Whether to convert elements in `commits` to SHA-1 object identifiers,
            for example, "HEAD" to "3a27ee24b37a3e9572a0acc0aaecd22cc9c10bc7"
        single_use
            If True, do not keep the connection to `git cat-file --batch-command`
            open, but close it automatically.

        Yields
        ------
        str
            Commit from `commits` that is valid (i.e., exists in the repository,
            and is a commit)

        Returns
        -------
        Iterable[str]
            Subset of identifiers from `commits` that are valid commits
        """
        proc = self.batch_command

        # write commands, batched
        for commit_id in commits:
            proc.stdin.write(f'info {commit_id}^{{commit}}\n')

        proc.stdin.write('flush\n')
        proc.stdin.flush()

        # read results, batched
        for commit_id in commits:
            line = proc.stdout.readline()
            info = line.rstrip('\n').split(sep=' ')
            if len(info) == 3 and info[1] == 'commit':
                yield info[0] if to_oid else commit_id

        if single_use:
            self.close_batch_command()

    def get_current_branch(self) -> Union[str, None]:
        """Return short name of the current branch

        It returns name of the branch, e.g. "main", rather than fully
        qualified name (full name), e.g. "refs/heads/main".

        Will return None if there is no current branch, that is if
        repo is in the 'detached HEAD' state.

        Returns
        -------
        str or None
            name of the current branch
        """
        cmd = [
            'git', '-C', self.repo,
            'symbolic-ref', '--quiet', '--short', 'HEAD'
        ]
        try:
            # Using '--quiet' means that the command would not issue an error message
            # but exit with non-zero status silently if HEAD is not a symbolic ref, but detached HEAD
            process = subprocess.run(cmd,
                                     capture_output=True, check=True,
                                     # branch names cannot contain '\r' (CR) character,
                                     # see https://git-scm.com/docs/git-check-ref-format
                                     text=True, errors=self.encoding_errors)
        except subprocess.CalledProcessError:
            return None

        return process.stdout.strip()

    def resolve_symbolic_ref(self, ref: str = 'HEAD') -> Union[str, None]:
        """Return full name of reference `ref` symbolic ref points to

        If `ref` is not symbolic reference (e.g. ref='HEAD' and detached
        HEAD state) it returns None.

        Parameters
        ----------
        ref : str
            name of the symbolic reference, e.g. "HEAD"

        Returns
        -------
        str or None
            resolved `ref`
        """
        cmd = [
            'git', '-C', self.repo,
            'symbolic-ref', '--quiet', str(ref)
        ]
        try:
            # Using '--quiet' means that the command would not issue an error message
            # but exit with non-zero status silently if `ref` is not a symbolic ref
            process = subprocess.run(cmd,
                                     capture_output=True, check=True,
                                     # branch names and symbolic refereces cannot contain '\r' (CR),
                                     # see https://git-scm.com/docs/git-check-ref-format
                                     text=True, errors=self.encoding_errors)
        except subprocess.CalledProcessError:
            return None

        return process.stdout.strip()

    def _to_refs_list(self, ref_pattern: Union[str, list[str]] = 'HEAD') -> list[str]:
        # support single patter or list of patterns
        # TODO: use variable number of parameters instead (?)
        if not isinstance(ref_pattern, list):
            ref_pattern = [ref_pattern]

        return filter(
            # filter out cases of detached HEAD, resolved to None (no branch)
            lambda x: x is not None,
            map(
                # resolve symbolic references, currently only 'HEAD' is resolved
                lambda x: x if x != 'HEAD' else self.resolve_symbolic_ref(x),
                ref_pattern
            )
        )

    # TODO?: change name to `list_merged_into`
    def check_merged_into(self, commit: str, ref_pattern: Union[str, list[str]] = 'HEAD') -> list[str]:
        """List those refs among `ref_pattern` that contain given `commit`

        This method can be used to check if a given `commit` is merged into
        at least one ref matching `ref_pattern` using 'git for-each-ref --contains',
        see https://git-scm.com/docs/git-for-each-ref

        Return list of refs that contain given commit, or in other words
        list of refs that given commit is merged into.

        Note that symbolic refs, such as 'HEAD', are expanded.

        Parameters
        ----------
        commit : str
            The commit to check if it is merged
        ref_pattern : str or list[str]
            <pattern>…, that is a pattern or list of patterns; check
            each ref that match against at least one patterns, either
            using fnmatch(3) or literally, in the latter case matching
            completely, or from the beginning up to a slash.  Defaults
            to 'HEAD'.

        Returns
        -------
        list[str]
            list of refs matching `ref_pattern` that `commit` is merged
            into (that contain given `commit`)
        """
        ref_pattern = self._to_refs_list(ref_pattern)

        cmd = [
            'git', '-C', self.repo,
            'for-each-ref', f'--contains={commit}',  # only list refs which contain the specified commit
            '--format=%(refname)',  # we only need list of refs that fulfill the condition mentioned above
            *ref_pattern
        ]
        process = subprocess.run(cmd,
                                 capture_output=True, check=True,
                                 # branch and other refs names cannot contain '\r' (CR),
                                 # see https://git-scm.com/docs/git-check-ref-format
                                 text=True, errors=self.encoding_errors)
        return process.stdout.splitlines()

    def reverse_blame(self, commit: str, file: str|PathLike,
                      ref_pattern: str = 'HEAD',
                      line_extents: Optional[list[tuple[int, int]]] = None) -> tuple[dict, list]:
        """Find what revision each line of file at commit was modified since

        For each line of `file` (or subset of lines selected by `line_extents`),
        find how long it did survive starting from `commit`, that is find the last
        revision at which the line is yet present in the history.

        The origin of lines is automatically followed across whole-file renames;
        currently there is no option to tell this function to follow lines as they
        are copied and pasted into another file (TODO).

        In reverse blame, history is walked forward (from 'HEAD') instead of backward.
        Instead of showing the revision in which a line appeared, this shows the last
        revision in which a line has existed.

        Parameters
        ----------
        commit:
            where to start examine history from
        file:
            file to perform blame on (as a whole, or only selected lines)
        ref_pattern:
            <pattern>…, that is a pattern or list of patterns;
            check each ref that match against at least one patterns, either using
            fnmatch(3) or literally, in the latter case matching completely,
            or from the beginning up to a slash.  Defaults to 'HEAD'.
            *NOTE*: currently unused, 'HEAD' is always used.
        line_extents:
            which lines to blame, provided as list of line
            ranges (as extents: [(<beg>,<end>),...])
            for example generated by `GitRepo.changed_lines_extents` method,
            optional

        Returns
        -------
        (dict, list)
            information about commits (dict) and information about lines (list)
        """
        ref_pattern = self._to_refs_list(ref_pattern)

        line_args = []
        if line_extents is not None:
            for beg, end in line_extents:
                line_args.extend(['-L', f'{beg},{end}'])

        cmd = [
            'git', '-C', self.repo,
            'blame', '--reverse', commit, '--porcelain',
            *line_args,
            str(file)
        ]
        process = subprocess.run(cmd, capture_output=True, check=True)

        # TODO: extract this into a helper function
        try:
            output = process.stdout.decode(self.default_file_encoding)
        except UnicodeDecodeError:
            # not a valid utf-8, simply use bytes
            #output = process.stdout
            # _parse_blame_porcelain _currently_ can only handle strings
            output = process.stdout.decode(self.fallback_encoding)

        return _parse_blame_porcelain(
            output
        )

    def changes_survival(self, commit: str, prev: Optional[str] = None,
                         addition_optimization: bool = False) -> tuple[dict, dict]:
        """Find what revision each line of `commit` changes was modified since

        This performs reverse blame for each file modified in diff between
        `commit` and `prev`, which is still present in the post-image of diff
        (which means that file deletions are excluded), limited to lines changed
        in that file.

        Returns 2-element tuple, with per-path information about blamed commits
        as the first element, and per-path list of blame information for each
        changed line.

        Example of results:

            ({
                'file': {
                    'd860e7a706ac8aa45089111495ad7fe0004cbbfa': {
                        'author': 'A U Thor',
                        'author-email': '<author@example.com>',
                        'author-time': '1693601010',
                        'author-tz': '-0600',
                        # ...
                        'filename': 'file',
                        'summary': 'Changed file'
                    }
                }
            },[
                {
                    'commit': 'd860e7a706ac8aa45089111495ad7fe0004cbbfa',
                    'line': 'contents of 1st line',
                    'final': 1,
                    'original': 1,
                    'original_filename': 'file',
                    # ...
                }
            ])

        Parameters
        ----------
        commit:
            later (second) of two commits to compare,
            defaults to 'HEAD', that is the current commit
        prev:
            earlier (first) of two commits to compare,
            defaults to None, which means comparing to parent of `commit`
        addition_optimization:
            whether to blame whole file
            for files that were added between `prev` and `commit`

        Returns
        -------
        (dict[str, dict], dict[str, list])
            information about commits blamed, and blame information
            for each changed file
        """
        lines_survival = {}
        all_commits_data = {}
        diff_stat = {}

        # if we are doing the optimization, we need additiona information
        if addition_optimization:
            diff_stat = self.diff_file_status(commit, prev)

        changes_info, file_diff_lines, patch = self.changed_lines_extents(commit, prev, side=DiffSide.POST)

        # map from file name in changed files to unidiff.PatchedFile for that file
        patched_files_map = {}
        patched_file: unidiff.PatchedFile
        for patched_file in patch:
            # same key as used in .changed_lines_extents()
            patched_files_map[decode_c_quoted_str(patched_file.path)] = patched_file

        for file_path, line_extents in changes_info.items():
            if not line_extents:
                # empty changes, for example pure rename
                continue

            # TODO: make it configurable
            # drop submodules from survival analysis
            if (file_path in patched_files_map and  # just in case
                get_patched_file_mode(patched_files_map[file_path], file_path) == GitFileMode.SUBMODULE):
                continue

            # if file was added in commit, blame whole file
            if addition_optimization:
                if (None, file_path) in diff_stat:  # pure addition
                    line_extents = None  # blame whole file

            file_path = decode_c_quoted_str(file_path)
            commits_data, lines_data = self.reverse_blame(commit, file_path,
                                                          line_extents=line_extents)

            # helper structure to find corresponding unidiff.patch.Line aka PatchLine
            lines_data_diff_lines = {}
            if file_path in file_diff_lines:
                lines_data_diff_lines = {
                    diff_line.target_line_no: diff_line
                    for diff_line in file_diff_lines[file_path]
                }

            for line_info in lines_data:
                if 'previous' in commits_data[line_info['commit']]:
                    line_info['previous'] = commits_data[line_info['commit']]['previous']

                line_no = int(line_info['final'])
                if line_no in lines_data_diff_lines:
                    # TODO: add a test that PatchLine matches line ('final', 'line')
                    line_info['unidiff.patch.Line'] = lines_data_diff_lines[line_no]

            lines_survival[file_path] = lines_data
            # NOTE: 'filename', 'boundary', and details of 'previous'
            # are different for different files, but common data could be extracted
            all_commits_data[file_path] = commits_data

        return all_commits_data, lines_survival

    def count_commits(self,
                      start_from: str = StartLogFrom.CURRENT,
                      until_commit: str = None,
                      first_parent: bool = False) -> int:
        """Count number of commits in the repository

        Starting from `start_from`, count number of commits, stopping
        at `until_commit` if provided.

        If `first_parent` is set to True, makes Git follow only the first
        parent commit upon seeing a merge commit.

        Parameters
        ----------
        start_from : str or StartLogFrom
            where to start from to follow 'parent' links
        until_commit : str or None
            where to stop following 'parent' links; also ensures that we
            follow ancestry path to it, optional
        first_parent : bool
            follow only the first parent commit upon seeing a merge
            commit

        Returns
        -------
        int
            number of commits
        """
        if hasattr(start_from, 'value'):
            start_from = start_from.value
        cmd = [
            'git', '-C', self.repo,
            'rev-list', '--count', str(start_from),
        ]
        if until_commit is not None:
            cmd.extend(['--not', until_commit, f'--ancestry-path={until_commit}', '--boundary'])
        if first_parent:
            cmd.append('--first-parent')
        process = subprocess.run(cmd,
                                 capture_output=True, check=True,
                                 # `git rev-list --count <start>` returns a number, no '\r' possible
                                 encoding='utf-8', errors=self.encoding_errors)

        return int(process.stdout)

    def list_authors_shortlog(self, start_from: str = StartLogFrom.ALL) -> list[Union[str, bytes]]:
        """List all authors using git-shortlog

        Summarizes the history of the project by providing the list of authors
        together with their commit counts.  Uses `git shortlog --summary`
        internally.

        Parameters
        ----------
        start_from : str or StartLogFrom
            where to start from to follow 'parent' links

        Returns
        -------
        list[str|bytes]
            list of authors together with their commit count, in the
            'SPACE* <count> TAB <author>' format
        """
        if hasattr(start_from, 'value'):
            start_from = start_from.value
        elif start_from is None:
            start_from = '--all'
        cmd = [
            'git', '-C', self.repo,
            'shortlog',
            '--summary',  # Suppress commit description and provide a commit count summary only.
            '-n',  # Sort output according to the number of commits per author
            start_from,
        ]
        process = subprocess.run(cmd, capture_output=True, check=True)
        try:
            # try to return text
            return process.stdout.decode(GitRepo.log_encoding, errors=self.encoding_errors).splitlines()
        except UnicodeDecodeError:
            # if not possible, return bytes
            return process.stdout.splitlines()

    def list_core_authors(self, start_from: str|StartLogFrom = StartLogFrom.ALL,
                          perc: float = 0.8) -> tuple[list[AuthorStat], float]:
        """List core authors using git-shortlog, and their fraction of commits

        Get list of authors contributions via 'git-shortlog' with
        `list_authors_shortlog`, parse it with `parse_shortlog_count`,
        and select core authors from this list with `select_core_authors`.

        Parameters
        ----------
        start_from:
            where to start from to follow 'parent' links
        perc:
            fraction threshold for considering author a core author,
            assumed to be 0.0 <= `perc` <= 1.0 (not checked!)

        Returns
        -------
        (list[AuthorStat], float)
            list of core authors, sorted, and cumulative fraction of contributions
            of returned authors
        """
        return select_core_authors(
            parse_shortlog_count(self.list_authors_shortlog(start_from)),
            perc
        )

    def find_roots(self, start_from: str = StartLogFrom.CURRENT) -> list[str]:
        """Find root commits (commits without parents), starting from `start_from`

        Parameters
        ----------
        start_from : str or StartLogFrom
            where to start from to follow 'parent' links

        Returns
        -------
        list[str]
            list of root commits, as SHA-1
        """
        if hasattr(start_from, 'value'):
            start_from = start_from.value
        elif start_from is None:
            start_from = 'HEAD'

        cmd = [
            'git', '-C', self.repo,
            'rev-list', '--max-parents=0',  # gives all root commits
            str(start_from),
        ]
        process = subprocess.run(cmd,
                                 capture_output=True, check=True,
                                 # the Git command above returns list of commit identifiers
                                 # separated by newlines, therefore no '\r' in output possible
                                 text=True, errors=self.encoding_errors)
        return process.stdout.splitlines()

    def get_config(self, name: str, value_type: Optional[str] = None) -> Union[str, None]:
        """Query specific git config option

        If there is no Git configuration variable named `name`,
        then it returns None.

        Parameters
        ----------
        name : str
            name of the configuration option, for example,
            'remote.origin.url' or 'user.name'
        value_type : Literal['bool', 'int', 'bool-or-int', 'path', 'expiry-date', 'color'] or None
            name of git type to canonicalize outgoing value, see
            https://git-scm.com/docs/git-config#Documentation/git-
            config.txt---typelttypegt optional

        Returns
        -------
        str or None
            value of requested git configuration variable
        """
        cmd = [
            'git', '-C', self.repo,
            'config', str(name)
        ]
        if value_type is not None:
            cmd.append(f"--type={value_type}")

        try:
            process = subprocess.run(cmd,
                                     capture_output=True, check=True)
            return process.stdout.decode(errors=self.encoding_errors).strip()

        except subprocess.CalledProcessError as err:
            # This command will fail with non-zero status upon error. Some exit codes are:
            # - The section or key is invalid (ret=1),
            # - ...
            if err.returncode == 1:
                return None
            else:
                raise err

# end of file utils/git.py

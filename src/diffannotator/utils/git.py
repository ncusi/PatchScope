# -*- coding: utf-8-unix -*-
"""Utilities to get data out of git repositories.

This file defines a base class, `GitRepo`, which uses straight-up
calling git commands, and needs Git to be installed.

Usage:
------
Example usage:
  >>> from diffannotator.utils.git import GitRepo
  >>> patch = GitRepo('path/to/git/repo').unidiff('HEAD')  # 'HEAD' is the default
  ...     ...

This implementation / backend retrieves data by calling `git` via
`subprocess.Popen` or `subprocess.run`, and parsing the output.

WARNING: at the time this backend does not have error handling implemented;
it would simply return empty result, without any notification about the
error (like incorrect repository path, or incorrect commit)!!!
"""
import os
import re
import subprocess
from io import StringIO
from pathlib import Path
from typing import Optional, Union, TypeVar, Literal, overload
from typing import Iterable, Iterator  # should be imported from collections.abc

from unidiff import PatchSet

# TODO: move to __init__.py (it is common to all scripts)
PathLike = TypeVar("PathLike", str, bytes, Path, os.PathLike)


class GitRepo:
    """Class representing Git repository, for performing operations on"""
    path_encoding = 'utf8'
    default_file_encoding = 'utf8'
    log_encoding = 'utf8'
    fallback_encoding = 'latin1'  # must be 8-bit encoding
    # see 346245a1bb ("hard-code the empty tree object", 2008-02-13)
    # https://github.com/git/git/commit/346245a1bb6272dd370ba2f7b9bf86d3df5fed9a
    # https://github.com/git/git/commit/e1ccd7e2b1cae8d7dab4686cddbd923fb6c46953
    empty_tree_sha1 = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'

    def __init__(self, repo_dir: PathLike):
        """Constructor for `GitRepo` class

        :param repo_dir: path to the Git repository
        """
        # TODO: check that `git_directory` is a path to git repository
        # TODO: remember absolute path (it is safer)
        self.repo = Path(repo_dir)

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

        :param repository: The (possibly remote) repository to clone from,
            usually a URL (ssh, git, http, or https) or a local path.
        :param directory: The name of a new directory to clone into, optional.
            The "humanish" part of the source repository is used if `directory`
            is not provided (if it is `None`).
        :param working_dir: The directory where to run the
            `git-clone https://git-scm.com/docs/git-clone` operation;
            otherwise current working directory is used.  The value
            of this parameter does not matter if `directory` is provided,
        :param reference_local_repository: Use `reference_local_repository`
            to avoid network transfer, and to reduce local storage costs
        :param dissociate: whether to dissociate with `reference_local_repository`,
            used only if `reference_local_repository` is not None
        :param make_path_absolute: Ensure that returned `GitRepo` uses absolute path
        :return: Cloned repository as `GitRepo` if operation was successful,
            otherwise `None`.
        """
        # TODO: make it @classmethod (to be able to use in constructor)
        def _to_repo_path(a_path: str):
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

    def format_patch(self,
                     output_dir: Optional[PathLike] = None,
                     revision_range: Union[str, Iterable[str]] = ('-1', 'HEAD')) -> str:
        """Generate patches out of specified revisions, saving them as individual files

        :param output_dir: output directory for patches; if not set (the default),
            save patches in the current working directory
        :param revision_range: arguments to pass to `git format-patch`, see
            https://git-scm.com/docs/git-format-patch; by default generates single patch
            from the HEAD
        :return: output from the `git format-patch` process
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

        process = subprocess.run(cmd,
                                 capture_output=True, check=True,
                                 encoding='utf-8')
        # MAYBE: better checks for process.returncode, and examine process.stderr
        if process.returncode == 0:
            return process.stdout
        else:
            return process.stderr

    @overload
    def unidiff(self, commit: str = ..., prev: Optional[str] = ..., wrap: Literal[True] = ...) -> PatchSet:
        ...

    @overload
    def unidiff(self, commit: str = ..., prev: Optional[str] = ..., *, wrap: Literal[False]) -> Union[str, bytes]:
        ...

    @overload
    def unidiff(self, commit: str = ..., prev: Optional[str] = ..., wrap: bool = ...) -> Union[str, bytes, PatchSet]:
        ...

    def unidiff(self, commit='HEAD', prev=None, wrap=True):
        """Return unified diff between `commit` and `prev`

        If `prev` is None (which is the default), return diff between the
        `commit` and its first parent, or between the `commit` and the empty
        tree if `commit` does not have any parents (if it is a root commit).

        If `wrap` is True (which is the default), wrap the result in
        unidiff.PatchSet to make it easier to extract information from
        the diff.  Otherwise, return diff as plain text.

        :param str commit: later (second) of two commits to compare,
            defaults to 'HEAD', that is the current commit
        :param prev: earlier (first) of two commits to compare,
            defaults to None, which means comparing to parent of `commit`
        :type prev: str or None
        :param bool wrap: whether to wrap the result in PatchSet
        :return: the changes between two arbitrary commits,
            `prev` and `commit`
        :rtype: str or bytes or PatchSet
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
            return PatchSet(diff_output)
        else:
            return diff_output

    @overload
    def log_p(self, revision_range: Union[str, Iterable[str]] = ..., wrap: Literal[True] = ...) \
            -> Iterator[PatchSet]:
        ...

    @overload
    def log_p(self, revision_range: Union[str, Iterable[str]] = ..., wrap: Literal[False] = ...) \
            -> Iterator[str]:
        ...

    @overload
    def log_p(self, revision_range: Union[str, Iterable[str]] = ..., wrap: bool = ...) \
            -> Union[Iterator[str], Iterator[PatchSet]]:
        ...

    def log_p(self, revision_range=('-1', 'HEAD'), wrap=True):
        """Generate commits with unified diffs for a given `revision_range`

        If `revision_range` is not provided, it generates single most recent
        commit on the current branch.

        The `wrap` parameter controls the output format.  If true (the
        default), generate series of `unidiff.PatchSet` for commits changes.
        If false, generate series of raw commit + unified diff of commit
        changes (as `str`).  This is similar to how `unidiff()` method works.

        :param revision_range: arguments to pass to `git log --patch`, see
            https://git-scm.com/docs/git-log; by default generates single patch
            from the HEAD
        :param wrap: whether to wrap the result in PatchSet
        :return: the changes for given `revision_range`
        """
        def commit_with_patch(_commit_id: str, _commit_data: StringIO) -> PatchSet:
            """Helper to create PatchSet with `_commit_id` as commit_id attribute"""
            _commit_data.seek(0)  # rewind to beginning for reading by the PatchSet constructor
            patch_set = PatchSet(_commit_data)  # parse commit with patch to PatchSet
            patch_set.commit_id = _commit_id  # remember the commit id in an attribute
            return patch_set

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

        process = subprocess.Popen(
            cmd,
            bufsize=1,  # line buffered
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding='utf-8',
            text=True,
        )

        commit_data = StringIO()
        commit_id: Optional[str] = None
        while process.poll() is None:
            log_p_line = process.stdout.readline()
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

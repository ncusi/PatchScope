#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Usage: python -m diffannotator.generate_patches <options> <repo> [<revision-range>]

Generate patches from repo in the form suitable for later analysis by
the `annotate.py` script, and then further for gathering statistics with
the `gather_data.py` script.

Example (after installing the 'diffannotator' package):
    diff-generate python-diff-annotator \
        --output-dataset=diffannotator/user-jnareb --author=jnareb
"""
import os
import re
import subprocess
from io import StringIO
from pathlib import Path
from typing import Optional, Union, TypeVar, overload, Literal
from typing import Iterable, Iterator  # should be imported from collections.abc

import typer
from typing_extensions import Annotated
from unidiff import PatchSet

# TODO: move to __init__.py (it is common to all scripts)
PathLike = TypeVar("PathLike", str, bytes, Path, os.PathLike)


# TODO: extract move to gitrepo.py or utils/git.py
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
        while process.poll() is None:
            log_p_line = process.stdout.readline()
            if log_p_line:
                if log_p_line[0] == '\0':
                    # end of old commit, start of new commit
                    ## DEBUG (TODO: switch to logger.debug())
                    #print(f"new commit: {log_p_line[1:]}", end="")
                    # return old commit data
                    if wrap:
                        yield PatchSet(commit_data)
                    else:
                        yield commit_data.getvalue()
                    # start gathering data for a new commit
                    commit_data.truncate(0)
                    # strip the '\0' separator
                    log_p_line = log_p_line[1:]

                # gather next line of commit data
                commit_data.write(log_p_line)

        if commit_data.tell() > 0:
            # there is gathered data from the last commit
            ## DEBUG (TODO: switch to logger.debug())
            #print("last commit")
            if wrap:
                yield PatchSet(commit_data)
            else:
                yield commit_data.getvalue()

        return_code = process.wait()
        if return_code != 0:
            print(f"Error running 'git log' for {self.repo.name} repo, error code = {return_code}")
            print(f"- repository path: '{self.repo}'")


app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def main(
    ctx: typer.Context,
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
        Optional[Path],
        typer.Option(
            file_okay=False,  # cannot be ordinary file, if exists
            dir_okay=True,    # if exists, must be a directory
            help="Where to save generated patches.",
        )
    ] = None,
) -> None:
    """Create patches from local Git repository with provided REPO_PATH

    You can add additional options and parameters, which will be passed to
    the `git format-patch` command.  With those options and arguments you
    can specify which commits to operate on.

    1. A single commit, <since>, specifies that the commits leading to
       the tip of the current branch that are not in the history
       that leads to the <since> to be output.  Example: 'HEAD~2'.

    2. Generic <revision-range> expression means the commits in the
       specified range.  Example: 'origin/main..main', or '--root HEAD',
       or '--user=joe --root HEAD'.

    If not provided <since> or <revision-range>, a single patch for
    the current commit on the current branch will be created ('HEAD').

    To create patches for everything since the beginning of history
    up until <commit>, use '--root <commit>' as extra options.
    """
    # create GitRepo 'helper' object
    repo = GitRepo(repo_path)
    # ensure that output directory exists
    if output_dir is not None:
        print(f"Ensuring that output directory '{output_dir}' exists")
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating patches from local Git repo '{repo_path}'")
    result = repo.format_patch(output_dir=output_dir,
                               revision_range=ctx.args)
    print(result)


if __name__ == "__main__":
    app()

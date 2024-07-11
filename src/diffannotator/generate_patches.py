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
from pathlib import Path
from typing import Optional, Union, TypeVar
from typing import Iterable  # should be imported from collections.abc

import typer

# TODO: move to __init__.py (it is common to all scripts)
PathLike = TypeVar("PathLike", str, bytes, Path, os.PathLike)


# TODO: extract move to gitrepo.py or utils/git.py
class GitRepo:
    """Class representing Git repository, for performing operations on"""
    path_encoding = 'utf8'
    default_file_encoding = 'utf8'
    log_encoding = 'utf8'

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
                     revision_range: Union[str, Iterable[str]] = ('-1', 'HEAD')) -> None:
        """Generate patches out of specified revisions, saving them as individual files

        :param output_dir: output directory for patches; if not set (the default),
            save patches in the current working directory
        :param revision_range: arguments to pass to `git format-patch`, see
            https://git-scm.com/docs/git-format-patch; by default generates single patch
            from the HEAD
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
        # TODO: check process.returncode and examine process.stderr


app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def main(ctx: typer.Context):
    for extra_arg in ctx.args:
        print(f"Got extra arg: {extra_arg}")


if __name__ == "__main__":
    app()

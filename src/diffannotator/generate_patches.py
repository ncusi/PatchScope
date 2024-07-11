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
from pathlib import Path
from typing import TypeVar

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


app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def main(ctx: typer.Context):
    for extra_arg in ctx.args:
        print(f"Got extra arg: {extra_arg}")


if __name__ == "__main__":
    app()

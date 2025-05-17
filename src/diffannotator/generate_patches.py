#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Usage: python -m diffannotator.generate_patches <options> <repo> [<revision-range>]

Generate patches from repo in the form suitable for later analysis by
the `annotate.py` script, and then further for gathering statistics with
the `gather_data.py` script.

Example (after installing the 'patchscope' package):
    diff-generate PatchScope \
        --output-dataset=patchscope/user-jnareb --author=jnareb
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional, TypeVar

import tqdm
import typer
from typing_extensions import Annotated

from .utils.git import GitRepo


# configure logging
logger = logging.getLogger(__name__)

# TODO: move to __init__.py (it is common to all scripts)
PathLike = TypeVar("PathLike", str, bytes, Path, os.PathLike)

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
    use_fanout: Annotated[
        bool,
        typer.Option(
            help="Use fan-out when saving patches, saved as `*.diff`"
        )
    ] = False,
) -> None:
    """Create patches from local Git repository with provided REPO_PATH

    You can add additional options and parameters, which will be passed to
    the `git format-patch` command.  With those options and arguments, you
    can specify which commits to operate on.

    1. A single commit, `<since>`, specifies that commits leading to
       the tip of the current branch that are not in the history
       that leads to the `<since>` to be output.  Example: '`HEAD~2`'.
       Not supported with '`--use-fanout`'.

    2. Generic `<revision-range>` expression means the commits in the
       specified range.  Example: '`origin/main..main`', or '`--root HEAD`',
       or '`--user=joe --root HEAD`'.

    If not provided `<since>` or `<revision-range>`, a single patch for
    the current commit on the current branch will be created ('`HEAD`').

    To create patches for everything since the beginning of history
    up until `<commit>`, use '`--root <commit>`' as extra options.
    """
    # create GitRepo 'helper' object
    repo = GitRepo(repo_path)
    # ensure that output directory exists
    if output_dir is not None:
        print(f"Ensuring that output directory '{output_dir}' exists")
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating patches from local Git repo '{repo_path}'")
    if use_fanout:
        print("using `git log -p` and saving as *.diff only")

        with tqdm.tqdm(desc="commit") as progress_bar:
            for patch in repo.log_p(revision_range=ctx.args, wrap=True):
                sha = getattr(patch, 'commit_id', '') # added by log_p method
                if not sha:
                    # TODO: use logger.error
                    print("ERROR: failed to get SHA-1 id for a commit, exiting",
                          file=sys.stderr)
                    return

                # sha is defined
                progress_bar.set_postfix(sha1=sha[:7])

                fanout_dir = sha[:2]
                basename = sha[2:]
                output_dir.joinpath(fanout_dir).mkdir(parents=True, exist_ok=True)
                output_dir.joinpath(fanout_dir, f"{basename}.diff")\
                    .write_text(str(patch))

                progress_bar.update()

    else:
        print("using `git format-patch` and saving as *.patch")

        result = repo.format_patch(output_dir=output_dir,
                                   revision_range=ctx.args)
        print(result)


if __name__ == "__main__":
    app()

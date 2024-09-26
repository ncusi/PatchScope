# -*- coding: utf-8 -*-
"""Test cases for `src/diffannotator/generate_patches.py` module"""
import inspect
# import os
import re
import subprocess
import time
from pathlib import Path

import pytest
import unidiff

from diffannotator.annotate import annotate_single_diff
from diffannotator.utils.git import GitRepo, ChangeSet


def test_clone_repository(tmp_path: Path):
    """Test clone_repository() static method of the GitRepo class"""
    test_repo_url = 'https://github.com/githubtraining/hellogitworld.git'
    repo = GitRepo.clone_repository(
        repository=test_repo_url,
        working_dir=tmp_path,
    )

    assert repo is not None, \
        f"successfully cloned repo from GitHub: {test_repo_url}"
    assert isinstance(repo, GitRepo), \
        "the result of cloning is a GitRepo object"
    assert repo.repo.name == 'hellogitworld', \
        "the repo was cloned into 'hellogitworld' subdirectory"
    assert tmp_path.joinpath(repo.repo, '.git', 'HEAD').is_file(), \
        "the repo dir it looks like Git repo (with '.git/HEAD')"

    # clone the same repository, into the same directory
    # but ensure that it uses absolute path
    repo = GitRepo.clone_repository(
        repository=test_repo_url,
        working_dir=tmp_path,
        make_path_absolute=True,
    )
    assert repo.repo.is_absolute(), \
        "repo uses absolute path to the repository"
    assert repo.repo.name == 'hellogitworld', \
        "the repo was re-cloned into 'hellogitworld' subdirectory"


def test_format_patch(tmp_path: Path):
    """Test format_patch() method in GitRepo class, and annotate_single_diff() function"""
    # MAYBE: create fixture
    test_repo_url = 'https://github.com/githubtraining/hellogitworld.git'
    repo = GitRepo.clone_repository(
        repository=test_repo_url,
        working_dir=tmp_path,
        make_path_absolute=True,
    )

    # create directory to save patch(es) to
    patches_dir = tmp_path / 'patch'
    patches_dir.mkdir(exist_ok=True)
    # generate patches (using `git format-patch`)
    repo.format_patch(output_dir=patches_dir)

    patches_paths = list(patches_dir.glob('*'))
    assert len(patches_paths) == 1, \
        "format_patch() created single patch in 'patch' subdirectory"

    # try to parse this patch file
    file_path = patches_paths[0]
    patch = annotate_single_diff(file_path)
    changed_file_name = 'pom.xml'
    assert len(patch) == 1, \
        "there is only one file in patch"
    assert changed_file_name in patch, \
        f"the '{changed_file_name}' file is found in patch data"
    assert len(patch[changed_file_name]['-']) == 1, \
        "there is only one removed line (one changed line)"
    assert len(patch[changed_file_name]['+']) == 1, \
        "there is only one added line (one changed line)"

    # create directory to save patch(es) to
    patches_dir = tmp_path / 'patches'
    patches_dir.mkdir(exist_ok=True)
    # generate patches (using `git format-patch`)
    repo.format_patch(output_dir=patches_dir,
                      revision_range=['--root', 'HEAD'])  # full history

    patches_paths = list(patches_dir.glob('*'))
    assert len(patches_paths) == 24, \
        "format_patch() created patches for all 24 commits in trunk"
    assert all([path.suffix == '.patch' for path in patches_paths]), \
        "all created files have '.patch' suffix"


def test_log_p(tmp_path: Path):
    """Test log_p() method in GitRepo class"""
    # MAYBE: create fixture
    test_repo_url = 'https://github.com/githubtraining/hellogitworld.git'
    repo = GitRepo.clone_repository(
        repository=test_repo_url,
        working_dir=tmp_path,
        make_path_absolute=True,
    )

    result = repo.log_p(revision_range=('-3', 'HEAD'), wrap=True)
    assert inspect.isgeneratorfunction(repo.log_p), \
        "GitRepo.log_p method is generator function"
    assert inspect.isgenerator(result), \
        "GitRepo.log_p() method returns generator"

    result = list(result)
    assert len(result) == 3, \
        "we got 3 patches we expected from `git log -3 HEAD` (with wrap)"
    assert all([isinstance(patch, unidiff.PatchSet) for patch in result]), \
        "all patches are wrapped in unidiff.PatchSet"
    assert all([isinstance(patch, ChangeSet) for patch in result]), \
        "all patches are wrapped in utils.git.ChangeSet"
    sha1_re = re.compile(r"^[0-9a-fA-F]{40}$")  # SHA-1 identifier is 40 hex digits long
    assert all([hasattr(patch, 'commit_id') and
                re.fullmatch(sha1_re, getattr(patch, 'commit_id') or '')
                for patch in result]), \
        "all patch sets have 'commit_id' attribute and it looks like SHA-1"

    result = repo.log_p(revision_range='HEAD~3..HEAD', wrap=False)
    result = list(result)
    assert len(result) == 3, \
        "we got 3 patches we expected from `git log HEAD~3..HEAD` (without wrap)"
    assert all([isinstance(patch, str) for patch in result]), \
        "all patches are returned as plain `str`"


@pytest.mark.slow
@pytest.mark.explore
@pytest.mark.skip(reason="skipping exploratory test")
def test_read_incrementally_from_subprocess():
    """Exploratory test to examine reading process output incrementally, line by line"""
    process = subprocess.Popen(
        # -u :: Force the stdout and stderr streams to be unbuffered.
        ["python", "-u", "tests/helpers/spew.py"],
        bufsize=1,  # line buffered
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        encoding='utf-8',
        text=True,
    )
    # os.set_blocking(process.stdout.fileno(), False)  # on Unix-like systems
    start = time.time()
    elapsed_times = []
    while process.poll() is None:
        data = process.stdout.readline()
        if data:
            elapsed_times.append(time.time() - start)

    return_code = process.wait()

    assert return_code == 0, \
        "process finished without errors"
    assert elapsed_times[-1] - elapsed_times[0] > 1.0, \
        "got first line more than 1.0 seconds earlier than last line"

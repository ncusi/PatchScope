# -*- coding: utf-8 -*-
"""Test cases for `src/diffannotator/generate_patches.py` module"""
from pathlib import Path

from diffannotator.generate_patches import GitRepo


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

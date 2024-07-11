# -*- coding: utf-8 -*-
"""Test cases for `src/diffannotator/generate_patches.py` module"""
from pathlib import Path

from diffannotator.annotate import annotate_single_diff
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


def test_format_patch(tmp_path: Path):
    """Test format_patch() method in GitRepo class"""
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

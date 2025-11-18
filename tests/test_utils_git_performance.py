"""Performance tests for diffannotator.utils.git module (and proposed functions)"""
import subprocess
from typing import Optional, Iterable

import pytest
import unidiff

from diffannotator.utils.git import GitRepo
from tests.conftest import example_repo


def try_unidiff_in_loop(repo: GitRepo) -> list[unidiff.PatchSet]:
    """Filter out invalid commits with single-commit .unidiff() in a try-except block"""
    # NOTE: only "v1" and "v2" exists in the example_repo
    result: list[Optional[unidiff.PatchSet]] = []
    for commit_id in ("v1", "v2", "v3", "v4", "v2^", "v4^"):
        try:
            result.append(repo.unidiff(commit_id))
        except subprocess.CalledProcessError:
            pass  # skip a commit
    return result


def if_valid_unidiff_in_loop(repo: GitRepo) -> list[unidiff.PatchSet]:
    """Filter out invalid commits with .is_valid_commit() (and .unidiff()) in a loop"""
    result: list[Optional[unidiff.PatchSet]] = []
    for commit_id in ("v1", "v2", "v3", "v4", "v2^", "v4^"):
        if repo.is_valid_commit(commit_id):
            result.append(repo.unidiff(commit_id))

    return result


def filter_valid_log_p(repo: GitRepo) -> Iterable[unidiff.PatchSet]:
    """Filter out invalid commits in a batch with .are_valid_objects(), use .log_p()"""
    commit_list = ("v1", "v2", "v3", "v4", "v2^", "v4^")
    validity = repo.are_valid_objects(commit_list, object_type='commit')
    filtered_list = [oid for oid, is_valid in zip(commit_list, validity)
                     if is_valid]
    return repo.log_p(revision_range=('--no-walk=unsorted', *filtered_list), wrap=True)


@pytest.mark.benchmark(group="filtered-log_p")
def test_try_unidiff_loop(benchmark, example_repo):
    actual = benchmark(try_unidiff_in_loop, example_repo)
    assert len(actual) == 3, "there were 3 valid commits"

    expected_0 = example_repo.unidiff('v1')
    assert str(actual[0]) == str(expected_0), "first element is correct"


@pytest.mark.benchmark(group="filtered-log_p")
def test_chk_unidiff_loop(benchmark, example_repo):
    actual = benchmark(if_valid_unidiff_in_loop, example_repo)
    assert len(actual) == 3, "there were 3 valid commits"

    expected_0 = example_repo.unidiff('v1')
    assert str(actual[0]) == str(expected_0), "first element is correct"


@pytest.mark.benchmark(group="filtered-log_p")
def test_batch_chk_log_p(benchmark, example_repo):
    actual = benchmark(filter_valid_log_p, example_repo)
    actual = list(actual)  # read in full (it can be a generator)
    assert len(actual) == 3, "there were 3 valid commits"

    expected_0 = example_repo.unidiff('v1')
    assert str(actual[0]) == str(expected_0), "first element is correct"

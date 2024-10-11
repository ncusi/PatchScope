"""conftest.py: local per-directory plugins / per-directory configuration

It is used in thiis project to provide variables and fixtures common
to all the tests in 'tests/' directory.

https://docs.pytest.org/en/stable/how-to/writing_plugins.html#pluginorder
https://docs.pytest.org/en/stable/how-to/writing_plugins.html#localplugin
https://docs.pytest.org/en/stable/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files
"""
import os
import subprocess
from pathlib import Path

import pytest

from diffannotator.utils.git import GitRepo

# global variable, common for all tests
default_branch = 'main'


@pytest.fixture(scope="module")  # like unittest.setUpClass()
def example_repo(tmp_path_factory: pytest.TempPathFactory) -> GitRepo:
    """Prepare Git repository for testing `utils.git` module

    Uses GitRepo.create_tag() for creating one of lightweight tags,
    so that test_list_tags() test also tests GitRepo.create_tag().
    """
    tmp_path = tmp_path_factory.mktemp('repos')

    repo_name = 'test_utils_git-repo'
    repo_path = str(tmp_path / repo_name)

    # initialize repository and  configure it
    subprocess.run(['git', 'init', repo_path], check=True, stdout=subprocess.DEVNULL)  # noisy
    subprocess.run(['git', '-C', repo_path, 'config', 'user.name', 'A U Thor'], check=True)
    subprocess.run(['git', '-C', repo_path, 'config', 'user.email', 'author@example.com'], check=True)
    subprocess.run(['git', '-C', repo_path, 'branch', '-m', default_branch], check=True)

    # create files, and initial commit
    Path(repo_path).joinpath('example_file').write_text('example\n2\n3\n4\n5\n')
    Path(repo_path).joinpath('subdir').mkdir()
    Path(repo_path).joinpath('subdir', 'subfile').write_text('subfile')
    subprocess.run(['git', '-C', repo_path, 'add', '.'], check=True)
    subprocess.run(['git', '-C', repo_path, 'commit', '-m', 'Initial commit'],
                   check=True, stdout=subprocess.DEVNULL)  # noisy
    subprocess.run(['git', '-C', repo_path, 'tag', 'v1'])

    # intermediate commit, for testing blame
    Path(repo_path).joinpath('subdir', 'subfile').write_text('subfile\n')
    subprocess.run(['git', '-C', repo_path, 'commit', '-a', '-m', 'Change subdir/subfile'],
                   check=True, stdout=subprocess.DEVNULL)  # noisy
    subprocess.run(['git', '-C', repo_path, 'tag', 'v1.5'])

    # add new file
    Path(repo_path).joinpath('new_file').write_text(''.join([f"{i}\n" for i in range(10)]))
    subprocess.run(['git', '-C', repo_path, 'add', 'new_file'], check=True)
    # change file
    Path(repo_path).joinpath('subdir', 'subfile').write_text('subfile\nsubfile\n')
    # rename file, and change it a bit
    Path(repo_path).joinpath('example_file').write_text('example\n2\n3\n4b\n5\n')
    subprocess.run(['git', '-C', repo_path, 'mv',
                    'example_file', 'renamed_file'], check=True)
    # commit changes
    subprocess.run(['git', '-C', repo_path, 'commit', '-a',
                    '-m', 'Change some files\n\n* one renamed file\n* one new file'],
                   env=dict(
                       # inherit environment variables
                       os.environ,
                       # configure git-commit behavior
                       # see https://git-scm.com/docs/git-commit#_commit_information
                       GIT_AUTHOR_NAME='Joe Random',
                       GIT_AUTHOR_EMAIL='joe@random.com',
                       GIT_AUTHOR_DATE='1693605193 -0600',
                   ),
                   check=True, stdout=subprocess.DEVNULL)  # noisy
    # tag for easy access
    subprocess.run(['git', '-C', repo_path, 'tag', 'v2'])

    return GitRepo(repo_path)

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


## ----------------------------------------------------------------------
## add a --run-slow command line option to control skipping of pytest.mark.slow marked tests
## https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option
def pytest_addoption(parser):
    parser.addoption(
        "--run-slow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-slow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


## ----------------------------------------------------------------------
## fixtures


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
    subprocess.run(['git', '-c', f'init.defaultBranch={default_branch}', 'init', repo_path],
                   check=True, stdout=subprocess.DEVNULL)  # noisy
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


@pytest.fixture(scope="module")  # like unittest.setUpClass()
def example_repo_utf8(tmp_path_factory: pytest.TempPathFactory) -> GitRepo:
    """Prepare a Git repository with utf-8 names for testing `utils.git` module"""
    tmp_path = tmp_path_factory.mktemp('repos')

    repo_name = 'test_utils_git-repo_utf8'
    repo_path = str(tmp_path / repo_name)

    # initialize repository and  configure it
    subprocess.run(['git', '-c', f'init.defaultBranch={default_branch}', 'init', repo_path],
                   check=True, stdout=subprocess.DEVNULL)  # noisy
    subprocess.run(['git', '-C', repo_path, 'config', 'user.name', 'A U Þór'], check=True)
    subprocess.run(['git', '-C', repo_path, 'config', 'user.email', 'author@example.com'], check=True)
    subprocess.run(['git', '-C', repo_path, 'branch', '-m', default_branch], check=True)

    # create files, and initial commit
    Path(repo_path).joinpath('przykładowy plik').write_text('zażółć\ngęsią\njaźń\n', encoding='utf-8')
    subprocess.run(['git', '-C', repo_path, 'add', '.'], check=True)

    subprocess.run(['git', '-C', repo_path, 'commit', '-m', 'Początkowy commit'],
                   check=True, stdout=subprocess.DEVNULL)  # noisy
    subprocess.run(['git', '-C', repo_path, 'tag', 'v1'])

    # change file, creating a new commit
    Path(repo_path).joinpath('przykładowy plik').write_text(
        'zażółć\ngęślą\njaźń\n\n'
        'Pójdź, kińże tę chmurność w głąb flaszy!',
        encoding = 'utf-8',
    )
    subprocess.run(['git', '-C', repo_path, 'commit', '-a', '-m', 'Zmieniono "przykładowy plik"'],
                   check=True, stdout=subprocess.DEVNULL)  # noisy
    subprocess.run(['git', '-C', repo_path, 'tag', 'v2'])

    return GitRepo(repo_path)


@pytest.fixture(scope="module")  # like unittest.setUpClass()
def example_repo_binary(tmp_path_factory: pytest.TempPathFactory) -> GitRepo:
    """Prepare a Git repository with "binary" files for testing `utils.git` module"""
    tmp_path = tmp_path_factory.mktemp('repos')

    repo_name = 'test_utils_git-binary'
    repo_path = str(tmp_path / repo_name)

    # initialize repository and  configure it
    subprocess.run(['git', '-c', f'init.defaultBranch={default_branch}', 'init', repo_path],
                   check=True, stdout=subprocess.DEVNULL)  # noisy
    subprocess.run(['git', '-C', repo_path, 'config', 'user.name', 'Joe Random'], check=True)
    subprocess.run(['git', '-C', repo_path, 'config', 'user.email', 'joe@example.com'], check=True)
    subprocess.run(['git', '-C', repo_path, 'branch', '-m', default_branch], check=True)

    # create a "binary" file, and initial commit
    Path(repo_path).joinpath('example.bin').write_bytes(b'\x00\x01\x02\x03\x04\x05\x06\x07')
    Path(repo_path).joinpath('README.md').write_text('# Example repository\n')
    subprocess.run(['git', '-C', repo_path, 'add', '.'],
                   check=True)
    subprocess.run(['git', '-C', repo_path, 'commit', '-m', 'Initial commit'],
                   check=True, stdout=subprocess.DEVNULL)  # noisy
    subprocess.run(['git', '-C', repo_path, 'tag', 'v1'],
                   check=True)

    # change a "binary" file, creating a new commit
    Path(repo_path).joinpath('example.bin').write_bytes(b'\x00\x08\x09\x0a\x00\x00')
    subprocess.run(['git', '-C', repo_path, 'commit', '-a', '-m', 'Changed example.bin file'],
                   check=True, stdout=subprocess.DEVNULL)  # noisy
    subprocess.run(['git', '-C', repo_path, 'tag', 'v2'],
                   check=True)

    return GitRepo(repo_path)


## ----------------------------------------------------------------------
## helper functions


def count_pm_lines(changes_data: dict) -> tuple[int, int]:
    """Count number of '-' and '+' lines in changes part of annotation data

    :param changes_data: information about changes extracted from annotation data;
        in the v2 data format this data is available at the 'changes' key
    :return: (total number of '-' lines, total number of '+' lines)
    """
    total_p = total_m = 0
    for file_name, file_data in changes_data.items():  # we are not interested in file names here
        for data_key, data_value in file_data.items():
            if data_key == '-':
                total_m += len(data_value)
            elif data_key == '+':
                total_p += len(data_value)

    return total_m, total_p


# end of file tests/conftest.py


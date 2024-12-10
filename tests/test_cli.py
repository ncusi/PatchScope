# -*- coding: utf-8 -*-
"""Test cases for all typer-based command line (CLI) scripts

https://typer.tiangolo.com/tutorial/testing/
"""
import json
import subprocess
import traceback
from pathlib import Path

import pytest
from typer.testing import CliRunner

from diffannotator.annotate import app as annotate_app, Bug
from diffannotator.generate_patches import app as generate_app
from diffannotator.gather_data import app as gather_app
from diffannotator.utils.git import GitRepo
from .conftest import count_pm_lines

runner = CliRunner()


#-----------------------------------------------------------------------------
# testing annotate_app


def test_annotate_patch(tmp_path: Path):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(annotate_app, ["patch", f"{file_path}", f"{save_path}"])

    # TODO: extract this common code into conftest.py, maybe as a pytest plugin
    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand without errors"
    assert save_path.is_file(), \
        "app created file with results"
    assert "Annotating" in result.stdout and "Saving results" in result.stdout, \
        "app prints expected output"


def test_annotate_dataset(tmp_path: Path):
    dataset_dir = Path('tests/test_dataset_structured')

    result = runner.invoke(annotate_app, ["dataset", f"--output-prefix={tmp_path}", f"{dataset_dir}"])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'dataset' subcommand without errors"
    assert f"{dataset_dir}" in result.stdout, \
        "app prints about processing the dataset"


def test_annotate_dataset_with_fanout(tmp_path: Path):
    dataset_dir = Path('tests/test_dataset_fanout')

    result = runner.invoke(annotate_app, [
        "dataset", f"--output-prefix={tmp_path}", f"{dataset_dir}",
        "--patches-dir=", "--annotations-dir=",
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'dataset' subcommand without errors"
    assert f"{dataset_dir}" in result.stdout, \
        "app prints about processing the dataset"


def test_annotate_from_repo(tmp_path: Path):
    # TODO: create a fixture with a common code
    test_repo_url = 'https://github.com/githubtraining/hellogitworld.git'
    repo_dir = tmp_path / 'hellogitworld'
    output_dir = tmp_path / 'annotation'

    # clone the repository "by hand"
    subprocess.run([
        'git', '-C', str(tmp_path), 'clone', test_repo_url
    ], capture_output=True, check=True)

    # without --use-fanout
    result = runner.invoke(annotate_app, [
        "from-repo",
        f"--output-dir={output_dir}",
        str(repo_dir),
        '-5', 'HEAD'  # 5 latest commit on the current branch
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'from-repo' subcommand without errors"
    assert f"{output_dir}" in result.stdout, \
        "app prints about the output directory"
    assert f"{repo_dir}" in result.stdout, \
        "app mentions the path to the Git repository"
    assert output_dir.exists() and output_dir.is_dir(), \
        "app created the output directory (or it existed)"

    # with --use-fanout
    result = runner.invoke(annotate_app, [
        "from-repo",
        f"--output-dir={output_dir}",
        "--use-fanout",
        str(repo_dir),
        '-5', 'HEAD'  # 5 latest commit on the current branch
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'from-repo --with-fanout' subcommand without errors"


# faster way of providing Git repository than cloning it from GitHub
def test_annotate_from_repo_parallel(tmp_path: Path, example_repo: GitRepo):
    repo_dir = example_repo.repo
    output_dir = tmp_path / 'annotation'

    result = runner.invoke(annotate_app, [
        "from-repo",
        f"--output-dir={output_dir}",
        "--n_jobs=2",
        str(repo_dir),
        '-2', 'HEAD'  # 5 latest commit on the current branch
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'from-repo --n_jobs=2' subcommand without errors"


def test_annotate_patch_with_line_callback(tmp_path: Path):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    # callback as string
    result = runner.invoke(annotate_app, [
        "--line-callback", "return None",  # no-op line callback
        "patch", f"{file_path}", f"{save_path}"
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with a no-op line str callback without errors"
    # NOTE: this check is performed only once
    assert "custom line callback" in result.stdout, \
        "app mentions that there was custom line callback"

    # callback as file, just body of function
    callback_path = Path('tests/test_code_fragments/example_line_callback.py.body')
    result = runner.invoke(annotate_app, [
        f"--line-callback", f"{callback_path}",  # file with line callback
        "patch", f"{file_path}", f"{save_path}"
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with line callback from file defining body without errors"

    # callback as file, full definition of function, starting at first line
    callback_path = Path('tests/test_code_fragments/example_line_callback_func.py')
    result = runner.invoke(annotate_app, [
        f"--line-callback", f"{callback_path}",  # file with line callback
        "patch", f"{file_path}", f"{save_path}"
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with line callback from file defining function without errors"


def test_annotate_patch_with_line_callback_hapybug(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    #file_path = Path('tests/test_dataset_structured/scrapy-11/patches/9de6f1ca757b7f200d15e94840c9d431cf202276.diff')
    #file_path = Path('tests/test_dataset_structured/keras-10/patches/c1c4afe60b1355a6c0e83577791a0423f37a3324.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.v2.json')

    # callback as file, full definition of function
    callback_path = Path('data/experiments/HaPy-Bug/hapybug_line_callback_func.py')
    result = runner.invoke(annotate_app, [
        f"--line-callback", f"{callback_path}",  # file with line callback
        "patch", f"{file_path}", f"{save_path}"
    ])

    if result.exit_code != 0:
        print(f"Exit code: {result.exit_code}")
        print(result.stdout)
    if caplog.text:
        print("Captured logs:")
        print(caplog.text)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with line callback from file defining function without errors"

    annotation_data: dict = json.loads(save_path.read_text())
    #from rich.pretty import pprint
    #print(result.stdout)
    #pprint(annotation_data)
    assert annotation_data['changes']['tqdm/contrib/__init__.py']['+'][0]['type'] == 'bug(fix)', \
        "the callback was run, and it did provide 'bug(fix)' as line type for code changes"


def test_annotate_patch_with_purpose_to_annotation(tmp_path: Path):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(annotate_app, [
        "--purpose-to-annotation=",  # reset mapping
        "--purpose-to-annotation=docs:documentation",  # explicit mapping
        "--purpose-to-annotation=test",  # implicit mapping
        "patch", f"{file_path}", f"{save_path}"
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with a --purpose-to-annotation without errors"
    assert \
        "documentation\t=>\tdocumentation" not in result.stdout and \
        "docs\t=>\tdocumentation" in result.stdout and \
        "test\t=>\ttest" in result.stdout, \
        "app correctly prints that mapping changed to the requested values"


# NOTE: some duplication with/similarities to test_annotate_patch_with_purpose_to_annotation
def test_annotate_patch_with_pattern_to_purpose(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(annotate_app, [
        "--pattern-to-purpose=",  # reset mapping
        "--pattern-to-purpose=tests/test_*.py:test",  # explicit mapping
        "--pattern-to-purpose=test",  # implicit mapping, should warn
        "patch", f"{file_path}", f"{save_path}"
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    separator = " has purpose "
    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with a --pattern-to-purpose without errors"
    assert f"CMakeLists.txt{separator}project" not in result.stdout, \
        "app resets the mapping with empty --pattern-to-purpose, removing defaults"
    assert f"tests/test_*.py{separator}test" in result.stdout, \
        "app adds the requested mapping with --pattern-to-purpose"
    assert \
        f"test{separator}test" not in result.stdout and \
        "Warning: --pattern-to-purpose=test ignored" in caplog.text, \
        "app does not add mapping via --pattern-to-purpose=<pattern> (no purpose)"


def test_annotate_patch_with_ext_to_language(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(annotate_app, [
        "--ext-to-language=.lock:YAML",  # explicit mapping; not something true in general
        "patch", f"{file_path}", f"{save_path}"
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with a --ext-to-language without errors"
    assert ".lock" in result.stdout and "YAML" in result.stdout, \
        "app correctly prints that ext mapping changed to the requested values"

    result = runner.invoke(annotate_app, [
        "--ext-to-language=",  # clear the mapping
        "--ext-to-language=.extension",  # extension without language name
        "patch", f"{file_path}", f"{save_path}"
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)
    #print(f"{caplog.messages=}")
    #print(f"{caplog.records=}")
    #print(f"{caplog.record_tuples=}")

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with special cases of --ext-to-language without errors"
    assert "Warning:" in caplog.text and ".extension ignored" in caplog.text, \
        "app warns about --ext-to-language with value without colon (:)"
    assert "Cleared mapping from file extension to programming language" in result.stdout, \
        "app mentions that it cleared mapping because of empty value of --ext-to-language"


# TODO: very similar to previous test, use parametrized test
def test_annotate_patch_with_filename_to_language(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(annotate_app, [
        "--filename-to-language=LICENSE:txt",  # explicit mapping with unique language name
        "patch", f"{file_path}", f"{save_path}"
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with a --filename-to-language without errors"
    assert "LICENSE" in result.stdout and "txt" in result.stdout, \
        "app correctly prints that ext mapping changed to the requested values"

    result = runner.invoke(annotate_app, [
        "--filename-to-language=",  # clear the mapping
        "--filename-to-language=COPYING",  # extension without language name
        "patch", f"{file_path}", f"{save_path}"
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with special cases of --filename-to-language without errors"
    assert "Warning:" in caplog.text and "COPYING ignored" in caplog.text, \
        "app warns about --filename-to-language with value without colon (:)"
    assert "Cleared mapping from filename to programming language" in result.stdout, \
        "app mentions that it cleared mapping because of empty value of --filename-to-language"


#-----------------------------------------------------------------------------
# testing generate_app


def test_generate_patches(tmp_path: Path):
    test_repo_url = 'https://github.com/githubtraining/hellogitworld.git'
    repo_dir = tmp_path / 'hellogitworld'
    output_dir = tmp_path / 'patches'

    # clone the repository "by hand"
    subprocess.run([
        'git', '-C', str(tmp_path), 'clone', test_repo_url
    ], capture_output=True, check=True)

    result = runner.invoke(generate_app, [
        f"--output-dir={output_dir}",
        str(repo_dir),
        '-5', 'HEAD'  # 5 latest commit on the current branch
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "generate app runs without errors"
    assert output_dir.is_dir(), \
        "output directory exists, and is directory"
    patches_paths = list(output_dir.glob('*'))
    assert len(patches_paths) == 5, \
        "generate app created 5 patch files"
    assert all([path.suffix == '.patch' for path in patches_paths]), \
        "all created files have '.patch' suffix"


def test_generate_patches_with_fanout(tmp_path: Path):
    test_repo_url = 'https://github.com/githubtraining/hellogitworld.git'
    repo_dir = tmp_path / 'hellogitworld'
    output_dir = tmp_path / 'patches'

    # clone the repository "by hand"
    subprocess.run([
        'git', '-C', str(tmp_path), 'clone', test_repo_url
    ], capture_output=True, check=True)

    result = runner.invoke(generate_app, [
        f"--output-dir={output_dir}",
        "--use-fanout",
        str(repo_dir),
        '-5', 'HEAD'  # 5 latest commit on the current branch
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "generate app runs without errors"
    assert output_dir.is_dir(), \
        "output directory exists, and is directory"
    subdir_paths = list(output_dir.glob('*'))
    total_diffs = 0
    for path in subdir_paths:
        #print(f"{path=!s}")
        assert len(path.name) == 2, \
            "fan-out directory uses name with length of 2"
        for diff_file in path.glob('*.diff'):
            #print(f"diff_file={diff_file.name}")
            total_diffs += 1
            assert diff_file.is_file(), \
                "*.diff files are files"
            assert len(diff_file.name) == 40 - 2 + 5, \
                "*.diff files have expected file name length"

    # NOTE: somehow this test is unreliable on MS Windows
    # it fails unless print statements are un-commented
    #assert total_diffs == 5, \
    #    "generate app created 5 diff files"
    print(f"{total_diffs=}/5")


#-----------------------------------------------------------------------------
# testing gather_app


def test_gather_data(tmp_path: Path):
    dataset_dir_patches = Path('tests/test_dataset_structured')

    ### preparation: generating annotations
    # TODO: create fixture creating annotations, split the test
    # TODO: or create parametrized test to avoid repetition; might be not possible
    result = runner.invoke(annotate_app, [
        # select subcommand
        "dataset",
        # pass options and arguments to subcommand
        f"--output-prefix={tmp_path}",
        f"{dataset_dir_patches}",
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "annotate app runs 'dataset' subcommand on structured dataset without errors"

    # DEBUG
    #json_files = sorted(tmp_path.glob('**/*.json'))
    #print(f"{tmp_path=}")
    #print(f"{json_files=}")

    ### testing 'purpose-counter' subcommand

    dataset_dir_annotations = tmp_path / dataset_dir_patches
    json_path = Path(f"{dataset_dir_annotations}.purpose-counter.json")
    result = runner.invoke(gather_app, [
        # exercise common arguments
        f"--annotations-dir={Bug.DEFAULT_ANNOTATIONS_DIR}",  # should and must be no-op
        # select subcommand
        "purpose-counter",
        # pass options and arguments to subcommand
        f"--output={json_path}",
        f"{dataset_dir_annotations}",
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "gather app runs 'purpose-counter' subcommand on generated annotations without errors"
    assert json_path.is_file(), \
        "output file app was requested to use exists (it was created)"
    assert json_path.stat().st_size > 0, \
        "generated JSON file with results is not empty"

    # DEBUG
    #print(json_path.read_text())

    ### testing 'purpose-per-file' subcommand

    json_path = Path(f"{dataset_dir_annotations}.purpose-per-file.json")
    result = runner.invoke(gather_app, [
        # select subcommand
        "purpose-per-file",
        # pass options and arguments to subcommand
        f"{json_path}",
        f"{dataset_dir_annotations}",
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "gather app runs 'purpose-per-file' subcommand on generated annotations without errors"
    assert json_path.is_file(), \
        "output 'purpose-per-file' file app was requested to use exists (it was created)"
    assert json_path.stat().st_size > 0, \
        "generated 'purpose-per-file' JSON file with results is not empty"

    # DEBUG
    #print(json_path.read_text())


    ### for 'lines-stats'

    json_path = Path(f"{dataset_dir_annotations}.lines-stats.json")
    result = runner.invoke(gather_app, [
        # select subcommand
        "lines-stats",
        # pass options and arguments to subcommand
        f"{json_path}",
        f"{dataset_dir_annotations}",
    ])

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "gather app runs 'lines-stats' subcommand on generated annotations without errors"
    assert json_path.is_file(), \
        "output 'lines-stats' file app was requested to use exists (it was created)"
    assert json_path.stat().st_size > 0, \
        "generated 'lines-stats' JSON file with results is not empty"

    # DEBUG
    #print(json_path.read_text())

    ### for 'timeline'

    #dataset_dir_annotations = 'tests/test_dataset_annotated'
    json_path = Path(f"{dataset_dir_annotations}.timeline.json")
    result = runner.invoke(gather_app, [
        # select subcommand
        "timeline",
        # pass options and arguments to subcommand
        "--purpose-to-annotation=test:test",  # full
        "--purpose-to-annotation=other",      # simplified
        f"{json_path}",
        f"{dataset_dir_annotations}",
    ])

    #print(result.stdout)
    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "gather app runs 'timeline' subcommand on generated annotations without errors"
    assert json_path.is_file(), \
        "output 'timeline' file app was requested to use exists (it was created)"
    assert json_path.stat().st_size > 0, \
        "generated 'timeline' JSON file with results is not empty"


def test_annotate_then_gather_data_sizes_and_spreads(tmp_path: Path):
    """Use the example where previously -/+ counts didn't match n_rem, n_mod, n_add"""
    # see notebooks/panel/01-timeline.ipynb at caa24f9f5941cdd497bdf046dab8b13f3e8e34d1
    file_path = 'tests/test_dataset/tensorflow/87de301db14745ab920d7e32b53d926236a4f2af.diff'
    basename = Path(file_path).stem
    annotation_path = tmp_path.joinpath('tensorflow', basename[:7], basename).with_suffix('.v2.json')

    ## DEBUG
    #print(f"{tmp_path=}")
    #print(f"{file_path=}")
    #print(f"{basename=}")
    #print(f"{annotation_path=}")

    ### preparation: generating annotations

    result = runner.invoke(annotate_app, [
        # select subcommand
        "patch",
        # pass options and arguments to subcommand
        f"{file_path}",  # PATCH_FILE
        f"{annotation_path}",
    ])

    ## DEBUG
    #print(result.stdout)

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    # DEBUG
    #print(json_path.read_text())

    assert result.exit_code == 0, \
        "'diff-annotate patch' runs on given *.diff file without errors"
    assert annotation_path.exists(), \
        "'diff-annotate patch' produced requested file"

    annotation_data: dict = json.loads(annotation_path.read_text())

    ## DEBUG
    #from rich.pretty import pprint  # OR: from pprint import pprint
    #pprint(annotation_data, max_length=12)  # max_length require rich.pprint
    assert annotation_data['commit_metadata']['id'] == basename, \
        "'diff-annotate patch' correctly extracted commit id from input file name"
    assert 'changes' in annotation_data, \
        "'diff-annotate patch' uses v2 file format for output"

    # noinspection PyDictCreation
    total = {}  # don't want to run count_pm_lines() twice
    total['-'], total['+'] = count_pm_lines(annotation_data['changes'])

    ### processing: generating timeline

    # dataset_dir_annotations = 'tests/test_dataset_annotated'
    timeline_path = annotation_path.with_suffix('.timeline.json')
    result = runner.invoke(gather_app, [
        # common arguments
        "--annotations-dir=",
        # select subcommand
        "timeline",
        # pass options and arguments to subcommand
        f"{timeline_path}",  # FILE
        f"{annotation_path.parent.parent}",  # DATASETS...
    ])

    ## DEBUG
    #print(result.stdout)

    if result.exit_code != 0:
        print(result.stdout)
    if result.exception:
        print(f"Exception: {result.exception}")
        print("Traceback:")
        # or `result.exc_info[2]` instead of `result.exception.__traceback__`
        traceback.print_tb(result.exception.__traceback__)

    assert result.exit_code == 0, \
        "'diff-gather-stats timeline' runs on generated annotations without errors"
    assert timeline_path.exists() and timeline_path.is_file(), \
        "'diff-gather-stats timeline' produces requested file"
    assert timeline_path.stat().st_size > 0, \
        "'diff-gather-stats timeline' produces non-empty file"

    timeline_data: dict = json.loads(timeline_path.read_text())

    ## DEBUG
    #from rich.pretty import pprint  # OR: from pprint import pprint
    #pprint(timeline_data, max_length=12)  # max_length require rich.pprint

    # sanity checks
    assert 'tensorflow' in timeline_data and len(timeline_data['tensorflow']) == 1, \
        "'diff-gather-stats timeline' produced single-bug result for 'tensorflow' dataset"
    assert timeline_data['tensorflow'][0]['bug_id'] == basename[:7], \
        "'diff-gather-stats timeline' sets 'bug_id' to subdirectory name"
    assert timeline_data['tensorflow'][0]['patch_id'] == annotation_path.name, \
        "'diff-gather-stats timeline' sets 'bug_id' remembers name of annotation file"

    # checking data extraction
    assert (len(annotation_data['changes']) ==
            annotation_data['diff_metadata']['n_files'] ==         # there were no renamed files
            timeline_data['tensorflow'][0]['file_names'] ==
            timeline_data['tensorflow'][0]['diff.n_files']), \
        "all way of counting affected file names by the used 'diff-*' command matches"
    for pm in ['-', '+']:
        assert total[pm] == timeline_data['tensorflow'][0][f"{pm}:count"], \
            f"'diff-gather-stats timeline' correctly computes '{pm}:count'"
    for diff_size_metric in ['n_rem', 'n_mod', 'n_add']:
        assert (getattr(annotation_data['diff_metadata'], diff_size_metric, 0) ==
                getattr(timeline_data['tensorflow'][0], diff_size_metric, 0)), \
            f"'diff-annotate patch' and 'diff-gather-stats timeline' match on '{diff_size_metric}'"
    # NOTE: testing that -/+ counts match with 'n_rem', 'n_mod', 'n_add' are checked in different test

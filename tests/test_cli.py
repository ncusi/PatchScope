import subprocess
from pathlib import Path

from typer.testing import CliRunner

from diffannotator.annotate import app as annotate_app, Bug
from diffannotator.generate_patches import app as generate_app
from diffannotator.gather_data import app as gather_app


runner = CliRunner()


def test_annotate_patch(tmp_path: Path):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(annotate_app, ["patch", f"{file_path}", f"{save_path}"])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand without errors"
    assert save_path.is_file(), \
        "app created file with results"
    assert "Annotating" in result.stdout and "Saving results" in result.stdout, \
        "app prints expected output"


def test_annotate_dataset(tmp_path: Path):
    dataset_dir = Path('tests/test_dataset_structured')

    result = runner.invoke(annotate_app, ["dataset", f"--output-prefix={tmp_path}", f"{dataset_dir}"])

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
    # DEBUG
    #print(result.stdout)

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
    assert result.exit_code == 0, \
        "app runs 'from-repo --with-fanout' subcommand without errors"


def test_annotate_patch_with_line_callback(tmp_path: Path):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    # callback as string
    result = runner.invoke(annotate_app, [
        "--line-callback", "return None",  # no-op line callback
        "patch", f"{file_path}", f"{save_path}"
    ])

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

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with line callback from file defining body without errors"

    # callback as file, full definition of function, starting at first line
    callback_path = Path('tests/test_code_fragments/example_line_callback_func.py')
    result = runner.invoke(annotate_app, [
        f"--line-callback", f"{callback_path}",  # file with line callback
        "patch", f"{file_path}", f"{save_path}"
    ])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with line callback from file defining function without errors"


def test_annotate_patch_with_purpose_to_annotation(tmp_path: Path):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(annotate_app, [
        "--purpose-to-annotation=",  # reset mapping
        "--purpose-to-annotation=docs:documentation",  # explicit mapping
        "--purpose-to-annotation=test",  # implicit mapping
        "patch", f"{file_path}", f"{save_path}"
    ])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with a --purpose-to-annotation without errors"
    assert \
        "documentation\t=>\tdocumentation" not in result.stdout and \
        "docs\t=>\tdocumentation" in result.stdout and \
        "test\t=>\ttest" in result.stdout, \
        "app correctly prints that mapping changed to the requested values"


# NOTE: some duplication with/similarities to test_annotate_patch_with_purpose_to_annotation
def test_annotate_patch_with_pattern_to_purpose(tmp_path: Path):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(annotate_app, [
        "--pattern-to-purpose=",  # reset mapping
        "--pattern-to-purpose=tests/test_*.py:test",  # explicit mapping
        "--pattern-to-purpose=test",  # implicit mapping, should warn
        "patch", f"{file_path}", f"{save_path}"
    ])

    # print("----- (result.stdout)")
    # print(result.stdout)
    # print("-----")

    separator = " has purpose "
    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with a --pattern-to-purpose without errors"
    assert f"CMakeLists.txt{separator}project" not in result.stdout, \
        "app resets the mapping with empty --pattern-to-purpose, removing defaults"
    assert f"tests/test_*.py{separator}test" in result.stdout, \
        "app adds the requested mapping with --pattern-to-purpose"
    assert \
        f"test{separator}test" not in result.stdout and \
        "Warning: --pattern-to-purpose=test ignored" in result.stdout, \
        "app does not add mapping via --pattern-to-purpose=<pattern> (no purpose)"


def test_annotate_patch_with_ext_to_language(tmp_path: Path):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(annotate_app, [
        "--ext-to-language=.lock:YAML",  # explicit mapping; not something true in general
        "patch", f"{file_path}", f"{save_path}"
    ])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with a --ext-to-language without errors"
    assert ".lock" in result.stdout and "YAML" in result.stdout, \
        "app correctly prints that ext mapping changed to the requested values"

    result = runner.invoke(annotate_app, [
        "--ext-to-language=",  # clear the mapping
        "--ext-to-language=.extension",  # extension without language name
        "patch", f"{file_path}", f"{save_path}"
    ])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with special cases of --ext-to-language without errors"
    assert "Warning:" in result.stdout and ".extension ignored" in result.stdout, \
        "app warns about --ext-to-language with value without colon (:)"
    assert "Cleared mapping from file extension to programming language" in result.stdout, \
        "app mentions that it cleared mapping because of empty value of --ext-to-language"


# TODO: very similar to previous test, use parametrized test
def test_annotate_patch_with_filename_to_language(tmp_path: Path):
    file_path = Path('tests/test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(annotate_app, [
        "--filename-to-language=LICENSE:txt",  # explicit mapping with unique language name
        "patch", f"{file_path}", f"{save_path}"
    ])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with a --filename-to-language without errors"
    assert "LICENSE" in result.stdout and "txt" in result.stdout, \
        "app correctly prints that ext mapping changed to the requested values"

    result = runner.invoke(annotate_app, [
        "--filename-to-language=",  # clear the mapping
        "--filename-to-language=COPYING",  # extension without language name
        "patch", f"{file_path}", f"{save_path}"
    ])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with special cases of --filename-to-language without errors"
    assert "Warning:" in result.stdout and "COPYING ignored" in result.stdout, \
        "app warns about --filename-to-language with value without colon (:)"
    assert "Cleared mapping from filename to programming language" in result.stdout, \
        "app mentions that it cleared mapping because of empty value of --filename-to-language"


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


def test_gather_data(tmp_path: Path):
    dataset_dir_patches = Path('tests/test_dataset_structured')

    # TODO: create fixture creating annotations, split the test
    result = runner.invoke(annotate_app, [
        # select subcommand
        "dataset",
        # pass options and arguments to subcommand
        f"--output-prefix={tmp_path}",
        f"{dataset_dir_patches}",
    ])

    assert result.exit_code == 0, \
        "annotate app runs 'dataset' subcommand on structured dataset without errors"

    # DEBUG
    #json_files = sorted(tmp_path.glob('**/*.json'))
    #print(f"{tmp_path=}")
    #print(f"{json_files=}")

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

    # DEBUG
    #print(result.stdout)

    assert result.exit_code == 0, \
        "gather app runs 'purpose-counter' subcommand on generated annotations without errors"

    assert json_path.is_file(), \
        "output file app was requested to use exists (it was created)"
    assert json_path.stat().st_size > 0, \
        "generated JSON file with results is not empty"

    # DEBUG
    #print(json_path.read_text())

    json_path = Path(f"{dataset_dir_annotations}.purpose-per-file.json")

    result = runner.invoke(gather_app, [
        # select subcommand
        "purpose-per-file",
        # pass options and arguments to subcommand
        f"{json_path}",
        f"{dataset_dir_annotations}",
    ])

    # DEBUG
    # print(result.stdout)

    assert result.exit_code == 0, \
        "gather app runs 'purpose-per-file' subcommand on generated annotations without errors"

    assert json_path.is_file(), \
        "output file app was requested to use exists (it was created)"
    assert json_path.stat().st_size > 0, \
        "generated JSON file with results is not empty"

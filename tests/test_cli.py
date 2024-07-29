import subprocess
from pathlib import Path

from typer.testing import CliRunner

from diffannotator.annotate import app as annotate_app
from diffannotator.generate_patches import app as generate_app


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


def test_annotate_from_repo(tmp_path: Path):
    # TODO: create a fixture with a common code
    test_repo_url = 'https://github.com/githubtraining/hellogitworld.git'
    repo_dir = tmp_path / 'hellogitworld'
    output_dir = tmp_path / 'annotation'

    # clone the repository "by hand"
    subprocess.run([
        'git', '-C', str(tmp_path), 'clone', test_repo_url
    ], capture_output=True, check=True)

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

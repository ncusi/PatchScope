from pathlib import Path

from typer.testing import CliRunner

from diffannotator.annotate import app


runner = CliRunner()


def test_annotate_patch(tmp_path: Path):
    file_path = Path('test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(app, ["patch", f"{file_path}", f"{save_path}"])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand without errors"
    assert save_path.is_file(), \
        "app created file with results"
    assert "Annotating" in result.stdout and "Saving results" in result.stdout, \
        "app prints expected output"


def test_annotate_dataset(tmp_path: Path):
    dataset_dir = Path('test_dataset_structured')

    result = runner.invoke(app, ["dataset", f"--output-prefix={tmp_path}", f"{dataset_dir}"])

    assert result.exit_code == 0, \
        "app runs 'dataset' subcommand without errors"
    assert f"{dataset_dir}" in result.stdout, \
        "app prints about processing the dataset"


def test_annotate_patch_with_line_callback(tmp_path: Path):
    file_path = Path('test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    # callback as string
    result = runner.invoke(app, [
        "--line-callback", "return None",  # no-op line callback
        "patch", f"{file_path}", f"{save_path}"
    ])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with a no-op line str callback without errors"
    # NOTE: this check is performed only once
    assert "custom line callback" in result.stdout, \
        "app mentions that there was custom line callback"

    # callback as file, just body of function
    callback_path = Path('test_code_fragments/example_line_callback.py.body')
    result = runner.invoke(app, [
        f"--line-callback", f"{callback_path}",  # file with line callback
        "patch", f"{file_path}", f"{save_path}"
    ])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with line callback from file defining body without errors"

    # callback as file, full definition of function, starting at first line
    callback_path = Path('test_code_fragments/example_line_callback_func.py')
    result = runner.invoke(app, [
        f"--line-callback", f"{callback_path}",  # file with line callback
        "patch", f"{file_path}", f"{save_path}"
    ])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with line callback from file defining function without errors"


def test_annotate_patch_with_purpose_to_annotation(tmp_path: Path):
    file_path = Path('test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(app, [
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
    file_path = Path('test_dataset/tqdm-1/c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff')
    save_path = tmp_path.joinpath(file_path).with_suffix('.json')

    result = runner.invoke(app, [
        "--ext-to-language=.lock:YAML",  # explicit mapping; not something true in general
        "patch", f"{file_path}", f"{save_path}"
    ])

    assert result.exit_code == 0, \
        "app runs 'patch' subcommand with a --ext-to-language without errors"
    assert ".lock" in result.stdout and "YAML" in result.stdout, \
        "app correctly prints that ext mapping changed to the requested values"

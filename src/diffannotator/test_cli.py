from pathlib import Path

from typer.testing import CliRunner

from annotate import app


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

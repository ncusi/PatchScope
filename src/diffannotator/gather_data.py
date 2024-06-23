#!/usr/bin/env python
import json
import os
from collections import Counter
from pathlib import Path
from typing import List, TypeVar

import tqdm
import typer
from typing_extensions import Annotated

PathLike = TypeVar("PathLike", str, bytes, Path, os.PathLike)

app = typer.Typer(no_args_is_help=True, add_completion=False)


class AnnotatedFile:
    """Annotated single file in specific bug"""

    def __init__(self, file_path: PathLike):
        """Constructor of the annotated file of specific bug

        :param file_path: path to the single file
        """
        self._path = Path(file_path)

    def gather_data(self):
        with self._path.open('r') as json_file:
            hunk_purposes = Counter()
            added_line_purposes = Counter()
            removed_line_purposes = Counter()
            data = json.load(json_file)
            for hunk in data:
                print(hunk)
                print(data[hunk]['purpose'])
                hunk_purposes[data[hunk]['purpose']] += 1
                if '+' in data[hunk]:
                    added_lines = data[hunk]['+']
                    for added_line in added_lines:
                        added_line_purposes[added_line['purpose']] += 1
                if '-' in data[hunk]:
                    removed_lines = data[hunk]['-']
                    for removed_line in removed_lines:
                        removed_line_purposes[removed_line['purpose']] += 1
            return hunk_purposes, added_line_purposes, removed_line_purposes


class AnnotatedBug:
    """Annotated bug class"""

    def __init__(self, bug_dir: PathLike):
        """Constructor of the annotated bug

        :param bug_dir: path to the single bug
        """
        self._path = Path(bug_dir)
        self._annotations_path = self._path / "annotation"

        try:
            self.annotations = [str(d.name) for d in self._annotations_path.iterdir()]
        except Exception as ex:
            print(f"Error in AnnotatedBug for '{self._path}': {ex}")

    def gather_data(self):
        bug_hunk_purposes = Counter()
        bug_added_line_purposes = Counter()
        bug_removed_line_purposes = Counter()
        for annotation in self.annotations:
            if '...' in annotation:
                continue
            annotation_file_path = self._annotations_path / annotation
            annotation_file = AnnotatedFile(annotation_file_path)
            hunk_purposes, added_line_purposes, removed_line_purposes = annotation_file.gather_data()
            bug_hunk_purposes.update(hunk_purposes)
            bug_added_line_purposes.update(added_line_purposes)
            bug_removed_line_purposes.update(removed_line_purposes)
        return bug_hunk_purposes, bug_added_line_purposes, bug_removed_line_purposes


class AnnotatedBugDataset:
    """Annotated bugs dataset class"""

    def __init__(self, dataset_dir: PathLike):
        """Constructor of the annotated bug dataset.

        :param dataset_dir: path to the dataset
        """
        self._path = Path(dataset_dir)
        self.bugs: List[str] = []

        try:
            self.bugs = [str(d.name) for d in self._path.iterdir()
                         if d.is_dir()]
        except Exception as ex:
            print(f"Error in AnnotatedBugDataset for '{self._path}': {ex}")

    def gather_data(self):
        dataset_hunk_purposes = Counter()
        dataset_added_line_purposes = Counter()
        dataset_removed_line_purposes = Counter()
        for bug_id in tqdm.tqdm(self.bugs):
            print(bug_id)
            bug_path = self._path / bug_id
            bug = AnnotatedBug(bug_path)
            bug_hunk_purposes, bug_added_line_purposes, bug_removed_line_purposes = bug.gather_data()
            dataset_hunk_purposes.update(bug_hunk_purposes)
            dataset_added_line_purposes.update(bug_added_line_purposes)
            dataset_removed_line_purposes.update(bug_removed_line_purposes)
        return dataset_hunk_purposes, dataset_added_line_purposes, dataset_removed_line_purposes


@app.command()
def dataset(datasets: Annotated[
    List[Path],
    typer.Argument(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        writable=True,  # to save results
    )
]):
    """Gather data from all bugs in provided DATASETS

    Each DATASET is expected to be existing directory with the following
    structure:

        <dataset_directory>/<bug_directory>/patches/<patch_file>.diff.json

    Each DATASET can consist of many BUGs, each BUG should include patch
    of annotated *diff.json file in 'patches/' subdirectory.
    """
    for dataset in datasets:
        print(f"Dataset {dataset}")
        annotated_bugs = AnnotatedBugDataset(dataset)
        data = annotated_bugs.gather_data()
        print(data)


if __name__ == "__main__":
    app()

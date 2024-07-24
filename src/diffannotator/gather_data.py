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


class PurposeCounterResults:
    """Override this datastructure to gather results"""

    def __init__(self, processed_files, hunk_purposes, added_line_purposes, removed_line_purposes):
        self._processed_files = processed_files
        self._hunk_purposes = hunk_purposes
        self._added_line_purposes = added_line_purposes
        self._removed_line_purposes = removed_line_purposes

    def __add__(self, other):
        if isinstance(other, PurposeCounterResults):
            new_instance = PurposeCounterResults(
                self._processed_files + other._processed_files,
                self._hunk_purposes + other._hunk_purposes,
                self._added_line_purposes + other._added_line_purposes,
                self._removed_line_purposes + other._removed_line_purposes)
            return new_instance

    def __repr__(self):
        return f"PurposeCounterResults(_processed_files={self._processed_files!r}, _hunk_purposes={self._hunk_purposes!r}, _added_line_purposes={self._added_line_purposes!r}, _removed_line_purposes)={self._removed_line_purposes!r}"

    @staticmethod
    def default():
        """
        Constructs empty datastructure to work as 0 for addition via "+"

        :return: empty datastructure
        """
        return PurposeCounterResults([], Counter(), Counter(), Counter())

    @staticmethod
    def create(file_path, data):
        """
        Override this function for single annotation handling

        :param file_path: path to processed file
        :param data: dictionary with annotations (file content)
        :return: datastructure instance
        """
        hunk_purposes = Counter()
        added_line_purposes = Counter()
        removed_line_purposes = Counter()
        for hunk in data:
            # TODO: log info / debug
            #print(hunk)
            #print(data[hunk]['purpose'])
            hunk_purposes[data[hunk]['purpose']] += 1
            if '+' in data[hunk]:
                added_lines = data[hunk]['+']
                for added_line in added_lines:
                    added_line_purposes[added_line['purpose']] += 1
            if '-' in data[hunk]:
                removed_lines = data[hunk]['-']
                for removed_line in removed_lines:
                    removed_line_purposes[removed_line['purpose']] += 1
        return PurposeCounterResults([file_path], hunk_purposes, added_line_purposes, removed_line_purposes)


class AnnotatedFile:
    """Annotated single file in specific bug"""

    def __init__(self, file_path: PathLike):
        """Constructor of the annotated file of specific bug

        :param file_path: path to the single file
        """
        self._path = Path(file_path)

    def gather_data(self, bug_mapper):
        """
        Retrieves data from file

        :param bug_mapper: function to map bug to datastructure
        :return: resulting datastructure
        """
        with self._path.open('r') as json_file:
            data = json.load(json_file)
            return bug_mapper(str(self._path), data)


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

    def gather_data(self, bug_mapper, datastructure_generator):
        """
        Gathers dataset data via processing each file in current bug using AnnotatedFile class and provided functions

        :param bug_mapper: function to map bug to datastructure
        :param datastructure_generator: function to create empty datastructure to combine results via "+"
        :return: combined datastructure with all files data
        """
        combined_results = datastructure_generator()
        for annotation in self.annotations:
            if '...' in annotation:
                continue
            annotation_file_path = self._annotations_path / annotation
            annotation_file = AnnotatedFile(annotation_file_path)
            file_results = annotation_file.gather_data(bug_mapper)
            combined_results += file_results
        return combined_results


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

    def gather_data(self, bug_mapper, datastructure_generator):
        """
        Gathers dataset data via processing each bug using AnnotatedBug class and provided functions

        :param bug_mapper: function to map bug to datastructure
        :param datastructure_generator: function to create empty datastructure to combine results via "+"
        :return: combined datastructure with all bug data
        """
        combined_results = datastructure_generator()

        print(f"Gathering data from bugs/patches in '{self._path}' directory.")
        for bug_id in tqdm.tqdm(self.bugs):
            # TODO: log info / debug
            #print(bug_id)
            bug_path = self._path / bug_id
            bug = AnnotatedBug(bug_path)
            bug_results = bug.gather_data(bug_mapper, datastructure_generator)
            combined_results += bug_results

        return combined_results


@app.command()
def purpose_counter(datasets: Annotated[
    List[Path],
    typer.Argument(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        writable=False,
    )
]):
    """Calculate count of purposes from all bugs in provided datasets

    Each dataset is expected to be existing directory with the following
    structure:

        <dataset_directory>/<bug_directory>/annotation/<patch_file>.json

    Each dataset can consist of many BUGs, each BUG should include patch
    of annotated *diff.json file in 'annotation/' subdirectory.
    """
    for dataset in datasets:
        print(f"Dataset {dataset}")
        annotated_bugs = AnnotatedBugDataset(dataset)
        data = annotated_bugs.gather_data(PurposeCounterResults.create, PurposeCounterResults.default)
        print(data)


if __name__ == "__main__":
    app()

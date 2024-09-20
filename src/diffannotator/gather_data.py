#!/usr/bin/env python
import json
import os
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import List, TypeVar, Optional

import tqdm
import typer
from typing_extensions import Annotated

from .annotate import Bug


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
        return f"PurposeCounterResults(_processed_files={self._processed_files!r}, " \
               f"_hunk_purposes={self._hunk_purposes!r}, " \
               f"_added_line_purposes={self._added_line_purposes!r}, " \
               f"_removed_line_purposes)={self._removed_line_purposes!r})"

    def to_dict(self) -> dict:
        return {
            "processed_files": self._processed_files,
            "hunk_purposes": self._hunk_purposes,
            "added_line_purposes": self._added_line_purposes,
            "removed_line_purposes": self._removed_line_purposes,
        }

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

    def __init__(self, bug_dir: PathLike, annotations_dir: str = Bug.DEFAULT_ANNOTATIONS_DIR):
        """Constructor of the annotated bug

        :param bug_dir: path to the single bug
        """
        self._path = Path(bug_dir)
        self._annotations_path = self._path / annotations_dir

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

    def gather_data_dict(self, bug_dict_mapper):
        """
        Gathers dataset data via processing each file in current bug using AnnotatedFile class and provided functions

        :param bug_dict_mapper: function to map diff to dictionary
        :return: combined dictionary of all diffs
        """
        combined_results = {}
        for annotation in self.annotations:
            if '...' in annotation:
                continue
            annotation_file_path = self._annotations_path / annotation
            annotation_file = AnnotatedFile(annotation_file_path)
            diff_file_results = annotation_file.gather_data(bug_dict_mapper)
            combined_results |= {str(annotation): diff_file_results}
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

    def gather_data(self, bug_mapper, datastructure_generator,
                    annotations_dir: str = Bug.DEFAULT_ANNOTATIONS_DIR):
        """
        Gathers dataset data via processing each bug using AnnotatedBug class and provided functions

        :param bug_mapper: function to map bug to datastructure
        :param datastructure_generator: function to create empty datastructure to combine results via "+"
        :param annotations_dir: subdirectory where annotations are; path
            to annotation in a dataset is <bug_id>/<annotations_dir>/<patch_data>.json
        :return: combined datastructure with all bug data
        """
        combined_results = datastructure_generator()

        print(f"Gathering data from bugs/patches in '{self._path}' directory.")
        for bug_id in tqdm.tqdm(self.bugs, desc='bug'):
            # TODO: log info / debug
            #print(bug_id)
            bug_path = self._path / bug_id
            bug = AnnotatedBug(bug_path, annotations_dir=annotations_dir)
            bug_results = bug.gather_data(bug_mapper, datastructure_generator)
            combined_results += bug_results

        return combined_results

    def gather_data_dict(self, bug_dict_mapper,
                         annotations_dir: str = Bug.DEFAULT_ANNOTATIONS_DIR):
        """
        Gathers dataset data via processing each bug using AnnotatedBug class and provided function

        :param bug_dict_mapper: function to map diff to dictionary
        :param annotations_dir: subdirectory where annotations are; path
            to annotation in a dataset is <bug_id>/<annotations_dir>/<patch_data>.json
        :return: combined dictionary of all bugs
        """
        combined_results = {}
        for bug_id in tqdm.tqdm(self.bugs):
            print(bug_id)
            bug_path = self._path / bug_id
            bug = AnnotatedBug(bug_path, annotations_dir=annotations_dir)
            bug_results = bug.gather_data_dict(bug_dict_mapper)
            combined_results |= {bug_id: bug_results}
        return combined_results


def map_diff_to_purpose_dict(diff_file_path, data):
    """
    Example functon mapping diff of specific commit to dictionary

    :param diff_file_path: file path containing diff
    :param data: dictionary loaded from file
    :return: dictionary with file purposes
    """
    result = {}
    for hunk in data:
        print(hunk)
        print(data[hunk]['purpose'])
        if hunk not in result:
            result[hunk] = []
        result[hunk].append(data[hunk]['purpose'])
    return result


def save_result(result, result_json):
    print(f"Saving results to '{result_json}' JSON file")
    with result_json.open(mode='w') as result_f:
        json.dump(result, result_f, indent=4)


# implementing options common to all subcommands
# see https://jacobian.org/til/common-arguments-with-typer/
@app.callback()
def common(
    ctx: typer.Context,
    annotations_dir: Annotated[
        str,
        typer.Option(
            metavar="DIR_NAME",
            help="Subdirectory to read annotations from; use '' to do without such"
        )
    ] = Bug.DEFAULT_ANNOTATIONS_DIR,
):
    # if anything is printed by this function, it needs to utilize context
    # to not break installed shell completion for the command
    # see https://typer.tiangolo.com/tutorial/options/callback-and-context/#fix-completion-using-the-context
    if ctx.resilient_parsing:
        return

    # pass to subcommands via context
    ctx.obj = SimpleNamespace(
        annotations_dir=annotations_dir,
    )


@app.command()
def purpose_counter(
    ctx: typer.Context,
    datasets: Annotated[
        List[Path],
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=False
        )
    ],
    result_json: Annotated[
        Optional[Path],
        typer.Option(
            "--output", "-o",
            dir_okay=False,
            metavar="JSON_FILE",
            help="JSON file to write gathered results to",
        )
    ] = None,
):
    """Calculate count of purposes from all bugs in provided datasets

    Each dataset is expected to be existing directory with the following
    structure:

        <dataset_directory>/<bug_directory>/annotation/<patch_file>.json

    Each dataset can consist of many BUGs, each BUG should include patch
    of annotated *diff.json file in 'annotation/' subdirectory.
    """
    result = {}
    for dataset in datasets:
        print(f"Dataset {dataset}")
        annotated_bugs = AnnotatedBugDataset(dataset)
        data = annotated_bugs.gather_data(PurposeCounterResults.create,
                                          PurposeCounterResults.default,
                                          annotations_dir=ctx.obj.annotations_dir)
        result[dataset] = data

    if result_json is None:
        print(result)
    else:
        save_result({
                        str(key): value.to_dict()
                        for key, value in result.items()
                    },
                    result_json)


@app.command()
def purpose_per_file(
    ctx: typer.Context,
    result_json: Annotated[
        Path,
        typer.Argument(
            dir_okay=False,
            help="JSON file to write gathered results to"
        )
    ],
    datasets: Annotated[
        List[Path],
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=False,
            help="list of dirs with datasets to process"
        )
    ],
):
    """Calculate per-file count of purposes from all bugs in provided datasets

    Each dataset is expected to be existing directory with the following
    structure:

        <dataset_directory>/<bug_directory>/annotation/<patch_file>.json

    Each dataset can consist of many BUGs, each BUG should include patch
    of annotated *diff.json file in 'annotation/' subdirectory.
    """
    result = {}
    for dataset in datasets:
        print(f"Dataset {dataset}")
        annotated_bugs = AnnotatedBugDataset(dataset)
        data = annotated_bugs.gather_data_dict(map_diff_to_purpose_dict,
                                               annotations_dir=ctx.obj.annotations_dir)
        result[str(dataset)] = data

    print(result)
    save_result(result, result_json)


if __name__ == "__main__":
    app()

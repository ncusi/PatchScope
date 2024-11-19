import json
from pathlib import Path
from typing import Optional, Union

import panel as pn
import param

from diffinsights_web.utils.notifications import warning_notification

DATASET_DIR = 'data/examples/stats'


@pn.cache
def find_dataset_dir() -> Optional[Path]:
    for TOP_DIR in ['', '..', '../..']:
        full_dir = Path(TOP_DIR).joinpath(DATASET_DIR)

        if full_dir.is_dir():
            return full_dir

    return None


@pn.cache
def find_timeline_files(dataset_dir: Union[Path, str, param.Path, None]) -> dict[str, str]:
    if dataset_dir is None:
        warning_notification("No directory with data files to read")
        return {}

    else:
        # param.Path is not a pathlib.Path, but contains a string
        if isinstance(dataset_dir, param.Path):
            dataset_dir = dataset_dir.rx.value
            if dataset_dir is None:
                # TODO?: put this warning closer to the source, if possible:
                #        find_dataset_dir() returning None
                warning_notification("Did not find directory with data files to read")
                return {}

        # value extracted from param.Path is str, not pathlib.Path
        if not isinstance(dataset_dir, Path):
            dataset_dir = Path(dataset_dir)

        # assuming naming convention *.timeline.*.json for appropriate data files
        return {
            str(path.stem): str(path)
            for path in dataset_dir.glob('*.timeline.*.json')
        }


@pn.cache
def get_timeline_data(json_path: Optional[Path]) -> dict:
    if json_path is None:
        return {}

    with open(json_path, mode='r') as json_fp:
        return json.load(json_fp)


@pn.cache
def find_repos(timeline_data: dict) -> list[str]:
    return list(timeline_data.keys())


class TimelineDataStore(pn.viewable.Viewer):
    dataset_dir = param.Path(constant=True,
                             doc="Dataset directory with *.timeline.*.json files")

    def __init__(self, **params):
        super().__init__(**params)

        # select JSON data file
        select_file_widget = pn.widgets.Select(
            name="input JSON file",
            options=find_timeline_files(self.param.dataset_dir)
        )
        self.timeline_data_rx = pn.rx(get_timeline_data)(
            json_path=select_file_widget,
        )
        # select repo from selected JSON file
        self.find_repos_rx = pn.rx(find_repos)(
            timeline_data=self.timeline_data_rx,
        )
        select_repo_widget = pn.widgets.Select(
            name="repository",
            options=self.find_repos_rx,
            disabled=len(self.find_repos_rx.rx.value) <= 1,
        )

        self._widgets = [
            select_file_widget,
            select_repo_widget,
        ]

    def __panel__(self):
        return pn.WidgetBox(
            *self._widgets,
        )

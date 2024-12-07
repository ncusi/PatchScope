import json
from pathlib import Path
from typing import Union, Optional

import panel as pn
import param

from diffinsights_web.utils.notifications import warning_notification


def get_lines_stats_data(dataset_dir: str, timeseries_file: str) -> Optional[dict]:
    timeseries_file_path = Path(timeseries_file)
    if not timeseries_file_path.is_absolute():
        timeseries_file_path = Path(dataset_dir).joinpath(timeseries_file)

    dataset_dir = timeseries_file_path.parent
    lines_stats_file = timeseries_file_path.name.replace('.timeline.', '.lines-stats.')
    file_path = dataset_dir.joinpath(lines_stats_file)

    if file_path.is_file():
        with open(file_path, mode='r') as json_fp:
            return json.load(json_fp)
    else:
        return None


class LinesStatsDataStore(pn.viewable.Viewer):
    dataset_dir = param.Foldername(
        constant=True,
        doc="Dataset directory with *.lines-stats.*.json files "
            "(used if `timeseries_file_path` is relative path)",
    )
    timeseries_file = param.String(
        allow_refs=True,  # to allow widgets and reactive expressions
        doc="Selected JSON file with timeline data to find lines-stats companion for"
    )

    def __init__(self, **params):
        super().__init__(**params)

        self.lines_stats_data_rx = pn.rx(get_lines_stats_data)(
            dataset_dir=self.dataset_dir,
            timeseries_file=self.timeseries_file,
        )

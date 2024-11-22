import json
from pathlib import Path
from typing import Optional, Union

import panel as pn
import pandas as pd
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


@pn.cache
def get_timeline_df(timeline_data: dict, repo: str) -> pd.DataFrame:
    init_df = pd.DataFrame.from_records(timeline_data[repo])

    # no merges, no roots; add 'n_commits' column; drop rows with N/A for timestamps
    df = init_df[init_df['n_parents'] == 1]\
        .dropna(subset=['author.timestamp', 'committer.timestamp'], how='any')\
        .assign(
            n_commits =  1,
            author_date    = lambda x: pd.to_datetime(x['author.timestamp'],    unit='s', utc=True),
            committer_date = lambda x: pd.to_datetime(x['committer.timestamp'], unit='s', utc=True),
        )

    return df


def agg_func_mapping():
    columns_agg_sum = ['n_commits']
    agg_func_sum = {col: 'sum' for col in columns_agg_sum}

    agg_func = 'sum'
    columns_agg_any = ['+:count', '-:count', 'file_names', 'diff.patch_size', 'diff.groups_spread']
    agg_func_any = {col: agg_func for col in columns_agg_any}

    return agg_func_sum | agg_func_any


@pn.cache
def resample_timeline(timeline_df: pd.DataFrame,
                      resample_rate: str,
                      group_by: Optional[str] = None,
                      date_column: str = 'author_date') -> pd.DataFrame:
    # select appropriate aggregation function for specific columns
    agg_func_map = agg_func_mapping()

    # all columns to aggregate values of
    columns_agg = list(agg_func_map.keys())

    # aggregate over given period of time, i.e. resample
    if group_by is None:
        # resample only
        df_r = timeline_df.resample(
            resample_rate,
            on=date_column,
        )
    else:
        # group by and resample
        df_r = timeline_df.groupby([
            group_by,
            pd.Grouper(
                freq=resample_rate,
                key=date_column,
            )
        ])

    return df_r[columns_agg].agg(
        agg_func_map,
        numeric_only=True
    )


# mapping form display name to frequency alias
# see table in https://pandas.pydata.org/docs/user_guide/timeseries.html#dateoffset-objects
time_series_frequencies = {
    'calendar day frequency': 'D',
    'weekly frequency': 'W',
    'semi-month end frequency (15th and end of month)': 'SME',
    'month end frequency': 'ME',
    'quarter end frequency': 'QE',
}
# mapping from alias to display stem
frequency_names = {
    'D': 'day',
    'W': 'week',
    'SME': 'semi-month',
    'ME': 'month',
    'QE': 'quarter',
}


class TimelineDataStore(pn.viewable.Viewer):
    dataset_dir = param.Foldername(
        constant=True,
        doc="Dataset directory with *.timeline.*.json files",
    )
    group_by = param.Selector(
        default='author.email',
        objects=[
            'author.email',
            'committer.email',
        ],
        constant=True,  # can be set only in the constructor (without overrides)
    )

    def __init__(self, **params):
        super().__init__(**params)

        # select JSON data file, and extract data from it
        self.select_file_widget = pn.widgets.Select(
            name="input JSON file",
            options=find_timeline_files(self.param.dataset_dir)
        )
        self.timeline_data_rx = pn.rx(get_timeline_data)(
            json_path=self.select_file_widget,
        )
        # select repo from selected JSON file
        self.find_repos_rx = pn.rx(find_repos)(
            timeline_data=self.timeline_data_rx,
        )
        self.select_repo_widget = pn.widgets.Select(
            name="repository",
            options=self.find_repos_rx,
            disabled=len(self.find_repos_rx.rx.value) <= 1,
        )
        # convert extracted data to pd.DataFrame
        self.timeline_df_rx = pn.rx(get_timeline_df)(
            timeline_data=self.timeline_data_rx,
            repo=self.select_repo_widget,
        )
        # select resample frequency, and resample+groupby
        self.resample_frequency_widget = pn.widgets.Select(
            name="frequency",
            value='W',
            options=time_series_frequencies,
            sizing_mode="stretch_width",
        )
        self.resampled_timeline_all_rx = pn.rx(resample_timeline)(
            timeline_df=self.timeline_df_rx,
            resample_rate=self.resample_frequency_widget,
        )
        self.resampled_timeline_by_author_rx = pn.rx(resample_timeline)(
            timeline_df=self.timeline_df_rx,
            resample_rate=self.resample_frequency_widget,
            group_by=self.group_by,
        )

        self._widgets = [
            self.select_file_widget,
            self.select_repo_widget,
            self.resample_frequency_widget,
        ]

    @param.output(param.DataFrame)
    def timeline_data(self):
        return self.timeline_data_rx

    def __panel__(self):
        return pn.WidgetBox(
            *self._widgets,
        )

import json
import datetime
from pathlib import Path
from typing import Optional, Union

import panel as pn
import pandas as pd
import param

from diffinsights_web.utils.notifications import warning_notification


# global variables:
read_cached_df: bool = True  #: whether to use cached DataFrames if available
save_cached_df: bool = True  #: whether to save DataFrames as *.feather files


def path_to_name(file_path: Union[Path, str]) -> str:
    # handle the case where file_path is str, e.g. is widget value
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    basename = str(file_path.stem)
    try:
        # everything up to first '.', if present
        # this should be the typical case
        return basename[0:basename.index('.')]
    except ValueError:
        # otherwise return whole basename
        return basename


#@pn.cache
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
            path_to_name(path): str(path)
            for path in dataset_dir.glob('*.timeline.*.json')
        }


#@pn.cache
def get_timeline_data(json_path: Optional[Path]) -> dict:
    if json_path is None:
        return {}

    # NOTE: json_path can be 'str', not 'Path'
    if not isinstance(json_path, Path):
        json_path = Path(json_path)
    if read_cached_df and json_path.with_suffix('.feather').is_file():
        # assume only one repo, with name given by first part of JSON file pathname
        # TODO: implement better handling than this special case
        #print(f"get_timeline_data({json_path=}) -> found .feather cache")
        return { json_path.stem.split(sep='.', maxsplit=1)[0]: None }

    with open(json_path, mode='r') as json_fp:
        return json.load(json_fp)


#@pn.cache
def find_repos(timeline_data: dict) -> list[str]:
    return list(timeline_data.keys())


#@pn.cache
def get_timeline_df(json_path: Optional[Path], timeline_data: dict, repo: str) -> pd.DataFrame:
    """Create timeline DataFrame from timeline data in JSON file

    If global variable `read_cached_df` is True, and *.feather file with cached
    data exists, read DataFrame from that file.  If global variable `save_cached_df`
    is True, and *.feather file with cached data does not exist, save DataFrame
    to that file.

    :param json_path: used to find cached data, if present, and possibly
        for error and debug messages (when logging)
    :param timeline_data: per-repo data to convert to pd.DataFrame and process;
        usually there is only a single repo (single key) in `timeline_data` dict
    :param repo: data from which repo to extract from `timeline_data`
    :return: augmented dataframe, for example with 'n_commits' column added
    """
    if json_path is not None:
        # NOTE: json_path can be 'str', not 'Path'
        cache_file = Path(json_path).with_suffix('.feather')
        if read_cached_df and cache_file.is_file():
            # read cached data
            try:
                #print(f"get_timeline_df({json_path=}, {timeline_data=}, {repo=}) -> read .feather cache")
                return pd.read_feather(cache_file)
            except ModuleNotFoundError:
                # No module named 'pyarrow'
                # TODO: log warning for this problem
                print("get_timeline_df -> ModuleNotFoundError")
                pass

    # TODO: remove after test_app_contributors_performance.py gets fixed
    try:
        init_df = pd.DataFrame.from_records(timeline_data[repo])
    except KeyError:
        # workaround: use first (and oftentimes only) repo
        init_df = pd.DataFrame.from_records(timeline_data[next(iter(timeline_data))])

    # no merges, no roots; add 'n_commits' column; drop rows with N/A for timestamps
    df = init_df[init_df['n_parents'] == 1]\
        .dropna(subset=['author.timestamp', 'committer.timestamp'], how='any')\
        .assign(
            n_commits =  1,
            author_date    = lambda x: pd.to_datetime(x['author.timestamp'],    unit='s', utc=True),
            committer_date = lambda x: pd.to_datetime(x['committer.timestamp'], unit='s', utc=True),
        )

    if save_cached_df and json_path is not None:
        # TODO: add logging
        cache_file = Path(json_path).with_suffix('.feather')
        # TODO: check if json_path is newer
        if not cache_file.is_file():
            df.to_feather(cache_file)

    return df


def agg_func_mapping(pm_count_cols: Optional[list[str]] = None) -> dict[str, str]:
    if pm_count_cols is None:
        pm_count_cols = ['+:count', '-:count']

    # there is always one commit per commit; 'n_commits' is always 1 in timeline_df
    # so any other aggregation function than 'sum' does not make sense for 'n_commits' column
    columns_agg_sum = ['n_commits']
    agg_func_sum = {col: 'sum' for col in columns_agg_sum}

    agg_func = 'sum'  # TODO: make it a parameter to this function, and make it selectable
    columns_agg_any = ['file_names', *pm_count_cols, 'diff.patch_size', 'diff.groups_spread']
    agg_func_any = {col: agg_func for col in columns_agg_any}

    return agg_func_sum | agg_func_any


#@pn.cache
def get_pm_count_cols(timeline_df: pd.DataFrame) -> list[str]:
    ## DEBUG
    # TODO: replace with logging
    #print(f"RUNNING get_pm_count_cols(timeline_df={type(timeline_df)}(<{hex(id(timeline_df))}>))")
    #print(f"  {timeline_df.columns=}")
    # for every '-:column' there should be '+:column'
    pm_count_cols_set = {
        col[2:] for col in timeline_df.columns
        if col.startswith('+:') or col.startswith('-:')
    }
    #print(f"  {pm_count_cols_set=}")
    pm_count_cols = [
        col
        for col_base in pm_count_cols_set
        if col_base.startswith('type.') or col_base == 'count'  # only types of lines
        for col in [f"-:{col_base}", f"+:{col_base}"]
    ]
    #print(f"  {pm_count_cols=}")
    return pm_count_cols


# @pn.cache
def add_pm_count_perc(resampled_df: pd.DataFrame,
                      pm_count_cols: list[str]) -> pd.DataFrame:
    ## DEBUG
    # TODO: replace with logging
    #print(f"RUNNING add_pm_count_perc(resampled_df=DataFrame(<{hex(id(resampled_df))}>, "
    #      f"pm_count_cols=[{', '.join(pm_count_cols[:6])},...])")
    #print(f"  {resampled_df.columns=}")
    for col in pm_count_cols:
        if col in {'-:count', '+:count'}:  # '-:count' or '+:count'
            continue

        if col not in resampled_df:
            #print(f"  ZERO {col}")
            resampled_df.loc[:, col] = 0

        col_perc = f"{col} [%]"
        if col_perc in resampled_df.columns:
            #print(f"  SKIP {col_perc}")
            continue

        if col.startswith('+:'):
            resampled_df.loc[:, col_perc] = resampled_df[col] / resampled_df['+:count']
        elif col.startswith('-:'):
            resampled_df.loc[:, col_perc] = resampled_df[col] / resampled_df['-:count']

    for col in pm_count_cols:
        if col in {'-:count', '+:count'}:  # '-:count' or '+:count'
            continue

        # previous loop ensured that both "-:<column>" and "+:<column>" exists
        if col.startswith('-:'):  # we need only one of those
            continue

        col_base = col[2:]  # remove "+:" prefix
        col_base_perc = f"{col_base} [%]"
        if col_base_perc in resampled_df.columns:
            # print(f"  SKIP {col_base_perc}")
            continue

        resampled_df.loc[:, col_base_perc] = (
                (resampled_df[f"-:{col_base}"] + resampled_df[f"+:{col_base}"]) /
                (resampled_df['-:count'] + resampled_df['+:count'])
        )

    #print(f"  returned DataFrame(<{hex(id(resampled_df))}>)")
    return resampled_df


#@pn.cache
def resample_timeline(timeline_df: pd.DataFrame,
                      resample_rate: str,
                      group_by: Optional[str] = None,
                      date_column: str = 'author_date',
                      pm_count_cols: Optional[list[str]] = None) -> pd.DataFrame:
    # select appropriate aggregation function for specific columns
    agg_func_map = agg_func_mapping(pm_count_cols)

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

    df_agg = df_r[columns_agg].agg(
        agg_func_map,
        numeric_only=True
    )
    # add [%] columns to resampled timelines
    return add_pm_count_perc(df_agg, pm_count_cols)


def author_timeline_df(resample_by_author_df: pd.DataFrame, author_id: str) -> pd.DataFrame:
    # WORKAROUND
    if author_id not in resample_by_author_df.index:
        print(f"WARNING: author_timeline_df(): {author_id=}"
              f" not in resample_by_author_df=<{hex(id(resample_by_author_df))}> index")
        author_id = resample_by_author_df.index[0][0]  # this dataframe has multiindex
        print(f"         using {author_id=} instead")

    return resample_by_author_df.loc[author_id]


def author_timeline_df_freq(resample_by_author_df: pd.DataFrame,
                            author_id: str,
                            resample_rate: str) -> pd.DataFrame:
    # WORKAROUND
    if author_id not in resample_by_author_df.index:
        print(f"WARNING: author_timeline_df_freq(): {author_id=}"
              f" not in resample_by_author_df=<{hex(id(resample_by_author_df))}> index")
        author_id = resample_by_author_df.index[0][0]  # this dataframe has multiindex
        print(f"         using {author_id=} instead")

    # NOTE: instead of .asfreq(<freq>) one can use .resample(<freq>).first() instead
    return resample_by_author_df.loc[author_id].asfreq(resample_rate).fillna(0)


#@pn.cache
def get_max_date(timeline_df: pd.DataFrame) -> datetime.datetime:
    return timeline_df['author_date'].max().to_pydatetime()


#@pn.cache
def get_date_range(timeline_df: pd.DataFrame, from_date_str: str):
    # TODO: create reactive component or bound function to compute from_date to avoid recalculations
    # TODO: use parsed `from_date` instead of using raw `from_date_str`
    min_date = timeline_df['author_date'].min()
    if from_date_str:
        # the `from_date_str` is in YYYY.MM.DD format
        from_date = pd.to_datetime(from_date_str, yearfirst=True, utc=True)
        min_date = max(min_date, from_date)

    ## DEBUG
    #print(f"get_date_range(timeline_df=<{hex(id(timeline_df))}, {from_date_str=}>):")
    #print(f"  {min_date=}, {timeline_df['author_date'].max()=}")

    return (
        min_date,
        timeline_df['author_date'].max(),
    )


#@pn.cache
def get_value_range(timeline_df: pd.DataFrame, column: str = 'n_commits'):
    # problems importing SpecialColumnsEnum - circular dependency
    # therefore use more generic solution: protect against all key errors
    if column not in timeline_df.columns:
        return 0.0, 1.0

    return (
        timeline_df[column].min(),
        timeline_df[column].max(),
    )


# NOTE: consider putting the filter earlier in the pipeline (needs profiling / benchmarking?)
# TODO: replace `from_date_str` (raw string) with `from_date` (parsed value)
def filter_df_by_from_date(resampled_df: pd.DataFrame,
                           from_date_str: str,
                           date_column: Optional[str] = None) -> pd.DataFrame:
    from_date: Optional[pd.Timestamp] = None
    if from_date_str:
        try:
            # the `from_date_str` is in YYYY.MM.DD format
            # TODO: refactor to remove code duplication (if not using `from_date` as argument)
            from_date = pd.to_datetime(from_date_str, yearfirst=True, utc=True)
        except ValueError as err:
            # NOTE: should not happen, value should be validated earlier
            warning_notification(f"from={from_date_str!r} is not a valid date: {err}")

    filtered_df = resampled_df
    if from_date is not None:
        if date_column is None:
            filtered_df = resampled_df[resampled_df.index >= from_date]
        else:
            if pd.api.types.is_timedelta64_dtype(resampled_df[date_column]):
                filtered_df = resampled_df[resampled_df[date_column] >= from_date]
            elif pd.api.types.is_numeric_dtype(resampled_df[date_column]):
                # assume numeric date column is UNIX timestamp
                filtered_df = resampled_df[resampled_df[date_column] >= from_date.timestamp()]
            else:
                warning_notification(f"unsupported type {resampled_df.dtypes[date_column]!r} "
                                     f"for column {date_column!r}")

    if len(filtered_df) == 0 and date_column is None:  # second part: run only once (or twice)
        warning_notification(f"cutoff of {from_date} leads to an empty result")

    return filtered_df


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


def authors_info_df(timeline_df: pd.DataFrame,
                    column: str = 'n_commits',
                    from_date_str: str = '') -> pd.DataFrame:
    info_columns = list(agg_func_mapping().keys())

    # sanity check
    if column not in info_columns:
        column = info_columns[0]

    filtered_df = filter_df_by_from_date(timeline_df, from_date_str,
                                         date_column='author.timestamp')

    df = filtered_df\
        .groupby(by='author.email')[info_columns + ['author.name']]\
        .agg({
            col: 'sum' for col in info_columns
        } | {
            # https://stackoverflow.com/questions/15222754/groupby-pandas-dataframe-and-select-most-common-value
            'author.name': pd.Series.mode,
        })\
        .sort_values(by=column, ascending=False)\
        .rename(columns={
            '+:count': 'p_count',
            '-:count': 'm_count',
            'author.name': 'author_name',
        })

    #print(f" -> {df.columns=}, {df.index.name=}")
    return df


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
            #name="input JSON file",
            name="repository data",  # NOTE: this name is easier to understand, even if less correct
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
            #name="repository",
            name="name of data subset",  # NOTE: in all examples there is only one subset
            options=self.find_repos_rx,
            value=self.find_repos_rx[0],
            disabled=self.find_repos_rx.rx.pipe(len) <= 1,
        )
        # convert extracted data to pd.DataFrame
        self.timeline_df_rx = pn.rx(get_timeline_df)(
            json_path=self.select_file_widget,
            timeline_data=self.timeline_data_rx,
            repo=self.select_repo_widget,
        )
        # find maximum date
        self.timeline_max_date_rx = pn.rx(get_max_date)(
            timeline_df=self.timeline_df_rx,
        )


        # select which extra columns to aggregate over (preserve in resampled dataframe)
        # all datasets should have the same set of columns, so no need to have this reactive
        # NOTE: reactive expression doesn't play well with set(), hence passing .rx.value
        self.pm_count_cols = get_pm_count_cols(self.timeline_df_rx.rx.value)

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
            pm_count_cols=self.pm_count_cols,
        )
        self.resampled_timeline_by_author_rx = pn.rx(resample_timeline)(
            timeline_df=self.timeline_df_rx,
            resample_rate=self.resample_frequency_widget,
            group_by=self.param.group_by.rx(),
            pm_count_cols=self.pm_count_cols,
        )

        ## DEBUG
        # TODO: replace with logging
        #print(f"  timeline_df                  -> <{hex(id(self.timeline_df_rx.rx.value))}>, "
        #      f"rx -> <{hex(id(self.timeline_df_rx))}>")
        #print(f"  resampled_timeline_all       -> <{hex(id(self.resampled_timeline_all_rx.rx.value))}>, "
        #      f"rx -> <{hex(id(self.resampled_timeline_all_rx))}>")
        #print(f"  resampled_timeline_by_author -> <{hex(id(self.resampled_timeline_by_author_rx.rx.value))}>, "
        #      f"rx -> <{hex(id(self.resampled_timeline_by_author_rx))}>")

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

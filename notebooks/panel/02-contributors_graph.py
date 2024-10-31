import datetime
import json
import logging
from pathlib import Path
from typing import Optional

# data analysis
import numpy as np
import pandas as pd

# dashboard
import panel as pn

# plotting
import hvplot.pandas  # noqa


logger = logging.getLogger("panel.contributors_graph")
pn.extension("jsoneditor",
             design="material", sizing_mode="stretch_width")

DATASET_DIR = 'data/examples/stats'


def find_dataset_dir() -> Optional[Path]:
    for TOP_DIR in ['', '..', '../..']:
        #print(f"find_dataset_dir(): {TOP_DIR}")
        full_dir = Path(TOP_DIR).joinpath(DATASET_DIR)

        if full_dir.is_dir():
            #print(f"find_dataset_dir(): found {full_dir}")
            return full_dir

    return None


def find_timeline_files(dataset_dir: Optional[Path]) -> list[Path]:
    if dataset_dir is None:
        #print(f"find_timeline_files({dataset_dir=}): []")
        return []
    else:
        # assuming naming convention for file names
        #print(f"find_timeline_files({dataset_dir=}): searching...")
        res = {
            str(path.stem): str(path) 
            for path in dataset_dir.glob('*.timeline.*.json')
        }
        #print(f" -> {res}")
        return res


@pn.cache
def get_timeline_data(json_path: Path) -> dict:
    logger.debug(f"[@pn.cache] get_timeline_data() for {json_path=}")
    with open(json_path, mode='r') as json_fp:
        return json.load(json_fp)


def find_repos(timeline_data: dict):
    return list(timeline_data.keys())


@pn.cache
def get_timeline_df(timeline_data: dict, repo: str) -> pd.DataFrame:
    init_df = pd.DataFrame.from_records(timeline_data[repo])
    # no merges, no roots; add 'n_commits' column; drop rows with N/A for timestamps
    return init_df[init_df['n_parents'] == 1]\
        .dropna(subset=['author.timestamp', 'committer.timestamp'], how='any')\
        .assign(
            n_commits =  1,
            author_date = lambda x: pd.to_datetime(x['author.timestamp'], unit='s', utc=True),
            committer_date = lambda x: pd.to_datetime(x['committer.timestamp'], unit='s', utc=True),
        )#\
        #.rename(columns={
        #    'author_date': 'author.date',
        #    'committer_date': 'committer.date',
        #})


#@pn.cache
def resample_timeline_all(timeline_df: pd.DataFrame, resample_rate: str) -> pd.DataFrame:
    df = timeline_df.resample(
        resample_rate,
        on='author_date'
    ).agg(
        'sum',
        numeric_only=True
    )

    # to be possibly used for xlabel when plotting
    #df['author.date(UTC)'] = df.index
    #df['author.date(Y-m)'] = df.index.strftime('%Y-%m')

    return df


#@pn.cache
def get_date_range(timeline_df: pd.DataFrame):
    return (
        timeline_df['author_date'].min(),
        timeline_df['author_date'].max(),
    )


#@pn.cache
def head_info(repo: str, resample: str, frequency_names: dict[str, str]) -> str:
    return f"""
    <h1>Contributors to {repo}</h1>
    <p>Contributions per {frequency_names.get(resample, 'unknown frequency')} to HEAD, excluding merge commits</p>
    """

def sampling_info(resample: str, frequency_names: dict[str, str], min_max_date) -> str:
    return f"""
    **Commits over time**
    
    {frequency_names.get(resample, 'unknown frequency').title()}ly from {min_max_date[0].strftime('%-d %a %Y')} to {min_max_date[1].strftime('%-d %a %Y')}
    """


def plot_commits(resampled_df: pd.DataFrame):
    return resampled_df.hvplot.step(
        x='author_date', y='n_commits',
        color='blue',
        responsive=True,
    )


# mapping form display name to alias
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


select_file_widget = pn.widgets.Select(name="input JSON file", options=find_timeline_files(find_dataset_dir()))

get_timeline_data_rx = pn.rx(get_timeline_data)(
    json_path=select_file_widget,
)
find_repos_rx = pn.rx(find_repos)(
    timeline_data=get_timeline_data_rx,
)
select_repo_widget = pn.widgets.Select(name="repository", options=find_repos_rx, disabled=len(find_repos_rx.rx.value) <= 1)

resample_frequency_widget = pn.widgets.Select(name="frequency", value='W', options=time_series_frequencies)

head_styles = {
    'font-size': 'larger',
}
head_text_rx = pn.rx(head_info)(
    repo=select_repo_widget,
    resample=resample_frequency_widget,
    frequency_names=frequency_names,
)

get_timeline_df_rx = pn.rx(get_timeline_df)(
    timeline_data=get_timeline_data_rx,
    repo=select_repo_widget,
)
get_date_range_rx = pn.rx(get_date_range)(
    timeline_df=get_timeline_df_rx,
)
sampling_info_rx = pn.rx(sampling_info)(
    resample=resample_frequency_widget,
    frequency_names=frequency_names,
    min_max_date=get_date_range_rx,
)

resample_timeline_all_rx = pn.rx(resample_timeline_all)(
    timeline_df=get_timeline_df_rx,
    resample_rate=resample_frequency_widget,
)

plot_commits_rx = pn.rx(plot_commits)(
    resampled_df=resample_timeline_all_rx,
)

#if pn.state.location:
#    pn.state.location.sync(select_file_widget, {'value': 'file'})
#    pn.state.location.sync(select_repo_widget, {'value': 'repo'})

template = pn.template.MaterialTemplate(
    site="diffannotator",
    title="Contributors Graph",  # TODO: make title dynamic
    sidebar_width=350,
    sidebar=[
        select_file_widget,
        select_repo_widget,
        resample_frequency_widget,
    ],
    main=[
        pn.Column(
            pn.pane.HTML(head_text_rx, styles=head_styles),
            pn.Card(
                pn.Column(
                    pn.pane.Markdown(sampling_info_rx, styles=head_styles),
                    pn.pane.HoloViews(plot_commits_rx),
                ),
                collapsible=False, hide_header=True,
            )
        )
    ]
)
template.servable()

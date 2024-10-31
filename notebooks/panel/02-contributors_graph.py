import datetime
import json
import logging
from pathlib import Path
from typing import Optional

from dateutil.relativedelta import relativedelta

# data analysis
#import numpy as np
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


def find_timeline_files(dataset_dir: Optional[Path]) -> dict[str, str]:
    if dataset_dir is None:
        #print(f"find_timeline_files({dataset_dir=}): []")
        return {}
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


def find_repos(timeline_data: dict) -> list[str]:
    return list(timeline_data.keys())


@pn.cache
def get_timeline_df(timeline_data: dict, repo: str) -> pd.DataFrame:
    init_df = pd.DataFrame.from_records(timeline_data[repo])
    # no merges, no roots; add 'n_commits' column; drop rows with N/A for timestamps
    return init_df[init_df['n_parents'] == 1]\
        .dropna(subset=['author.timestamp', 'committer.timestamp'], how='any')\
        .assign(
            n_commits =  1,
            author_date    = lambda x: pd.to_datetime(x['author.timestamp'],    unit='s', utc=True),
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
def head_info(repo: str, resample: str, frequency: dict[str, str]) -> str:
    return f"""
    <h1>Contributors to {repo}</h1>
    <p>Contributions per {frequency.get(resample, 'unknown frequency')} to HEAD, excluding merge commits</p>
    """


def sampling_info(resample: str, frequency: dict[str, str], min_max_date) -> str:
    return f"""
    **Commits over time**

    {frequency.get(resample, 'unknown frequency').title()}ly from {min_max_date[0].strftime('%d %a %Y')} to {min_max_date[1].strftime('%d %a %Y')}
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

time_range_period = {
    'All': None,
    'Last month': 1,
    'Last 3 months': 3,
    'Last 6 months': 6,
    'Last 12 months': 12,
    'Last 24 months': 24,
}


def time_range_options(period_name_to_months: dict[str, Optional[int]]) -> dict[str, str]:
    today = datetime.date.today()
    #print(f"time_range_options(): {today=}")
    return {
        k: '' if v is None else (today + relativedelta(months=-v)).strftime('%d.%m.%Y')
        for k, v in period_name_to_months.items()
    }


def handle_custom_range(widget: pn.widgets.select.SingleSelectBase,
                        value: Optional[str], na_str: str = 'Custom range') -> None:
    if value is None or value in widget.options.values():
        if na_str in widget.options:
            del widget.options[na_str]
            #print(f"after del {widget.options=}")

        #print(f"no changes {widget.options=}")
        return

    widget.options[na_str] = value
    widget.value = value
    #print(f"after add {widget.options=}")
    widget.param.trigger('options')
    #widget.param.trigger('value')
    #widget.disabled_options = [value]


# sidebar widgets
select_file_widget = pn.widgets.Select(name="input JSON file", options=find_timeline_files(find_dataset_dir()))

get_timeline_data_rx = pn.rx(get_timeline_data)(
    json_path=select_file_widget,
)
find_repos_rx = pn.rx(find_repos)(
    timeline_data=get_timeline_data_rx,
)
select_repo_widget = pn.widgets.Select(name="repository", options=find_repos_rx, disabled=len(find_repos_rx.rx.value) <= 1)

resample_frequency_widget = pn.widgets.Select(name="frequency", value='W', options=time_series_frequencies)

# main contents widgets
select_period_from_widget = pn.widgets.Select(
    name="Period:",
    options={'Any': None},
    value='Any',
    # style
    width=300,
)
select_period_from_widget.options = time_range_options(time_range_period)
select_period_from_widget.value = None
#print(f"{select_period_from_widget.options=}")


def select_period_from_widget__onload() -> None:
    if pn.state.location:
        #print(f"{pn.state.session_args.get('from')[0].decode()}")
        select_period_from_widget.in_onload = True
        handle_custom_range(
            widget=select_period_from_widget,
            value=pn.state.session_args.get('from')[0].decode(),
        )
        select_period_from_widget.in_onload = False


def select_period_from_widget__callback(*events) -> None:
    #print(f"select_period_from_widget__callback({events=}):")
    na_str = 'Custom range'

    for event in events:
        # value of attribute 'value' change
        if event.what == 'value' and event.name == 'value':
            #print(f"=> {getattr(select_period_from_widget, 'in_onload', False)=} -> {na_str in select_period_from_widget.options}")
            if not getattr(select_period_from_widget, 'in_onload', False):
                #print(f"=> non in onload")
                if na_str in select_period_from_widget.options:
                    del select_period_from_widget.options[na_str]
                    select_period_from_widget.param.trigger('options')
                    #print(f"-> after del[{na_str!r}]: {select_period_from_widget.options=}")


select_period_from_widget.param.watch(select_period_from_widget__callback, ['value'], onlychanged=True)

# main contents
head_styles = {
    'font-size': 'larger',
}
head_text_rx = pn.rx(head_info)(
    repo=select_repo_widget,
    resample=resample_frequency_widget,
    frequency=frequency_names,
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
    frequency=frequency_names,
    min_max_date=get_date_range_rx,
)

resample_timeline_all_rx = pn.rx(resample_timeline_all)(
    timeline_df=get_timeline_df_rx,
    resample_rate=resample_frequency_widget,
)

plot_commits_rx = pn.rx(plot_commits)(
    resampled_df=resample_timeline_all_rx,
)

if pn.state.location:
#    pn.state.location.sync(select_file_widget, {'value': 'file'})
#    pn.state.location.sync(select_repo_widget, {'value': 'repo'})
    pn.state.location.sync(resample_frequency_widget, {'value': 'resample'})
    pn.state.location.sync(select_period_from_widget, {'value': 'from'})

pn.state.onload(select_period_from_widget__onload)

# GitHub: ..., line counts have been omitted because commit count exceeds 10,000.
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
            pn.Row(
                pn.pane.HTML(head_text_rx, styles=head_styles),
                select_period_from_widget,
            ),
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

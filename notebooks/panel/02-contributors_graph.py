import datetime
import json
import logging
import os
import re
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
pn.extension(
    "jsoneditor",
    notifications=True,
    design="material", sizing_mode="stretch_width"
)
pn.state.notifications.position = 'top-center'
loaded = False

# TODO: replace with a better mechanism, e.g. Proxy object for pn.state.notifications
warnings: list[str] = []


def warning_notification(msg: str) -> None:
    if loaded:
        #print(f"immediate warning: {msg}")
        pn.state.notifications.warning(msg)
    else:
        #print(f"postponed warning: {msg}")
        warnings.append(msg)


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


#@pn.cache
def get_timeline_data(json_path: Optional[Path]) -> dict:
    logger.debug(f"[@pn.cache] get_timeline_data({json_path=})")

    if json_path is None:
        return {
            'demo repo': [
                {
                    "bug_id": "demo data",
                    "patch_id": "000000000",
                    "author.timestamp":    1302557067,
                    "committer.timestamp": 1302558888,
                    "n_parents": 1,
                },
                {
                    "bug_id": "demo data",
                    "patch_id": "000000001",
                    "author.timestamp":     1391253300,
                    "committer.timestamp":  1391253900,
                    "n_parents": 1,
                },
                {
                    "bug_id": "demo data",
                    "patch_id": "000000002",
                    "author.timestamp":    1445339935,
                    "committer.timestamp": 1446061018,
                    "n_parents": 1,
                },
                {
                    "bug_id": "demo data",
                    "patch_id": "000000003",
                    "author.timestamp":    1445339935 + 24*60*60,
                    "committer.timestamp": 1446061018 + 25*60*60,
                    "n_parents": 1,
                }
            ]
        }
    with open(json_path, mode='r') as json_fp:
        return json.load(json_fp)


def find_repos(timeline_data: dict) -> list[str]:
    return list(timeline_data.keys())


#@pn.cache
def get_timeline_df(timeline_data: dict, repo: str) -> pd.DataFrame:
    #print(f"get_timeline_df({len(timeline_data)=}, {repo=})")
    #print(f"{timeline_data=}")
    init_df = pd.DataFrame.from_records(timeline_data[repo])
    #print(init_df)
    # no merges, no roots; add 'n_commits' column; drop rows with N/A for timestamps
    df = init_df[init_df['n_parents'] == 1]\
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

    #print(f"  -> df={hex(id(df))}, {df.shape=}")
    return df


def authors_info_df(timeline_df: pd.DataFrame,
                    column: str = 'n_commits',
                    from_date_str: str = '') -> pd.DataFrame:
    info_columns = ['n_commits', '+:count', '-:count']

    # sanity check
    if column not in info_columns:
        column = info_columns[0]

    filtered_df = filter_df_by_from_date(timeline_df, from_date_str, 'author.timestamp')

    df = filtered_df\
        .groupby(by='author.email')[info_columns]\
        .agg('sum')\
        .sort_values(by=column, ascending=False)\
        .rename(columns={
            '+:count': 'p_count',
            '-:count': 'm_count',
        })

    #print(df)
    return df


#@pn.cache
def resample_timeline_all(timeline_df: pd.DataFrame, resample_rate: str) -> pd.DataFrame:
    #print(f"resample_timeline_all(timeline_df={hex(id(timeline_df))}, {resample_rate=})")
    # some columns need specific aggregation function
    columns_agg_sum = ['n_commits']
    agg_func_sum = {col: 'sum' for col in columns_agg_sum}

    agg_func = 'sum'
    columns_agg_any = ['+:count', '-:count']
    agg_func_any = {col: agg_func for col in columns_agg_any}

    # all columns to aggregate values of
    columns_agg = [*columns_agg_sum, *columns_agg_any]

    # aggregate over given period of time, i.e. resample
    df = timeline_df.resample(
        resample_rate,
        on='author_date'
    )[columns_agg].agg(
        agg_func_sum | agg_func_any,
        numeric_only=True
    )

    # to be possibly used for xlabel when plotting
    #df['author.date(UTC)'] = df.index
    #df['author.date(Y-m)'] = df.index.strftime('%Y-%m')
    #print(df)

    #print(f"  -> df={hex(id(df))}, {df.shape=}")
    return df


# NOTE: consider putting the filter earlier in the pipeline (needs profiling / benchmarking?)
def filter_df_by_from_date(resampled_df: pd.DataFrame,
                           from_date_str: str,
                           date_column: Optional[str] = None) -> pd.DataFrame:
    from_date: Optional[pd.Timestamp] = None
    if from_date_str:
        try:
            # the `from_date_str` is in DD.MM.YYYY format
            from_date = pd.to_datetime(from_date_str, dayfirst=True, utc=True)
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

    return filtered_df


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


def html_date_humane(date: pd.Timestamp) -> str:
    date_format = '%d %a %Y'
    if os.name == 'nt':
        date_format = '%#d %a %Y'
    elif os.name == 'posix':
        date_format = '%-d %a %Y'

    return f'<time datetime="{date.isoformat()}">{date.strftime(date_format)}</time>'


def sampling_info(resample: str, column: str, frequency: dict[str, str], min_max_date) -> str:
    contribution_type = column_to_contribution.get(column, "Unknown type of contribution")

    return f"""
    <strong>{contribution_type} over time</strong>
    <p>
    {frequency.get(resample, 'unknown frequency').title()}ly
    from {html_date_humane(min_max_date[0])}
    to {html_date_humane(min_max_date[1])}
    </p>
    """


def plot_commits(resampled_df: pd.DataFrame,
                 column: str = 'n_commits',
                 from_date_str: str = '',
                 kind: str = 'step', autorange: bool = True):
    #print(f"plot_commits(resampled_df={hex(id(resampled_df))}, {columns=}, {from_date_str=}, {kind=}, {autorange=})")
    #print(f"   {resampled_df.shape=}")
    filtered_df = filter_df_by_from_date(resampled_df, from_date_str)

    hvplot_kwargs = {}
    if kind == 'step':
        hvplot_kwargs.update({
            'where': 'mid',  # 'pre' is correct, but we need to adjust xlim
        })
    if kind in {'step', 'line'}:
        hvplot_kwargs.update({
            'line_width': 2,
            'hover_line_color': '#0060d0',
        })
    if autorange:
        # NOTE: doesn't seem to work, compare results in
        # https://hvplot.holoviz.org/user_guide/Large_Timeseries.html#webgl-rendering-current-default
        hvplot_kwargs.update({
            'autorange': 'y',
        })

    plot = filtered_df.hvplot(
        x='author_date', y=column,
        kind=kind,
        color='#006dd8',
        responsive=True,
        hover='vline',
        grid=True,
        ylim=(-1, None), ylabel='Contributions', xlabel='',
        padding=(0.005, 0),
        tools=[
            'xpan',
            'box_zoom',
            'wheel_zoom' if autorange else 'wheel_zoom',
            'save',
            'undo',
            'redo',
            'reset',
            'hover',
        ],
        **hvplot_kwargs,
    )
    # manually specifying the default tools gets rid of any preset default tools
    # you also just use an empty list here to use only chosen tools
    plot.opts(default_tools=[])

    return plot


def authors_cards(authors_df: pd.DataFrame,
                  top_n: int = 4) -> list[pn.layout.Card]:
    result: list[pn.layout.Card] = []
    for row in authors_df.head(top_n).itertuples():
        result.append(
            pn.layout.Card(
                header=f"{row[0]}",
                collapsible=False,
            )
        )

    return result


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


# ==================================================
# --------------------------------------------------
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

# might be not a Select widget
top_n_widget = pn.widgets.Select(name="top N", options=[4,10,32], value=4)

# ............................................................
# after the separator

select_plot_kind_widget = pn.widgets.Select(
    name="Plot kind:",
    options=[
        'step',
        'line',
        'bar',
        'area',
        'scatter',
    ],
    disabled_options=[
        'area',
        'scatter',
    ],
    value='step',
    align='end',
)

select_plot_theme_widget = pn.widgets.Select(
    name="Plot theme:",
    options=[
        'caliber',
        'carbon',
        'dark_minimal',
        'light_minimal',
        'night_sky',
        'contrast',
    ],
)

toggle_autorange_widget = pn.widgets.Checkbox(
    name="autoscale 'y' axis when using zoom tools",
    value=True,
)


# --------------------------------------------------
# main contents widgets
select_period_from_widget = pn.widgets.Select(
    name="Period:",
    options={'Any': ''},
    value='Any',
    # style
    width=110,
    margin=(20,5),
)
select_period_from_widget.options = time_range_options(time_range_period)
select_period_from_widget.value = ''
#print(f"{select_period_from_widget.options=}")


def select_period_from_widget__onload() -> None:
    global loaded, warnings
    loaded = True

    #print("select_period_from_widget__onload()")
    if select_file_widget.value is None:
        pn.state.notifications.info('Showing synthetic data created for demonstration purposes.', duration=0)

    for warning in warnings:
        pn.state.notifications.warning(warning)
    warnings = []

    if pn.state.location:
        #print(f"{pn.state.session_args.get('from')=}")
        query_from = pn.state.session_args.get('from', None)
        needs_adjusting = False
        if query_from is not None:
            value_from = query_from[0].decode()
            if value_from == '':
                pass
            elif match := re.match(r'(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.(?P<year>\d{4})', value_from):
                try:
                    datetime.date(int(match.group('year')), int(match.group('month')), int(match.group('day')))
                    needs_adjusting = True
                except ValueError as err:
                    warning_notification(f"from={value_from} is not a valid DD.YY.MMMM date: {err}")
                    value_from = ''
            else:
                warning_notification(f"from={value_from} does not match the DD.YY.MMMM pattern for dates")
                value_from = ''

        else:
            value_from = ''

        #print(f"   {needs_adjusting=}")
        if needs_adjusting:
            select_period_from_widget.in_onload = True
            handle_custom_range(
                widget=select_period_from_widget,
                value=value_from,
            )
            select_period_from_widget.in_onload = False


def select_period_from_widget__callback(*events) -> None:
    #print(f"select_period_from_widget__callback({len(events)=})")
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
                    #print(f"  -> after del[{na_str!r}]: {select_period_from_widget.options=}")


select_period_from_widget.param.watch(select_period_from_widget__callback, ['value'], onlychanged=True)

#: for the select_contribution_type_widget
contribution_types_map = {
    "Commits": "n_commits",
    "Additions": "+:count",
    "Deletions": "-:count",
}
column_to_contribution = {
    v: k for k, v in contribution_types_map.items()
}
select_contribution_type_widget = pn.widgets.Select(
    name="Contributions:",
    options=contribution_types_map,
    value="n_commits",
    width=180,
    margin=(20,0),  # same as `select_period_from_widget`
)

# ##################################################
# --------------------------------------------------
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
    column=select_contribution_type_widget,
    frequency=frequency_names,
    min_max_date=get_date_range_rx,
)

authors_info_df_rx = pn.rx(authors_info_df)(
    timeline_df=get_timeline_df_rx,
    column=select_contribution_type_widget,
    from_date_str=select_period_from_widget,
)
resample_timeline_all_rx = pn.rx(resample_timeline_all)(
    timeline_df=get_timeline_df_rx,
    resample_rate=resample_frequency_widget,
)

plot_commits_rx = pn.rx(plot_commits)(
    resampled_df=resample_timeline_all_rx,
    column=select_contribution_type_widget,
    from_date_str=select_period_from_widget,
    kind=select_plot_kind_widget,
    autorange=toggle_autorange_widget,
)


authors_grid = pn.layout.GridBox(
    ncols=2,
)


def update_authors_grid(authors_df: pd.DataFrame, top_n: int = 4) -> None:
    #print(f"update_authors_grid({top_n=})")
    authors_grid.clear()
    authors_grid.extend(
        authors_cards(
            authors_df=authors_df,
            top_n=top_n,
        )
    )


# NOTE: does not work as intended, displays widgets it depends on
#authors_cards_rx = pn.rx(authors_cards)(
#    authors_df=authors_info_df_rx,
#    top_n=top_n_widget,
#)
bind_update_authors_grid = pn.bind(
    # func
    update_authors_grid,
    # *dependencies
    authors_df=authors_info_df_rx,
    top_n=top_n_widget,
    # keywords
    watch=True,
)
# on init, update the authors_grid widget
bind_update_authors_grid()

# ==================================================
# main app

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
        top_n_widget,

        pn.layout.Divider(), # - - - - - - - - - - - - -

        select_plot_kind_widget,
        select_plot_theme_widget,
        toggle_autorange_widget,
    ],
    main=[
        pn.Column(
            pn.Row(
                pn.pane.HTML(head_text_rx, styles=head_styles),
                select_period_from_widget,
                select_contribution_type_widget,
            ),
            pn.Card(
                pn.Column(
                    pn.pane.HTML(sampling_info_rx, styles=head_styles),
                    pn.pane.HoloViews(plot_commits_rx, theme=select_plot_theme_widget),
                ),
                collapsible=False, hide_header=True,
            )
        ),
        authors_grid,
    ],
)
template.servable()

import datetime
import hashlib
import json
import logging
import os
import re
from collections import namedtuple
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta

# data analysis
import pandas as pd

# dashboard
import panel as pn

# plotting
import hvplot.pandas  # noqa


logger = logging.getLogger("panel.contributors_graph")
pn.extension(
    "jsoneditor", "perspective",
    notifications=True,
    design="material", sizing_mode="stretch_width"
)
pn.state.notifications.position = 'top-center'
loaded = False

# TODO: replace with a better mechanism, e.g. Proxy object for pn.state.notifications
warnings: list[str] = []


def warning_notification(msg: str) -> None:
    if loaded:
        pn.state.notifications.warning(msg)
    else:
        warnings.append(msg)


DATASET_DIR = 'data/examples/stats'


def find_dataset_dir() -> Optional[Path]:
    for TOP_DIR in ['', '..', '../..']:
        full_dir = Path(TOP_DIR).joinpath(DATASET_DIR)

        if full_dir.is_dir():
            return full_dir

    return None


def find_timeline_files(dataset_dir: Optional[Path]) -> dict[str, str]:
    if dataset_dir is None:
        # TODO?: add a warning
        return {}
    else:
        # assuming naming convention *.timeline.*.json for appropriate data files
        return {
            str(path.stem): str(path)
            for path in dataset_dir.glob('*.timeline.*.json')
        }


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


def authors_info_df(timeline_df: pd.DataFrame,
                    column: str = 'n_commits',
                    from_date_str: str = '') -> pd.DataFrame:
    info_columns = list(agg_func_mapping().keys())

    # sanity check
    if column not in info_columns:
        column = info_columns[0]

    filtered_df = filter_df_by_from_date(timeline_df, from_date_str, 'author.timestamp')

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


def agg_func_mapping():
    columns_agg_sum = ['n_commits']
    agg_func_sum = {col: 'sum' for col in columns_agg_sum}

    agg_func = 'sum'
    columns_agg_any = ['+:count', '-:count', 'file_names', 'diff.patch_size', 'diff.groups_spread']
    agg_func_any = {col: agg_func for col in columns_agg_any}

    return agg_func_sum | agg_func_any


#: for the select_contribution_type_widget
contribution_types_map = {
    "Commits": "n_commits",
    "Additions": "+:count",
    "Deletions": "-:count",
    "Files changed": "file_names",
    "Patch size (lines)": "diff.patch_size",
    "Patch spreading (lines)": "diff.groups_spread"
}
column_to_contribution = {
    v: k for k, v in contribution_types_map.items()
}


#@pn.cache
def resample_timeline(timeline_df: pd.DataFrame,
                      resample_rate: str, group_by: Optional[str] = None) -> pd.DataFrame:
    # select appropriate aggregation function for specific columns
    agg_func_map = agg_func_mapping()

    # all columns to aggregate values of
    columns_agg = list(agg_func_map.keys())

    # aggregate over given period of time, i.e. resample
    if group_by is None:
        # resample only
        df_r = timeline_df.resample(
            resample_rate,
            on='author_date'
        )
    else:
        # group by and resample
        df_r = timeline_df.groupby([
            group_by,
            pd.Grouper(key='author_date', freq=resample_rate)
        ])

    return df_r[columns_agg].agg(
        agg_func_map,
        numeric_only=True
    )


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


def author_timeline_df(resample_by_author_df: pd.DataFrame, author_id: str) -> pd.DataFrame:
    return resample_by_author_df.loc[author_id]


#@pn.cache
def get_date_range(timeline_df: pd.DataFrame, from_date_str: str):
    # TODO: create reactive component or bound function to compute from_date to avoid recalculations
    min_date = timeline_df['author_date'].min()
    if from_date_str:
        from_date = pd.to_datetime(from_date_str, dayfirst=True, utc=True)
        min_date = max(min_date, from_date)

    return (
        min_date,
        timeline_df['author_date'].max(),
    )


#@pn.cache
def get_value_range(timeline_df: pd.DataFrame, column: str = 'n_commits'):
    return (
        timeline_df[column].min(),
        timeline_df[column].max(),
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


def html_int_humane(val: int) -> str:
    thousands_sep = " "  # Unicode thin space (breakable in HTML), &thinsp;

    res = f'{val:,}'
    if thousands_sep != ",":
        res = res.replace(",", thousands_sep)

    return f'<data value="{val}" style="white-space: nowrap;">{res}</data>'


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


def author_info(authors_df: pd.DataFrame, author: str = '') -> str:
    author_s: pd.Series = authors_df.loc[author]

    if not author:
        return "{unknown}"

    # TODO: replace inline style with the use of `stylesheets=[stylesheet]`
    # use minus sign '−', rather than dash '-'
    return f"""
    <span style="color: rgb(89, 99, 110);">{html_int_humane(author_s.loc['n_commits'])}&nbsp;commits</span>
    <span class="additionsDeletionsWrapper">
    <span class="color-fg-success" style="color: #1a7f37">{html_int_humane(int(author_s.loc['p_count']))}&nbsp;++</span>
    <span class="color-fg-danger"  style="color: #d1242f">{html_int_humane(int(author_s.loc['m_count']))}&nbsp;−−</span>
    </span>
    """


def plot_commits(resampled_df: pd.DataFrame,
                 column: str = 'n_commits',
                 from_date_str: str = '',
                 xlim: Optional[tuple] = None, ylim: Optional[tuple] = None,
                 marginals: bool = True,
                 kind: str = 'step', autorange: bool = True):
    filtered_df = filter_df_by_from_date(resampled_df, from_date_str)

    hvplot_kwargs = {}
    if kind == 'step':
        hvplot_kwargs.update({
            'where': 'mid',  # 'pre' is correct, but we need to adjust xlim
        })
    if kind in {'step', 'line'}:
        hvplot_kwargs.update({
            'line_width': 2,
            'hover_line_width': 3,
        })
    if autorange:
        # NOTE: doesn't seem to work reliably, compare results in
        # https://hvplot.holoviz.org/user_guide/Large_Timeseries.html#webgl-rendering-current-default
        hvplot_kwargs.update({
            'autorange': 'y',
        })

    if xlim is None:
        xlim = (None, None)
    if ylim is None:
        ylim = (-1, None)
    else:
        # the use of (-1, ...) depends on the column(s)
        # sanity check - TODO: find the source of the bug
        if ylim[1] == 1:
            ylim = (-1, None)
        else:
            ylim = (-1, ylim[1])

    # via https://oklch-palette.vercel.app/ and https://htmlcolorcodes.com/rgb-to-hex/
    color_map = {
        'n_commits': '#006dd8',
        '+:count':   '#008826',
        '-:count':   '#d42000', # or '#c43711',
        # taken from maplotlib/seaborn's 10-hue categorical color palette
        # https://seaborn.pydata.org/tutorial/color_palettes.html
        'file_names': '#937860',
        'diff.patch_size': '#9467bd',
        'diff.groups_spread': '#e377c2',
    }
    color = color_map.get(column, '#006dd8')

    plot = filtered_df.hvplot(
        x='author_date', y=column,
        kind=kind,
        color=color,
        responsive=True,
        hover='vline',
        grid=True,
        xlim=xlim, xlabel='',
        ylim=ylim, ylabel='Contributions',
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
    plot.opts(default_tools=[], responsive=True, toolbar='above')

    # only main plot, and only when turned on
    if xlim == (None, None) and marginals:
        hist = filtered_df.hvplot.hist(
            y=column,
            color=color,
            #bins=20,
            invert=True,
            width=150,
            grid=True,
            xlabel='', xaxis=None,
            ylabel='', yaxis='right',
            padding=(0.005, 0),
            responsive=True,
        )
        hist.opts(default_tools=[], align='end', toolbar=None)

        return plot << hist

    return plot


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

    return {
        k: '' if v is None else (today + relativedelta(months=-v)).strftime('%d.%m.%Y')
        for k, v in period_name_to_months.items()
    }


def handle_custom_range(widget: pn.widgets.select.SingleSelectBase,
                        value: Optional[str], na_str: str = 'Custom range') -> None:
    if value is None or value in widget.options.values():
        if na_str in widget.options:
            # selecting pre-defined range, delete 'Custom range'
            del widget.options[na_str]

        # no value, or 'Custom range' already present - no need to add it
        return

    widget.options[na_str] = value
    widget.value = value
    widget.param.trigger('options')
    #widget.param.trigger('value')      # NOTE: not needed, causes unnecessary recalculation
    #widget.disabled_options = [value]  # NOTE: it is forbidden to set `value` to disabled option


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

toggle_marginals_widget = pn.widgets.Checkbox(
    name="marginals for main plot: hist",
    value=False,
)

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


def select_period_from_widget__onload() -> None:
    global loaded, warnings
    loaded = True

    if select_file_widget.value is None:
        pn.state.notifications.info('Showing synthetic data created for demonstration purposes.', duration=0)

    for warning in warnings:
        pn.state.notifications.warning(warning)
    warnings = []

    if pn.state.location:
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

        # don't adjust value if not needed
        if needs_adjusting:
            select_period_from_widget.in_onload = True
            handle_custom_range(
                widget=select_period_from_widget,
                value=value_from,
            )
            select_period_from_widget.in_onload = False


def select_period_from_widget__callback(*events) -> None:
    na_str = 'Custom range'

    for event in events:
        if event.what == 'value' and event.name == 'value':
            # value of attribute 'value' changed
            if not getattr(select_period_from_widget, 'in_onload', False):
                # delete 'Custom range' if needed, and not in onload callback
                if na_str in select_period_from_widget.options:
                    del select_period_from_widget.options[na_str]
                    select_period_from_widget.param.trigger('options')


select_period_from_widget.param.watch(select_period_from_widget__callback, ['value'], onlychanged=True)

select_contribution_type_widget = pn.widgets.Select(
    name="Contributions:",
    options=contribution_types_map,
    value="n_commits",
    width=180,
    margin=(20,0),  # TODO: extract variable - it is the same as in `select_period_from_widget`
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

authors_info_df_rx = pn.rx(authors_info_df)(
    timeline_df=get_timeline_df_rx,
    column=select_contribution_type_widget,
    from_date_str=select_period_from_widget,
)
resample_timeline_all_rx = pn.rx(resample_timeline)(
    timeline_df=get_timeline_df_rx,
    resample_rate=resample_frequency_widget,
)
resample_timeline_by_author_rx = pn.rx(resample_timeline)(
    timeline_df=get_timeline_df_rx,
    resample_rate=resample_frequency_widget,
    group_by='author.email',  # TODO: make it configurable (code duplication)
)
get_date_range_rx = pn.rx(get_date_range)(
    timeline_df=get_timeline_df_rx,
    from_date_str=select_period_from_widget,
)
get_value_range_rx = pn.rx(get_value_range)(
    timeline_df=resample_timeline_all_rx,
    column=select_contribution_type_widget,
)

sampling_info_rx = pn.rx(sampling_info)(
    resample=resample_frequency_widget,
    column=select_contribution_type_widget,
    frequency=frequency_names,
    min_max_date=get_date_range_rx,
)

plot_commits_rx = pn.rx(plot_commits)(
    resampled_df=resample_timeline_all_rx,
    column=select_contribution_type_widget,
    from_date_str=select_period_from_widget,
    marginals=toggle_marginals_widget,
    kind=select_plot_kind_widget,
    autorange=toggle_autorange_widget,
)
bind_plot_commits_no_df = pn.bind(
    # function
    plot_commits,
    # arguments
    # NOTE: explicitly missing `resampled_df=...,`
    column=select_contribution_type_widget,
    from_date_str=select_period_from_widget,
    xlim=get_date_range_rx,
    ylim=get_value_range_rx,  # TODO: allow to switch between totals, max N, and own
    kind=select_plot_kind_widget,
    autorange=toggle_autorange_widget,
)

authors_grid = pn.layout.GridBox(
    ncols=2,
)


#@pn.cache
def gravatar_url(email: str, size: int = 16) -> str:
    # https://docs.gravatar.com/api/avatars/python/

    # Set default parameters
    # ...

    # Encode the email to lowercase and then to bytes
    email_encoded = email.lower().encode('utf-8')

    # Generate the SHA256 hash of the email
    email_hash = hashlib.sha256(email_encoded).hexdigest()

    # https://docs.gravatar.com/api/avatars/images/
    # Construct the URL with encoded query parameters
    query_params = urlencode({'s': str(size)})  # NOTE: will be needed for 'd' parameter
    url = f"https://www.gravatar.com/avatar/{email_hash}?{query_params}"

    return url


def authors_list(authors_df: pd.DataFrame,
                 top_n: Optional[int] = None) -> list[str]:
    # TODO: return mapping { "[name] <[email]>": "[email]",... },
    #       instead of returning list of emails [ "[email]",... ]
    if top_n is None:
        return authors_df.index.to_list()
    else:
        return authors_df.head(top_n).index.to_list()


def authors_cards(authors_df: pd.DataFrame,
                  resample_by_author_df: pd.DataFrame,
                  top_n: int = 4) -> list[pn.layout.Card]:
    result: list[pn.layout.Card] = []
    avatar_size = 20

    row: namedtuple('Pandas', ['Index', 'n_commits', 'p_count', 'm_count', 'author_name'])
    for i, row in enumerate(authors_df.head(top_n).itertuples(), start=1):
        result.append(
            pn.layout.Card(
                pn.Column(
                    pn.pane.HTML(
                        author_info(authors_df=authors_df, author=row.Index)
                    ),
                    pn.pane.HoloViews(
                        bind_plot_commits_no_df(resampled_df=resample_by_author_df.loc[row.Index]),
                        theme=select_plot_theme_widget,
                        height=250,  # TODO: find a better way than fixed height
                        sizing_mode='stretch_width',
                        #sizing_mode='scale_both',  # NOTE: does not work, and neither does 'stretch_both'
                        #aspect_ratio=1.5,  # NOTE: does not help to use 'scale_both'/'stretch_both'
                        margin=5,
                    ),
                ),
                # NOTE: could not get it to span the whole width ot the card,
                # not without resorting to specifying fixed width
                header=pn.FlexBox(
                    # author.name <author.email>, using most common author.name
                    pn.pane.HTML('<div class="author">'
                                 f'<img src="{gravatar_url(row.Index, avatar_size)}" width="{avatar_size}" height="{avatar_size}" alt="" /> '
                                 f'{row.author_name} &lt;{row.Index}&gt;'
                                 '</div>'),
                    # position in the top N list
                    pn.pane.HTML(f'<div class="chip">#{i}</div>', width=20),
                    # FlexBox parameters
                    # https://css-tricks.com/snippets/css/a-guide-to-flexbox/
                    # https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_flexible_box_layout/Basic_concepts_of_flexbox
                    flex_direction="row",
                    flex_wrap="nowrap",
                    justify_content="space-between",
                    align_items="baseline",
                    gap="1 rem",
                    # layoutable parameters
                    sizing_mode='stretch_width',
                    width_policy="max",
                    #width=300,
                    #styles={"width": "100%"}
                ),
                collapsible=False,
            )
        )

    return result


def update_authors_grid(authors_df: pd.DataFrame,
                        resample_by_author_df: pd.DataFrame,
                        top_n: int = 4,
                        **_kwargs) -> None:
    authors_grid.clear()
    authors_grid.extend(
        authors_cards(
            authors_df=authors_df,
            resample_by_author_df=resample_by_author_df,
            top_n=top_n,
        )
    )


authors_list_rx = pn.rx(authors_list)(
    authors_df=authors_info_df_rx,  # depends: column, from_date_str
    top_n=top_n_widget,
)
# NOTE: does not work as intended, displays widgets it depends on
# might be helped by wrapping in pn.ReactiveExpr
#authors_cards_rx = pn.rx(authors_cards)(
#    authors_df=authors_info_df_rx,
#    top_n=top_n_widget,
#)
bind_update_authors_grid = pn.bind(
    # func
    update_authors_grid,
    # *dependencies
    authors_df=authors_info_df_rx,  # depends: column, from_date_str
    resample_by_author_df=resample_timeline_by_author_rx,  # depends: resample_rate, group_by
    # NOTE: passing partially bound function (as now) results, for some strange reason, in
    # TypeError: plot_commits() missing 1 required positional argument: 'resampled_df'
    #plot_commits_partial=bind_plot_commits_no_df,
    top_n=top_n_widget,
    # used only to define dependencies
    _xlim=get_date_range_rx,
    _ylim=get_value_range_rx,
    _kind=select_plot_kind_widget,
    _autorange=toggle_autorange_widget,
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
    # TODO: rename 'resample' to 'freq' (shorter and more memorable)
    # TODO: validate value of 'resample'/'freq', instead of trying to use it as is
    pn.state.location.sync(resample_frequency_widget, {'value': 'resample'})
    pn.state.location.sync(select_period_from_widget, {'value': 'from'})

pn.state.onload(select_period_from_widget__onload)

# GitHub: ..., line counts have been omitted because commit count exceeds 10,000.
template = pn.template.MaterialTemplate(
    site="diffannotator",
    title="Contributors Graph",  # TODO: make title dynamic
    favicon="favicon.png",
    sidebar_width=350,
    sidebar=[
        select_file_widget,
        select_repo_widget,
        resample_frequency_widget,
        toggle_marginals_widget,
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

json_timeline_data_panel = pn.widgets.JSONEditor(
    value=get_timeline_data_rx,  # or get_timeline_data(), which is @pn.cache'd
    mode='view',
    menu=True, search=True,
    width_policy='max',
    height=500,
)
timeline_all_panel = pn.pane.Perspective(
    get_timeline_df_rx,
    title=pn.rx("Perspective: repo={repo!r}") \
        .format(repo=select_repo_widget),
    editable=False,
    width_policy='max',
    height=500,
)
resample_timeline_all_panel = pn.pane.Perspective(
    resample_timeline_all_rx,  # or use reactive component, maybe
    title=pn.rx("Perspective: repo={repo!r}, resample={resample!r} all") \
        .format(repo=select_repo_widget, resample=resample_frequency_widget),
    editable=False,
    width_policy='max',
    height=500,
)
resample_timeline_by_author_panel = pn.pane.Perspective(
    resample_timeline_by_author_rx,
    title=pn.rx("Perspective: repo={repo!r}, resample={resample!r} by author") \
        .format(repo=select_repo_widget, resample=resample_frequency_widget),
    editable=False,
    width_policy='max',
    height=500,
)
authors_info_panel = pn.pane.Perspective(
    authors_info_df_rx,
    title=pn.rx("Authors info for repo={repo!r}, from={from_date!r}") \
        .format(repo=select_repo_widget, from_date=select_period_from_widget),
    editable=False,
    width_policy='max',
    height=500,
)
select_author_widget = pn.widgets.Select(
    name="author",
    options=authors_list_rx,
)
author_timeline_df_rx = pn.rx(author_timeline_df)(
    resample_by_author_df=resample_timeline_by_author_rx,
    author_id=select_author_widget,
)
author_timeline_panel = pn.Column(
    select_author_widget,
    pn.pane.Perspective(
        author_timeline_df_rx,
        title=pn.rx("repo={repo!r}, author={author!r}") \
            .format(
                repo=select_repo_widget,
                author=select_author_widget,
        ),
        editable=False,
        width_policy='max',
        height=500,
    ),
)
template.main.extend([
    pn.layout.Divider(),
    pn.Tabs(
        ('JSON', json_timeline_data_panel),
        ('data', timeline_all_panel),
        ('resampled', resample_timeline_all_panel),
        ('authors info', authors_info_panel),
        ('by author+resampled', resample_timeline_by_author_panel),
        (
            #pn.rx("author={author}").format(author=select_author_widget).rx.pipe(str),
            'selected author',
            author_timeline_panel,
        ),
        #dynamic=True,
        active=1,
    ),
])

template.servable()

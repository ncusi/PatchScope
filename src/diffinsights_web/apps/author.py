#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from typing import Optional

import numpy as np
import panel as pn
import pandas as pd
import seaborn as sns
from matplotlib.colors import LogNorm
from matplotlib.figure import Figure

from diffinsights_web.datastore import find_dataset_dir
from diffinsights_web.datastore.timeline import \
    find_timeline_files, find_repos, \
    get_timeline_data, get_timeline_df, path_to_name, frequency_names
from diffinsights_web.utils import round_10s
from diffinsights_web.views.plots.period import add_split_localtime, plot_periodicity_heatmap
from diffinsights_web.views.plots.sankey_mermaid import MermaidSankeyPlot
from diffinsights_web.widgets.caching import ClearCacheButton


logger = logging.getLogger("panel.author")
pn.extension(
    design="material", sizing_mode="stretch_width",
)

cols_plus_all  = [f"+:type.{line_type}"
                  for line_type in ['code', 'documentation', 'test', 'other', 'data', 'markup', 'project']]
cols_minus_all = [f"-:type.{line_type}"
                  for line_type in ['code', 'documentation', 'test', 'other', 'data', 'markup', 'project']]
all_possible_pm_col_basenames = [
    f"type.{line_type}"
    for line_type in ['code', 'documentation', 'test', 'other', 'data', 'markup', 'project']
]
all_possible_pm_col_perc_basenames = [f"{col} [%]" for col in all_possible_pm_col_basenames if col != 'count']


# ---------------------------------------------------------------------------
# functions to get data, required to construct other widgets
author_column = 'author.email'


@pn.cache
def get_authors(tf_timeline_df: pd.DataFrame) -> list[str]:
    #return tf_timeline_df[author_column].unique().tolist()
    return tf_timeline_df[author_column].value_counts(sort=True).index.tolist()


@pn.cache
def get_authors_counts(tf_timeline_df: pd.DataFrame) -> dict[str, int]:
    return tf_timeline_df[author_column].value_counts().to_dict()


def get_authors_options(tf_timeline_df: pd.DataFrame) -> dict[str, str]:
    authors_counts = get_authors_counts(tf_timeline_df)
    return {
        f"{author:14s}: {authors_counts[author]:6d} commits": author
        for author in authors_counts.keys()
    }


# ---------------------------------------------------------------------------
# widgets
dataset_dir = find_dataset_dir()
select_file_widget = pn.widgets.Select(
    #name="input JSON file",
    name="repository data",  # NOTE: this name is easier to understand, even if less correct
    options=find_timeline_files(dataset_dir)
)

get_timeline_data_rx = pn.rx(get_timeline_data)(
    json_path=select_file_widget,
)
find_repos_rx = pn.rx(find_repos)(
    timeline_data=get_timeline_data_rx,
)
repos_widget = pn.widgets.Select(
    #name="repository",
    name="name of data subset",  # NOTE: in all examples there is only one subset
    options=find_repos_rx,
    disabled=find_repos_rx.rx.pipe(len) <= 1,
)
get_timeline_df_rx = pn.rx(get_timeline_df)(
    json_path=select_file_widget,
    timeline_data=get_timeline_data_rx,
    repo=repos_widget,
)

authors_rx = pn.rx(get_authors)(
    tf_timeline_df=get_timeline_df_rx,
)
authors_options_rx = pn.rx(get_authors_options)(
    tf_timeline_df=get_timeline_df_rx,
)
authors_widget = pn.widgets.Select(
    name="author",
    value=authors_rx[0],
    options=authors_rx
)
authors_radio_box = pn.widgets.RadioBoxGroup(
    name='choose author',
    value=authors_rx[0],
    inline=False,
    options=authors_options_rx,
)

# mapping form display name to alias
time_series_frequencies = {
    'calendar day frequency': 'D',
    'weekly frequency': 'W',
    'semi-month end frequency (15th and end of month)': 'SME',
    'month end frequency': 'ME',
    'quarter end frequency': 'QE',
}
resample_rule_widget = pn.widgets.Select(
    name="frequency",
    value='ME',
    options=time_series_frequencies,
)

# Line type, or file purpose
column_base_widget = pn.widgets.Select(
    name="column [base]name",
    value='type.code',
    options=[*all_possible_pm_col_basenames, *all_possible_pm_col_perc_basenames],
    # disabled_options=all_possible_pm_col_perc_basenames
)
autoscale_widget = pn.widgets.Checkbox(
    name='autoscale column [base]name',
    value=True
)
pm_col_widget = pn.Row(
    pn.FlexBox(
        column_base_widget,
        # spacer? divider?
        autoscale_widget,
        align_items='baseline',
    ),
)

# resampling: aggregation
aggregation_functions = [
    'sum',
    'mean',
    'median',
    'max',
    'min',
    'std',
]
agg_func_widget = pn.widgets.Select(
    name="aggregation function",
    value=aggregation_functions[0],
    options=aggregation_functions,
)

# Histogram (and bihistogram) options
bin_width_widget = pn.widgets.EditableIntSlider(
    name="bin width",
    value=3,
    start=1, fixed_start=1, end=25,
    margin=(-5, 10)
)
max_value_widget = pn.widgets.EditableIntSlider(
    name="max value",
    value=100, start=10, fixed_start=1, end=500,
    step=5,
    margin=(-2, 10)
)
hist_widget = pn.WidgetBox(
    'histogram',
    bin_width_widget,
    max_value_widget,
    disabled=False
)

plot_sizing_mode = pn.widgets.Select(
    name='sizing_mode',
    options=['fixed', 'stretch_width'],
    value='fixed',
    disabled=True
)
plot_format = pn.widgets.Select(
    name='format',
    options=['png', 'svg'],
    value='png'
)
sidebar_width = pn.widgets.IntSlider(
    name='sidebar width',
    start=100, end=600,
    step=10,
    value=370
)


# ---------------------------------------------------------------------------
# data processing functions
@pn.cache
def resample_timeline(
    tf_timeline_df: pd.DataFrame,
    pm_count_cols: list[str],
    diff_x_cols: list[str],
    author: str,
    resample_rate: str = 'ME',
    agg_func: str = 'sum',
) -> pd.DataFrame:
    ## DEBUG
    #print(f"> resampling for {author} at sample rate '{resample_rate}' and agg_func '{agg_func}'")
    df = tf_timeline_df[tf_timeline_df[author_column] == author].resample(
        resample_rate,
        on='author_date'
    )[['n_commits', *pm_count_cols, *diff_x_cols]].agg(
        {col: agg_func if col in [*pm_count_cols, *diff_x_cols] else 'sum'  # excludes 'n_commits'
         for col in ['n_commits', *pm_count_cols, *diff_x_cols]},
        numeric_only=True
    )

    # to be possibly used for xlabel when plotting
    df['author.date(UTC)'] = df.index
    df['author.date(Y-m)'] = df.index.strftime('%Y-%m')

    # TODO: do it with dependencies / bound functions
    # NOTE: Panel specific !!!
    #column_base_widget.disabled_options = all_possible_pm_col_perc_basenames
    logger.debug(f"resample_timeline({author=}, {resample_rate=}, {agg_func=}) -> pd.DataFrame({hex(id(df))})")

    return df


@pn.cache
def add_pm_count_perc(
    resampled_df: pd.DataFrame,
    pm_count_cols: list[str],
) -> pd.DataFrame:
    ## DEBUG
    # print(f"RUNNING add_pm_count_perc({hex(id(resampled_df))}) -> {pm_count_cols}")
    for col in pm_count_cols:
        if col in {'-:count', '+:count'}:  # '-:count' or '+:count'
            continue

        if col not in resampled_df:
            # print(f"  ZERO {col}")
            resampled_df.loc[:, col] = 0

        col_perc = f"{col} [%]"
        if col_perc in resampled_df.columns:
            # print(f"  SKIP {col_perc}")
            continue

        if col.startswith('+:'):
            resampled_df.loc[:, col_perc] = resampled_df[col] / resampled_df['+:count']
        elif col.startswith('-:'):
            resampled_df.loc[:, col_perc] = resampled_df[col] / resampled_df['-:count']

    # TODO: do it with dependencies / bound functions
    # NOTE: Panel specific !!!
    #column_base_widget.disabled_options = []
    logger.debug(
        f"add_pm_count_perc(resampled_df=pd.DataFrame({hex(id(resampled_df))})) -> pd.DataFrame({hex(id(resampled_df))})")

    return resampled_df


# function that returns filtered (but not resampled) data
@pn.cache
def tf_timeline_df_author(tf_timeline_df: pd.DataFrame, author: str) -> pd.DataFrame:
    return tf_timeline_df[tf_timeline_df[author_column] == author]


# ..........................................................................
# data analysis/extraction functions
@pn.cache
def get_pm_count_cols(tf_timeline_df: pd.DataFrame) -> list[str]:
    pm_count_cols = [col for col in tf_timeline_df.columns if col.startswith('+:') or col.startswith('-:')]
    pm_count_cols.sort(key=lambda s: s[2:] + ('0' if s[0] == '-' else '1'))

    return pm_count_cols


@pn.cache
def get_diff_x_cols(tf_timeline_df: pd.DataFrame) -> list[str]:
    return [col for col in tf_timeline_df.columns if col.startswith('diff.')]


# ...........................................................................
# information summary functions
@pn.cache
def page_info_html(repo_name: str,
                   author_desc: str,
                   resample_freq: str,
                   frequency_names_map: dict[str, str]) -> str:
    return f"""
    <h1>Contributions to {repo_name} repository by {author_desc}</h1>
    <p>per {frequency_names_map.get(resample_freq, 'unknown frequency')} sampling is used</p>
    """


# ...........................................................................
# plotting functions
def plot_commits(
    resampled_df: pd.DataFrame,
    repo_desc: str, author_desc: str,
    frequency_names_map: dict[str, str],
    resample_rate: str = 'ME',
    figsize: tuple[float, float] = (5, 5),
) -> Figure:
    sns.set_style("whitegrid")

    fig = Figure(figsize=figsize)
    ax = fig.subplots()

    sns.lineplot(ax=ax, data=resampled_df,
                 x='author_date', y='n_commits',
                 color='blue', drawstyle='steps-post')

    ax.fill_between(resampled_df.index, resampled_df['n_commits'],
                    alpha=0.2, color='blue', step='post')
    # ax.set_ylim(0, 120)
    ax.set_ylabel("commits")
    # ax.set_xlim(datetime.date(2017, 3, 31), datetime.date(2024, 9, 30))
    ax.set_xlabel("author date")

    #fig.suptitle(f'repo={repo_desc}, count of commits, resample="{resample_rate}"', fontsize=10)
    fig.suptitle(f'Commits over time in {repo_desc} repository'
                 f', {frequency_names_map.get(resample_rate, "unknown")}ly contributions',
                 fontsize=10)
    ax.set_title(f"authored by {author_desc}", fontsize=9)

    return fig


# https://stackoverflow.com/questions/62678411/how-to-plot-a-paired-histogram-using-seaborn
# https://stackoverflow.com/a/62678622/46058

def plot_counts(
    resampled_df: pd.DataFrame,
    repo_desc: str, author_desc: str,
    frequency_names_map: dict[str, str],
    resample_rate: str = 'ME',
    agg_func: str = 'sum',
    figsize: tuple[float, float] = (5, 5),
) -> Figure:
    sns.set_style("whitegrid")

    ## DEBUG figsize
    # print(f"plot_counts(): {figsize=}")
    fig = Figure(figsize=figsize)
    axes = fig.subplots(nrows=2, ncols=1, sharex=True)

    max_count = resampled_df[['+:count', '-:count']].max().max()
    max_ylim = round_10s(max_count)

    for ax, column, color, invert in zip(axes.ravel(), ['+:count', '-:count'], ['green', 'red'], [False, True]):
        sns.lineplot(ax=ax, data=resampled_df,
                     x='author_date', y=column,
                     color=color, drawstyle='steps-post')

        ax.fill_between(resampled_df.index, resampled_df[column],
                        alpha=0.2, color=color, step='post')
        ax.set_ylim(0, max_ylim)
        ax.set_ylabel(f"{agg_func}({column})")

        if invert:
            ax.invert_yaxis()
            ax.set_xlabel('author date')
        else:
            # ax.set_title(f"author={author_desc}", fontsize=9)
            ax.axhline(0, linewidth=1, color="k")

    #fig.suptitle(f'repo={repo_desc}, author={author_desc}, lines per resample="{resample_rate}"', fontsize=10)
    fig.suptitle(f'Changed lines in {repo_desc} repository by {author_desc}, '
                 f'{frequency_names_map.get(resample_rate, "unknown")}ly {agg_func}',
                 fontsize=10)
    fig.subplots_adjust(hspace=0)

    # plt.show()
    # plt.close(fig) # CLOSE THE FIGURE!
    return fig


def plot_pm_col(
    resampled_df: pd.DataFrame,
    repo_desc: str, author_desc: str,
    column_base: str = 'type.code',
    resample_rate: str = 'ME',
    agg_func: str = 'sum',
    rescale: bool = True,
    figsize: tuple[float, float] = (5, 5),
) -> Figure:
    sns.set_style("whitegrid")

    p_col = f"+:{column_base}"
    m_col = f"-:{column_base}"

    fig = Figure(figsize=figsize)
    axes = fig.subplots(nrows=2, ncols=1, sharex=True)

    #if p_col not in resampled_df.columns:
    #    # retrying
    #    ## DEBUG
    #    # print(f"(re)running add_pm_count_perc because of missing {p_col!s}")
    #    resampled_df = add_pm_count_perc(resampled_df)

    if p_col not in resampled_df.columns:
        err_msg = f"{p_col!r} not in columns of DataFrame (BUG)"
        print(err_msg)

        fig.suptitle(err_msg)
        return fig  # empty figure

    if column_base.endswith(' [%]'):
        max_ylim = 1.05
    elif rescale or getattr(plot_pm_col, 'prev_max_ylim', None) is None:
        max_count = resampled_df[[p_col, m_col]].max().max()
        max_ylim = round_10s(max_count)
        if max_ylim == 0:  # degenerate case
            max_ylim = 10
        plot_pm_col.prev_max_ylim = max_ylim
    else:
        max_ylim = getattr(plot_pm_col, 'prev_max_ylim')

    for ax, column, color, invert in zip(axes.ravel(), [p_col, m_col], ['green', 'red'], [False, True]):
        sns.lineplot(ax=ax, data=resampled_df,
                     x='author_date', y=column,
                     color=color, drawstyle='steps-post')

        ax.fill_between(resampled_df.index, resampled_df[column],
                        alpha=0.2, color=color, step='post')
        ax.set_ylim(0, max_ylim)

        if invert:
            ax.invert_yaxis()
            ax.set_ylabel(f"{agg_func}({column})", loc="bottom", fontsize=9)
        else:
            # ax.set_title(f"author={author_desc}", fontsize=9)
            ax.set_ylabel(f"{agg_func}({column})", loc="top", fontsize=9)
            ax.axhline(0, color="k")

    fig.suptitle(f'repo={repo_desc}, author={author_desc}, lines per resample="{resample_rate}"', fontsize=10)
    fig.subplots_adjust(hspace=0)

    return fig


def plot_diff_3sizes(
    resampled_df: pd.DataFrame,
    repo_desc: str, author_desc: str,
    zero_s: Optional[pd.Series] = None,
    rescale_n_mod: bool = True,
    drop_yaxis: bool = False,
    resample_rate: str = 'ME',
    agg_func: str = 'sum',
    figsize: tuple[float, float] = (5, 5),
) -> Figure:
    sns.set_style("whitegrid")
    fig = Figure(figsize=figsize)
    ax = fig.subplots()

    if rescale_n_mod:
        n_mod_scale = 1.0
        #n_mod_label = "2*mod"
        n_mod_label = "mod"
    else:
        n_mod_scale = 0.5
        n_mod_label = "mod"

    # fill areas
    ax.fill_between(
        resampled_df.index,
        -resampled_df['diff.n_rem'] +
        -n_mod_scale * resampled_df['diff.n_mod']
        - (0 if zero_s is None else 0.5 * zero_s),
        -n_mod_scale * resampled_df['diff.n_mod']
        - (0 if zero_s is None else 0.5 * zero_s),
        color='r', label='rem',
        alpha=0.3, step='post', interpolate=True,
    )
    ax.fill_between(
        resampled_df.index,
        -n_mod_scale * resampled_df['diff.n_mod']
        - (0 if zero_s is None else 0.5 * zero_s),
        +n_mod_scale * resampled_df['diff.n_mod']
        - (0 if zero_s is None else 0.5 * zero_s),
        color='b', label=n_mod_label,
        alpha=0.4, step='post', interpolate=True,
    )
    ax.fill_between(
        resampled_df.index,
        +n_mod_scale * resampled_df['diff.n_mod']
        - (0 if zero_s is None else 0.5 * zero_s),
        +n_mod_scale * resampled_df['diff.n_mod'] +
        resampled_df['diff.n_add']
        - (0 if zero_s is None else 0.5 * zero_s),
        color='g', label='add',
        alpha=0.3, step='post', interpolate=True,
    )

    # top and bottom lines
    ax.plot(
        resampled_df.index,
        -resampled_df['diff.n_rem'] +
        -n_mod_scale * resampled_df['diff.n_mod']
        - (0 if zero_s is None else 0.5 * zero_s),
        color='r', lw=0.9, alpha=0.7,  # label='rem',
        drawstyle='steps-post',
    )
    ax.plot(
        resampled_df.index,
        +resampled_df['diff.n_add'] +
        +n_mod_scale * resampled_df['diff.n_mod']
        - (0 if zero_s is None else 0.5 * zero_s),
        color='g', lw=0.9, alpha=0.7,  # label='add',
        drawstyle='steps-post',
    )

    ax.legend()
    ax.set_xlabel('author.date')
    if drop_yaxis:
        ax.set_yticklabels([])
        # ax.set_yticks([])
        # ax.yaxis.set_visible(False)
        # ax.set_axis_off()
    else:
        ax.set_ylabel(f'{agg_func} of lines per {resample_rate!r}')

    fig.suptitle(f'repo={repo_desc}, author={author_desc}, sample="{resample_rate}"', fontsize=10)

    return fig


def plot_diff_pm(
    resampled_df: pd.DataFrame,
    repo_desc: str, author_desc: str,
    drop_yaxis: bool = False,
    resample_rate: str = 'ME',
    agg_func: str = 'sum',
    figsize: tuple[float, float] = (5, 5),
) -> Figure:
    sns.set_style("whitegrid")
    fig = Figure(figsize=figsize)
    ax = fig.subplots()

    ax.fill_between(
        resampled_df.index,
        -resampled_df['-:count'],
        color='r', label='−:count',
        alpha=0.4, step='post', interpolate=True,
    )
    ax.fill_between(
        resampled_df.index,
        +resampled_df['+:count'],
        color='g', label='+:count',
        alpha=0.4, step='post', interpolate=True,
    )

    ax.plot(
        resampled_df.index,
        -resampled_df['-:count'],
        color='r', lw=0.9, alpha=0.7, #label='rem',
        drawstyle='steps-post',
    )
    ax.plot(
        resampled_df.index,
        +resampled_df['+:count'],
        color='g', lw=0.9, alpha=0.7, #label='add',
        drawstyle='steps-post',
    )

    ax.legend()
    ax.set_xlabel('author.date')
    if drop_yaxis:
        ax.set_yticklabels([])
        #ax.set_yticks([])
        #ax.yaxis.set_visible(False)
        #ax.set_axis_off()
    else:
        ax.set_ylabel(f'{agg_func} of lines per {resample_rate!r}')

    fig.suptitle(f'repo={repo_desc}, author={author_desc}, sample="{resample_rate}"', fontsize=10)

    return fig


def plot_split_size(
    resampled_df: pd.DataFrame,
    figsize: tuple[float, float] = (5, 5),
) -> Figure:
    sns.set_style("whitegrid")

    fig = Figure(figsize=figsize)
    #axes = fig.subplots(nrows=2, ncols=1, sharex=True)
    ax = fig.subplots()

    resampled_df.plot.area(
        use_index=True, y=['diff.n_rem', 'diff.n_mod', 'diff.n_add'],
        color=['r', 'b', 'g'], alpha=0.6,
        #drawstyle='steps-post',  # does NOT work!
        ax=ax,
    )

    return fig


def bihist(
    ax,
    dataset1, dataset2,
    dataset1_name='dataset1', dataset2_name='dataset2',
    dataset1_color='g', dataset2_color='r',
    bins=None,
):
    # Plot the first histogram
    ax.hist(dataset1, bins=bins, label=dataset1_name, color=dataset1_color)

    # Plot the second histogram
    # (notice the negative weights, which flip the histogram upside down)
    ax.hist(dataset2, weights=-np.ones_like(dataset2), bins=bins, label=dataset2_name, color=dataset2_color)
    ax.axhline(0, color="k", linewidth=0.2)
    ax.legend()


def plot_bihist(
    dataset1, dataset2,
    dataset1_name='dataset1', dataset2_name='dataset2',
    dataset1_color='g', dataset2_color='r',
    bin_width=5, max_value=100, figsize=None
):
    sns.set_style("whitegrid")

    fig = Figure(figsize=figsize)
    ax = fig.subplots()

    bins = np.arange(0, max_value + bin_width, bin_width)

    bihist(ax,
           dataset1, dataset2,
           dataset1_name, dataset2_name,
           dataset1_color, dataset2_color,
           bins)

    return fig


def bihist_pm_df(
    df,
    column_fmt='{pm}:count',
    color_plus='g', color_minus='r',
    agg_func=None,
    bin_width=5, max_value=100,
    figsize=None,
    title=None,
):
    added_counts_column = column_fmt.format(pm='+')
    removed_counts_column = column_fmt.format(pm='-')
    added_counts_name = f"{column_fmt.format(pm='+')}"  # Unicode +
    removed_counts_name = f"{column_fmt.format(pm='−')}"  # Unicode −

    added_counts = df[added_counts_column].values
    removed_counts = df[removed_counts_column].values

    # TODO: automatic max_value if None
    fig = plot_bihist(dataset1=added_counts, dataset2=removed_counts,
                      dataset1_name=added_counts_name, dataset2_name=removed_counts_name,
                      dataset1_color=color_plus, dataset2_color=color_minus,
                      bin_width=bin_width, max_value=max_value, figsize=figsize)

    if title is not None:
        fig.suptitle(title, fontsize=10)

    if agg_func is None:
        fig.supxlabel(column_fmt.format(pm='±'))
    else:
        fig.supxlabel(f"{agg_func}({column_fmt.format(pm='±')})")

    return fig


def plot_heatmap(
    resampled_df: pd.DataFrame,
    repo_desc: str, author_desc: str,
    frequency_names_map: dict[str, str],
    resample_rate: str = 'ME', agg_func: str = 'sum',
    figsize: tuple[float, float] = (16, 4),
) -> Figure:
    for c in cols_plus_all:
        if c not in resampled_df.columns:
            resampled_df[c] = 0

    for c in cols_minus_all:
        if c not in resampled_df.columns:
            resampled_df[c] = 0

    resampled_df = resampled_df.set_index('author.date(Y-m)')

    sns.set_style("whitegrid")

    fig = Figure(figsize=figsize)
    axes = fig.subplots(nrows=2, ncols=1, sharex='col')

    sns.heatmap(resampled_df[cols_plus_all].transpose(),
                #square=True,
                cmap='Greens', vmin=0, vmax=15000,
                xticklabels=5, norm=LogNorm(),
                ax=axes[1])
    axes[1].set_xlabel('\nauthor date')

    sns.heatmap(resampled_df[reversed(cols_minus_all)].transpose(),
                #square=True,
                cmap='Reds', vmin=0, vmax=15000,
                xticklabels=5, norm=LogNorm(),
                ax=axes[0])
    axes[0].get_xaxis().set_visible(False)

    #fig.suptitle(f'repo={repo_desc}, author={author_desc}, resample="{resample_rate}", agg_func={agg_func!r}',
    #             fontsize=10)
    fig.suptitle(f'Number of added (\'+\') and removed (\'−\') lines in {repo_desc} repository, '
                 f'in commits authored by {author_desc}, '
                 f'{frequency_names_map.get(resample_rate, "unknown")}ly {agg_func} per line type',
                 fontsize=10)
    # fig.subplots_adjust(hspace=-0.2)

    return fig


# ---------------------------------------------------------------------------
# reactive components
get_pm_count_cols_rx = pn.rx(get_pm_count_cols)(
    tf_timeline_df=get_timeline_df_rx,
)
get_diff_x_cols_rx = pn.rx(get_diff_x_cols)(
    tf_timeline_df=get_timeline_df_rx,
)

# dependent data, part 1
resample_timeline_rx = pn.rx(resample_timeline)(
    tf_timeline_df=get_timeline_df_rx,
    pm_count_cols=get_pm_count_cols_rx,
    diff_x_cols=get_diff_x_cols_rx,
    author=authors_widget,
    resample_rate=resample_rule_widget,
    agg_func=agg_func_widget,
)
# dependent data, part 1: special case for heatmap (for now),
# because resample rate different from 'ME' doesn't look good
resample_timeline_ME_rx = pn.rx(resample_timeline)(
    tf_timeline_df=get_timeline_df_rx,
    pm_count_cols=get_pm_count_cols_rx,
    diff_x_cols=get_diff_x_cols_rx,
    author=authors_widget,
    resample_rate='ME',
    agg_func=agg_func_widget,
)
# computation based o dependent data, part 1
add_pm_count_perc_rx = pn.rx(add_pm_count_perc)(
    resampled_df=resample_timeline_rx,
    pm_count_cols=get_pm_count_cols_rx,
)
add_split_localtime_rx = pn.rx(add_split_localtime)(
    timeline_df=get_timeline_df_rx,
)
# dependent data, part 2
tf_timeline_df_author_rx = pn.rx(tf_timeline_df_author)(
    tf_timeline_df=get_timeline_df_rx,
    author=authors_widget,
)
# NOTE: alternative would be to add localtime after selecting author
timeline_df_author_localtime_rx = pn.rx(tf_timeline_df_author)(
    tf_timeline_df=add_split_localtime_rx,
    author=authors_widget,
)

# ...........................................................................
# plots
# plot that depends on the reactive data, part 1, defined above, i.e. `resample_timeline_rx`
plot_counts_rx = pn.rx(plot_counts)(
    resampled_df=resample_timeline_rx,
    repo_desc=repos_widget,
    author_desc=authors_widget,
    frequency_names_map=frequency_names,
    resample_rate=resample_rule_widget,
    agg_func=agg_func_widget,
    figsize=(5, 5),
)

# plot that depends on the reactive data, part 1, defined earlier, i.e. `resample_timeline_rx`
plot_commits_rx = pn.rx(plot_commits)(
    resampled_df=resample_timeline_rx,
    repo_desc=repos_widget,
    author_desc=authors_widget,
    frequency_names_map=frequency_names,
    resample_rate=resample_rule_widget, # 'n_commits' is excluded from selecting `agg_func`
    figsize=(12, 5),
)

# plot that depends on the special case of reactive data, part 1, defined earlier, i.e. `resample_timeline_ME_rx`
plot_heatmap_rx = pn.rx(plot_heatmap)(
    resampled_df=resample_timeline_ME_rx,
    repo_desc=repos_widget,
    author_desc=authors_widget,
    frequency_names_map=frequency_names,
    resample_rate='ME',
    agg_func=agg_func_widget,
    # figsize left at its default values
)

plot_periodicity_heatmap_rx = pn.rx(plot_periodicity_heatmap)(
    timeline_df_author=timeline_df_author_localtime_rx,
    width  = 800,  # 600
    height = 380,  # 250
    off_size = 150,  # 125
)

# plot that depends on the reactive data, part 2, defined earlier, i.e. `tf_timeline_df_author_rx`
bihist_pm_df_rx = pn.rx(bihist_pm_df)(
    df=tf_timeline_df_author_rx,
    # column_fmt: str = '{pm}:count', color_plus: str = 'g', color_minus:str = 'r',  # left at default values
    # agg_func: Optional[str] = None,  # not for this plot
    bin_width=bin_width_widget.param.value_throttled,
    max_value=max_value_widget.param.value_throttled,
    figsize=(5, 5),
    # figsize: Optional[tuple[float, float]] = None, # left at default values
    title=pn.rx('Histogram of changed lines per commit by {author} in {repo} repository').format(
        repo=repos_widget, author=authors_widget
    ),
)

# plot that depends on the reactive data, part 1, defined earlier, i.e. `resample_timeline_rx`
bihist_pm_df_resampled_rx = pn.rx(bihist_pm_df)(
    df=resample_timeline_rx,
    # column_fmt: str = '{pm}:count', color_plus: str = 'g', color_minus:str = 'r',  # left at default values
    agg_func=agg_func_widget,  # used for axis label
    bin_width=bin_width_widget.param.value_throttled,
    max_value=max_value_widget.param.value_throttled,
    # figsize: Optional[tuple[float, float]] = None,  # left at default values
    title=pn.rx('{repo}, per "{resample_rate}", author={author}').format(
        repo=repos_widget, author=authors_widget, resample_rate=resample_rule_widget,
    ),
)

# plot that depends on the reactive data, part 1, defined earlier, i.e. `resample_timeline_rx`
plot_pm_col_rx = pn.rx(plot_pm_col)(
    # pn.rx reactive components, choose one for `resampled_df`
    resampled_df=add_pm_count_perc_rx,  # either / or
    #resampled_df=resample_timeline_rx,  # either / or
    # widgets
    repo_desc=repos_widget,
    author_desc=authors_widget,
    column_base=column_base_widget,
    resample_rate=resample_rule_widget,
    agg_func=agg_func_widget,
    rescale=autoscale_widget,
    # figsize = (5, 5),  # left at default values
)

plot_diff_3sizes_rx = pn.rx(plot_diff_3sizes)(
    resampled_df=resample_timeline_rx,
    # new widget
    rescale_n_mod=True,
    # set value
    drop_yaxis=False,
    # standard widgets
    repo_desc=repos_widget,
    author_desc=authors_widget,
    resample_rate=resample_rule_widget,
    agg_func=agg_func_widget,
    #figsize=(5, 5),  # left at default values
)


# ---------------------------------------------------------------------------
# helper functions
def mpl_card(fig: Figure, header: str) -> pn.Card:
    return pn.Card(
        pn.pane.Matplotlib(
            fig,
            tight=True,
            format=plot_format.rx(),
            fixed_aspect=False,
            sizing_mode='fixed',
            width= 500,
            height=500,
            styles={
                "margin-left":  "auto",
                "margin-right": "auto",
            },
        ),
        collapsible=False,
        header=header,
    )


# ---------------------------------------------------------------------------
# page URL

# TODO: reduce code duplication with 'apps/contributors.py'
# handle URL params
def onload_update_query_args():
    #onload_callback()
    pn.state.location.update_query(
        repo=path_to_name(repos_widget.value),
        author=authors_widget.value,
    )


def select_file_widget_watcher(*events):
    for event in events:
        if event.name == 'value':
            pn.state.location.update_query(
                repo=path_to_name(event.new),
            )


if pn.state.location:
    # NOTE: we cannot use the following commented out line, as it would use whole path
    #pn.state.location.sync(repos_widget, {'value': 'repo'})
    # TODO: reduce code duplication with 'app/contributors.py' (currently different widget reference)
    pn.state.onload(
        onload_update_query_args
    )
    select_file_widget.param.watch(
        select_file_widget_watcher,
        ['value'],
        onlychanged=True,
    )
    repo_arg = pn.state.session_args.get("repo", [b""])[0].decode()
    if repo_arg in select_file_widget.options:
        # TODO: add logging
        select_file_widget.param.update(
            value=select_file_widget.options[repo_arg],
        )

    pn.state.location.sync(authors_widget, {'value': 'author'})
    pn.state.location.sync(resample_rule_widget, {'value': 'freq'})
    pn.state.location.sync(agg_func_widget, {'value': 'agg_func'})
    pn.state.location.sync(column_base_widget, {'value': 'column'})
    pn.state.location.sync(autoscale_widget, {'value': 'autoscale'})

# ---------------------------------------------------------------------------
# main app
head_styles = {
    'font-size': 'larger',
}
head_text_rx = pn.rx(page_info_html)(
    repo_name=repos_widget,
    author_desc=authors_widget,
    resample_freq=resample_rule_widget,
    frequency_names_map=frequency_names,
)

sankey_mermaid = MermaidSankeyPlot(
    dataset_dir=dataset_dir,
    timeseries_file=select_file_widget,
    timeline_df=get_timeline_df_rx,
    author_column=author_column,
    author=authors_widget,
)

template = pn.template.MaterialTemplate(
    site="PatchScope",
    title="Author Statistics",
    favicon="favicon-author.svg",
    sidebar_width=350,
    collapsed_sidebar=True,
    sidebar=[
        select_file_widget,
        repos_widget,  # disabled, and UNBOUND!
        authors_widget,      # either / or
        #authors_radio_box,  # either / or
        resample_rule_widget,
        agg_func_widget,
        #n_mod_widget,   # composite: switch + descriptions
        #pm_col_widget,  # composite: select + checkbox
        hist_widget,    # composite: two sliders
        pn.WidgetBox(
            'Sankey flow diagram',
            *sankey_mermaid.widgets(),
            disabled=False
        ),
        ClearCacheButton(),
        pn.layout.VSpacer(),
        #pn.Spacer(height=100),
        plot_sizing_mode,
        plot_format,
    ],
    main=[
        pn.FlexBox(
            pn.pane.HTML(head_text_rx, styles=head_styles),
            pn.Card(
                pn.pane.Matplotlib(
                    plot_commits_rx,
                    tight=True,
                    format=plot_format.rx(),
                    sizing_mode='stretch_width',
                    # start of different values of parameters than mpl_card()
                    fixed_aspect=True,
                    #width =1000,
                    height= 500,
                    # end of different parameters
                    styles={
                        "margin-left":  "auto",
                        "margin-right": "auto",
                    },
                ),
                collapsible=False,
                header="commit counts",
            ),
            pn.layout.FlexBox(
                # layout plots side by side, if they fit
                mpl_card(plot_counts_rx, "line counts"),
                mpl_card(bihist_pm_df_rx, "histogram of -/+ counts per commit"),
                align_content='space-evenly',
                justify_content='space-evenly',
                flex_direction='row',
                flex_wrap='nowrap',  # NOTE: without this it always wraps into column
            ),
            pn.Card(
                pn.pane.Matplotlib(
                    plot_heatmap_rx,
                    tight=True,
                    format=plot_format.rx(),
                    sizing_mode='stretch_width',
                    #sizing_mode='fixed',
                    fixed_aspect=True,
                    #width =1000,  # for sizing_mode='fixed'
                    height= 500,
                    # end of different parameters
                    styles={
                        "margin-left":  "auto",
                        "margin-right": "auto",
                    },
                    margin=10,
                ),
                collapsible=False,
                header="heatmap: line-types",
            ),
            pn.Card(
                sankey_mermaid,
                styles={
                    "margin-left":  "auto",
                    "margin-right": "auto",
                },
                sizing_mode="scale_both",
                collapsible=False,
                header="Sankey flow diagram: distribution of changes by directory and by line-type",
            ),
            pn.Card(
                # plot_periodicity_heatmap_rx,
                pn.pane.HoloViews(
                    plot_periodicity_heatmap_rx,
                    # sizes similar to the other heatmap
                    sizing_mode='stretch_width',
                    #sizing_mode='fixed',
                    #width =1000,
                    height= 600,
                    # end of different parameters
                    styles={
                        "margin-left":  "auto",
                        "margin-right": "auto",
                    },
                ),
                collapsible=False,
                header="periodic behavior, local time",
            )
        ),
    ],
)

template.servable()

if __name__ == "__main__":
    # Optionally run the application in a development server
    pn.serve(template, show=True)

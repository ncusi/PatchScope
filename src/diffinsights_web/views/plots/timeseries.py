from typing import Optional

import pandas as pd
import panel as pn
import param
import hvplot.pandas  # noqa

from diffinsights_web.utils.notifications import warning_notification
from diffinsights_web.views import TimelineView


@pn.cache
def get_date_range(timeline_df: pd.DataFrame, from_date_str: str):
    # TODO: create reactive component or bound function to compute from_date to avoid recalculations
    # TODO: use parsed `from_date` instead of using raw `from_date_str`
    min_date = timeline_df['author_date'].min()
    if from_date_str:
        from_date = pd.to_datetime(from_date_str, dayfirst=True, utc=True)
        min_date = max(min_date, from_date)

    ## DEBUG
    #print(f"get_date_range(timeline_df=<{hex(id(timeline_df))}, {from_date_str=}>):")
    #print(f"  {min_date=}, {timeline_df['author_date'].max()=}")

    return (
        min_date,
        timeline_df['author_date'].max(),
    )


# NOTE: consider putting the filter earlier in the pipeline (needs profiling / benchmarking?)
# TODO: replace `from_date_str` (raw string) with `from_date` (parsed value)
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


def plot_commits(resampled_df: pd.DataFrame,
                 column: str = 'n_commits',
                 from_date_str: str = '',
                 xlim: Optional[tuple] = None,
                 ylim: Optional[tuple] = None,
                 kind: str = 'step'):
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

    # special cases: y range limits
    if column == "KIND [%]":
        ylim = (0.0, 1.05)

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

    # special cases: the plot itself
    if column == "KIND [%]":
        kind_perc_columns = [
            col for col in resampled_df.columns
            if col.startswith('+:type.') and col.endswith(' [%]')
        ]
        if not kind_perc_columns:
            warning_notification("No columns found for 'KIND [%]' plot")
            kind_perc_columns = '+:count'  # fallback
            ylim = (-1, None)

        if kind not in {'bar', 'area'}:  # plots that support `stacked=True`
            kind = 'area'
        if kind == 'area':  # 'hover' for area plot with hvplot (bokeh backend) is useless
            tools = [
                'xpan',
                'box_zoom',
                'save',
                'reset',
            ]
        else:
            tools = [
                'xpan',
                'box_zoom',
                'save',
                'reset',
                'hover',
            ]
        # NOTE: somehow the area plot has 'wheel_zoom' and 'hover' tools anyway

        plot = filtered_df.hvplot(
            x='author_date',
            y=kind_perc_columns,
            kind=kind,
            stacked=True,  # cumulative plot, should stack to 1.0 (to 100.0 %)
            legend='bottom',
            responsive=True,
            hover='vline',
            grid=True,
            xlim=xlim, xlabel='',
            ylim=ylim, ylabel='Line types [%]',
            padding=(0.005, 0),
            tools=tools,
            # start testing
            #interpolation='steps-mid',  # interpolation option not found for area plot with bokeh
            #drawstyle='steps-mid',  # drawstyle option not found for area plot with boke
            #step='mid',  # step option not found for area plot with bokeh
            # https://hvplot.holoviz.org/user_guide/Pandas_API.html#colormaps
            # - shows `colormap` option for 'line', 'bar', and some line based plots
            # https://pandas.pydata.org/docs/user_guide/visualization.html#colormaps
            # https://matplotlib.org/stable/gallery/color/colormap_reference.html
            colormap='Greens',  # ignored for 'area' plots?
            # end testing
            **hvplot_kwargs,
        )
        if kind == 'area':
            plot.opts(active_tools=['xpan'])
        else:
            plot.opts(active_tools=['hover'])

    else:
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
                'save',
                'reset',
                'hover',
            ],
            **hvplot_kwargs,
        )
    # manually specifying the default tools gets rid of any preset default tools
    # you also just use an empty list here to use only chosen tools
    plot.opts(default_tools=[], responsive=True, toolbar='above')
    # MAYBE: backend_opts={"plot.toolbar.autohide": True}

    return plot


class TimeseriesPlot(TimelineView):
    # allow_refs=True is here to allow widgets
    column_name = param.String(allow_refs=True)
    from_date_str = param.String(allow_refs=True)

    def __init__(self, **params):
        super().__init__(**params)

        self.plot_commits_rx = pn.rx(plot_commits)(
            resampled_df=self.data_store.resampled_timeline_all_rx,
            column=self.param.column_name.rx(),
            from_date_str=self.param.from_date_str.rx(),
        )
        # output: ranges
        self.date_range_rx = pn.rx(get_date_range)(
            timeline_df=self.data_store.timeline_df_rx,
            from_date_str=self.param.from_date_str.rx(),
        )

        self.select_plot_theme_widget = pn.widgets.Select(
            name="Plot theme:",
            # see https://docs.bokeh.org/en/latest/docs/reference/themes.html
            options=[
                'caliber',
                'carbon',
                'dark_minimal',
                'light_minimal',
                'night_sky',
                'contrast',
            ],
        )

    def __panel__(self) -> pn.viewable.Viewable:
        return pn.Card(
            pn.Column(
                #pn.pane.HTML(sampling_info_rx, styles=head_styles),
                pn.pane.HoloViews(self.plot_commits_rx, theme=self.select_plot_theme_widget)
            ),
            collapsible=False, hide_header=True,
        )

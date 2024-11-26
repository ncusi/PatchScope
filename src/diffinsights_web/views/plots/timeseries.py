from enum import Enum
from typing import Optional

import pandas as pd
import panel as pn
import param
import hvplot.pandas  # noqa

from diffinsights_web.datastore.timeline import \
    get_date_range, get_value_range, filter_df_by_from_date, authors_info_df, author_timeline_df_freq
from diffinsights_web.utils.notifications import warning_notification
from diffinsights_web.views import TimelineView


class SpecialColumnEnum(Enum):
    LINE_TYPES_PERC = "KIND [%]"
    NO_PLOT = "<NO PLOT>"


def line_type_sorting_key(column_name: str) -> int:
    if 'type.code' in column_name:
        return 1
    elif 'type.documentation' in column_name:
        return 2
    elif 'type.test' in column_name:
        return 3
    elif 'type.data' in column_name:
        return 4
    elif 'type.markup' in column_name:
        return 5
    elif 'type.other' in column_name:
        return 99
    else:
        return 10


def plot_commits(resampled_df: pd.DataFrame,
                 column: str = 'n_commits',
                 from_date_str: str = '',
                 xlim: Optional[tuple] = None,
                 ylim: Optional[tuple] = None,
                 kind: str = 'step'):
    # super special case
    if column == SpecialColumnEnum.NO_PLOT.value:
        return

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
    if column == SpecialColumnEnum.LINE_TYPES_PERC.value:
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
    if column == SpecialColumnEnum.LINE_TYPES_PERC.value:
        kind_perc_columns = [
            col for col in resampled_df.columns
            if col.startswith('type.') and col.endswith(' [%]')
        ]
        kind_perc_columns.sort(key=line_type_sorting_key)
        if not kind_perc_columns:
            warning_notification("No columns found for 'KIND [%]' plot")
            kind_perc_columns = '+:count'  # fallback
            ylim = (-1, None)

        # no support for mapping from column name to color; single color or list
        # https://hvplot.holoviz.org/user_guide/Customization.html (color : str or array-like)

        # based on https://sashamaps.net/docs/resources/20-colors/
        kind_perc_colors = [
            '#4363d8',  # type.code - blue used for keyword in syntax highlighting
            '#9A6324',  # type.documentation - brown
            # alternatives: grey for comments, green for strings, violet for Markown header
            '#3cb44b',  # type.test - green
            '#ffe119',  # type.data - yellow
            '#800000',  # type.markup - maroon
            '#a9a9a9',  # type.other - grey
            # reserve
            '#e6194B',  # red
            '#f58231',  # orange
            '#911eb4',  # purple
            '#42d4f4',  # cyan
            '#f032e6',  # magenta
            '#bfef45',  # lime
            # ...
        ]

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
            color=kind_perc_colors,
            kind=kind,
            stacked=True,  # cumulative plot, should stack to 1.0 (to 100.0 %)
            legend='bottom',
            responsive=True,
            hover='vline',
            grid=True,  # hidden under cumulative stacked plot
            xlim=xlim, xlabel='',
            ylim=ylim, ylabel='Line types [%]',
            #clabel='Line types (kinds)',  # NOTE: does not work for legend title
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
            #colormap='Greens',  # ignored for 'area' plots?
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
        self.value_range_rx = pn.rx(get_value_range)(
            timeline_df=self.data_store.resampled_timeline_all_rx,
            column=self.param.column_name.rx(),
        )

        # authors info for authors grid selection
        self.authors_info_df_rx = pn.rx(authors_info_df)(
            timeline_df=self.data_store.timeline_df_rx,
            column=self.param.column_name.rx(),
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
        if self.column_name == SpecialColumnEnum.NO_PLOT.value:
            return pn.Spacer(height=0)

        return pn.pane.HoloViews(
            self.plot_commits_rx,
            theme=self.select_plot_theme_widget,
            # sizing configuration
            height=350,  # TODO: find a better way than fixed height
            sizing_mode='stretch_width',
        )


class TimeseriesPlotForAuthor(TimelineView):
    main_plot = param.ClassSelector(class_=TimeseriesPlot)
    author_email = param.String()

    def __init__(self, **params):
        #print("TimeseriesPlotForAuthor.__init__()")
        super().__init__(**params)

        self.resampled_df_rx = pn.rx(author_timeline_df_freq)(
            resample_by_author_df=self.main_plot.data_store.resampled_timeline_by_author_rx,
            author_id=self.author_email,
            resample_rate=self.data_store.resample_frequency_widget,
        )

        self.plot_commits_rx = pn.rx(plot_commits)(
            resampled_df=self.resampled_df_rx,
            column=self.main_plot.param.column_name.rx(),
            from_date_str=self.main_plot.param.from_date_str.rx(),
            xlim=self.main_plot.date_range_rx,
            ylim=self.main_plot.value_range_rx,  # TODO: allow to switch between totals, max N, and own
        )

    def __panel__(self) -> pn.viewable.Viewable:
        #print("TimeseriesPlotForAuthor.__panel__()")
        if self.main_plot.column_name == SpecialColumnEnum.NO_PLOT.value:
            return pn.Spacer(height=0)

        return pn.pane.HoloViews(
            self.plot_commits_rx,
            theme=self.main_plot.select_plot_theme_widget,
            # sizing configuration
            height=256,  # TODO: find a better way than fixed height
            sizing_mode='stretch_width',
            # sizing_mode='scale_both',  # NOTE: does not work, and neither does 'stretch_both'
            # aspect_ratio=1.5,  # NOTE: does not help to use 'scale_both'/'stretch_both'
            margin=5,
        )

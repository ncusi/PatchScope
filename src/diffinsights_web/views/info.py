import datetime
from collections import Counter
from typing import Optional

import pandas as pd
import panel as pn
import param
from dateutil.relativedelta import relativedelta

from diffinsights_web.datastore.timeline import frequency_names, filter_df_by_from_date, get_pm_count_cols
from diffinsights_web.utils.humanize import html_date_humane
from diffinsights_web.views import TimelineView, contribution_types_map, column_to_contribution, SpecialColumnEnum
from diffinsights_web.views.plots.timeseries import TimeseriesPlot


# common for all classes defined here
head_styles = {
    'font-size': 'larger',
}

#: for the ContributorsHeader.select_period_from_widget
time_range_period = {
    'All': None,
    'Last month': 1,
    'Last 3 months': 3,
    'Last 6 months': 6,
    'Last 12 months': 12,
    'Last 24 months': 24,
}


def time_range_options(end_date: Optional[datetime.date] = None) -> dict[str, str]:
    #print(f"time_range_options({end_date=})")
    if end_date is None:
        end_date = datetime.date.today()

    return {
        k: '' if v is None else (end_date + relativedelta(months=-v)).strftime('%Y.%m.%d')
        for k, v in time_range_period.items()
    }


@pn.cache
def head_info_html(repo_name: str,
                   resample_freq: str,
                   freq_names: dict[str, str]) -> str:
    return f"""
    <h1>Contributors to {repo_name}</h1>
    <p>Contributions per {freq_names.get(resample_freq, 'unknown frequency')} to HEAD, excluding merge commits</p>
    """


class ContributorsHeader(pn.viewable.Viewer):
    repo = param.String(
        allow_refs=True,  # allow for reactive expressions, and widgets
        doc="Name of the repository, for documentation purposes only",
    )
    freq = param.String(
        allow_refs=True,  # allow for reactive expressions, and widgets
        doc="Resampling frequency as frequency string, for documentation purposes only",
        # see table at https://pandas.pydata.org/docs/user_guide/timeseries.html#dateoffset-objects
    )
    end_date = param.ClassSelector(
        default=datetime.datetime.today(),
        class_=datetime.datetime,
        allow_refs=True,  # allow for reactive expressions, and widgets
        doc="Date from which to start counting down date periods from",
    )

    widget_top_margin = 20
    widget_gap_size = 5

    def __init__(self, **params):
        super().__init__(**params)

        self.head_text_rx = pn.rx(head_info_html)(
            repo_name=self.param.repo.rx(),
            resample_freq=self.param.freq.rx(),
            freq_names=frequency_names,
        )
        self.select_period_from_widget = pn.widgets.Select(
            name="Period:",
            options={'Any': ''},
            value='Any',
            # style
            width=120,
            margin=(self.widget_top_margin, self.widget_gap_size),
        )
        self.select_period_from_widget.options = time_range_options(
            end_date=self.param.end_date.rx.value,  # otherwise: TypeError: __str__ returned non-string (type rx)
        )
        self.select_period_from_widget.value = ''
        # NOTE: we could have used self.param.watch(..., ['end_date']), see
        # https://param.holoviz.org/user_guide/Dependencies_and_Watchers.html#watchers
        self.param.end_date.rx.watch(self.update_period_selector)

        self.select_contribution_type_widget = pn.widgets.Select(
            name="Contributions:",
            options=contribution_types_map,
            value="timeline|n_commits",  # first value in contribution_types_map
            # NOTE: disabled_options does not seem to work, no disabling (???)
            #       therefore there is no code that does disabling and enabling of this
            #disabled_options=[
            #    SpecialColumnEnum.SANKEY_DIAGRAM.value,  # need <name>.lines-stats.purpose-to-type.json
            #],
            # style
            width=200,
            margin=(self.widget_top_margin, 0),  # last widget, use x margin of 0
        )
        #print(f"{self.select_contribution_type_widget.value=}")
        #print(f"{self.select_contribution_type_widget.options=}")
        #print(f"{self.select_contribution_type_widget.disabled_options=}")

    def update_period_selector(self, new_value: datetime.datetime) -> None:
        #print(f"ContributorsHeader.update_period_from_selector({new_value=})")
        with param.parameterized.batch_call_watchers(self.select_period_from_widget):
            self.select_period_from_widget.options = time_range_options(end_date=new_value)
            if self.select_period_from_widget.value not in self.select_period_from_widget.options:
                self.select_period_from_widget.value = ''

    def __panel__(self):
        return pn.Row(
            pn.pane.HTML(self.head_text_rx, styles=head_styles),
            self.select_period_from_widget,
            self.select_contribution_type_widget,
        )


def sampling_info(resample_freq: str,
                  column: str,
                  frequency_names_map: dict[str, str],
                  min_max_date) -> str:
    plot_type = "timeline"
    if '|' in column:
        plot_type, _ = column.split('|', maxsplit=2)

    if plot_type == "sankey":
        # Sankey diagrams do not use resampling
        return f"""
        <p><strong>Distribution of changed lines types based on the directory structure</strong></p>
        <p><s>Using commits
        from {html_date_humane(min_max_date[0])}
        to {html_date_humane(min_max_date[1])}
        </s></p>
        """

    elif plot_type != "timeline":
        print(f"sampling_info(): expected plot_type of 'timeline', got {plot_type=}")
        return f"No support for <strong>{plot_type}</strong> plot type, for plotting <em>{column!r}</em>"

    #print(f"sampling_info({resample_freq=}, ...): {column=}, {column_to_contribution.keys()}")
    contribution_type = column_to_contribution.get(column, "Unknown type of contribution")

    return f"""
    <strong>{contribution_type}{' over time' if column != SpecialColumnEnum.NO_PLOT.value else ''}</strong>
    <p>
    {frequency_names_map.get(resample_freq, 'unknown frequency').title()}ly
    from {html_date_humane(min_max_date[0])}
    to {html_date_humane(min_max_date[1])}
    </p>
    """


class RepoPlotHeader(pn.viewable.Viewer):
    freq = param.String(
        allow_refs=True,  # allow for reactive expressions, and widgets
        doc="Resampling frequency as frequency string, for documentation purposes only",
        # see table at https://pandas.pydata.org/docs/user_guide/timeseries.html#dateoffset-objects
    )
    # allow_refs=True is here to allow widgets
    column_name = param.String(
        allow_refs=True,  # allow for reactive expressions, and widgets
        doc="Contribution type as value: column name in DataFrame, or special name",
    )
    plot = param.ClassSelector(class_=TimeseriesPlot)

    def __init__(self, **params):
        super().__init__(**params)

        self.sampling_info_rx = pn.rx(sampling_info)(
            resample_freq=self.param.freq.rx(),
            column=self.param.column_name.rx(),
            frequency_names_map=frequency_names,
            min_max_date=self.plot.date_range_rx,
        )

    def __panel__(self):
        return pn.pane.HTML(
            self.sampling_info_rx,
            styles=head_styles
        )


def contributions_perc_info(timeline_df: pd.DataFrame,
                            from_date_str: str,
                            author_id: Optional[str] = None,
                            show_descr: bool = False):
    types = [
        'code',
        'documentation',
        'test',
        'data',
        'markup',
        'other'
    ]
    css = """
    .bar-container {
        width: 100%;
        height: 8px;
        border-radius: 6px;
        border: 1px solid;
        display: flex;
    }
    .bar {
        height: 6px;
        display: block;
        outline: 2px solid #0000;
        padding: 1px 0px;
    }
    .bar-code { background-color: #4363d8; }
    .bar-documentation { background-color: #9A6324; }
    .bar-test { background-color: #3cb44b; }
    .bar-data { background-color: #ffe119; }
    .bar-markup { background-color: #800000; }
    .bar-other { background-color: #a9a9a9; }
    .svg-code { fill: #4363d8; }
    .svg-documentation { fill: #9A6324; }
    .svg-test { fill: #3cb44b; }
    .svg-data { fill: #ffe119; }
    .svg-markup { fill: #800000; }
    .svg-other { fill: #a9a9a9; }
    ul.horizontal {
        list-style: none !important;
        display: flex;
        flex-wrap: wrap;
        margin-left: 0px;
        padding-left: 0rem;
    }
    ul.horizontal li {
        display: inline-flex;
        padding-right: 1rem;
    }
    """
    filtered_df = filter_df_by_from_date(timeline_df, from_date_str,
                                         date_column='author.timestamp')
    if author_id is not None:
        filtered_df = filtered_df[filtered_df['author.email'] == author_id]

    pm_count_cols = get_pm_count_cols(timeline_df)
    pm_count_sum = filtered_df[pm_count_cols].sum().to_dict()

    line_kind_sum = Counter()
    for line_kind in types:
        for pm in list("-+"):
            col_name = f"{pm}:type.{line_kind}"
            if col_name in pm_count_sum:
                line_kind_sum[line_kind] += pm_count_sum[col_name]
            else:
                line_kind_sum[line_kind] += 0

    # NOTE: could be used as alternative way of computing
    for col_name, col_sum in pm_count_sum.items():
        line_kind = col_name[len("+:type."):]
        if line_kind in types:
            continue  # already counted

        # catch every line type not in `types` into "other" category
        if col_name.startswith('-:type.') or col_name.startswith('+:type.'):
            line_kind_sum["other"] += col_sum

    total_lines = 0
    for pm in list("-+"):
        if f"{pm}:count" in pm_count_sum:
            total_lines += pm_count_sum[f"{pm}:count"]

    html_parts = ['<div class="bar-container">']
    for line_kind in types:
        val_perc = 100.0*line_kind_sum[line_kind]/total_lines
        html_parts.append(
            f'<span class="bar bar-{line_kind}"'
            f' style="width: {val_perc:.1f}%;" title="{line_kind}: {val_perc:.1f}%"></span>'
        )
    html_parts.append('</div>')

    if show_descr:
        html_parts.append('<ul class="horizontal">')
        for line_kind in types:
            val_perc = 100.0 * line_kind_sum[line_kind] / total_lines
            html_parts.append(
                '<li>'
                f'<svg class="svg-{line_kind}" aria-hidden="true"'
                ' width="16" height="16" viewBox="0 0 16 16" version="1.1">'
                '<circle cx="8" cy="8" r="4" />'
                '</svg>'
                f'{line_kind}:&nbsp;{val_perc:.1f}%'
                '</li>'
            )
        html_parts.append('</ul>')

    return pn.pane.HTML(
        '\n'.join(html_parts),
        stylesheets=[css],
        #sizing_mode='stretch_width',
    )


class ContributionsPercHeader(TimelineView):
    author_id = param.String(None)
    from_date_str = param.String(allow_refs=True)  # allow_refs=True is here to allow widgets
    show_descr = param.Boolean(True)

    def __init__(self, **params):
        super().__init__(**params)

        # TODO: fix the bug with the output not updating on updated `from_date_str` widget
        self.contributions_perc_info_rx = pn.rx(contributions_perc_info)(
            timeline_df=self.data_store.timeline_df_rx,
            from_date_str=self.param.from_date_str.rx(),
            author_id=self.author_id,
            show_descr=self.show_descr,
        )

    def __panel__(self) -> pn.viewable.Viewable:
        return self.contributions_perc_info_rx.rx.value

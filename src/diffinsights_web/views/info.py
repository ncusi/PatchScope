import datetime
from collections import Counter
from typing import Optional

import pandas as pd
import panel as pn
import param
from dateutil.relativedelta import relativedelta

from diffinsights_web.datastore.timeline import frequency_names, filter_df_by_from_date, get_pm_count_cols
from diffinsights_web.utils.humanize import html_date_humane
from diffinsights_web.views import TimelineView
from diffinsights_web.views.plots.timeseries import SpecialColumnEnum, TimeseriesPlot


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


def time_range_options() -> dict[str, str]:
    today = datetime.date.today()

    return {
        k: '' if v is None else (today + relativedelta(months=-v)).strftime('%d.%m.%Y')
        for k, v in time_range_period.items()
    }


#: for the ContributorsHeader.select_contribution_type_widget
contribution_types_map = {
    "Commits": "n_commits",
    "Additions": "+:count",
    "Deletions": "-:count",
    "Files changed": "file_names",
    "Patch size (lines)": "diff.patch_size",
    "Patch spreading (lines)": "diff.groups_spread",
    # special cases:
    "Line types distribution [%]": SpecialColumnEnum.LINE_TYPES_PERC.value,
    "No plot": SpecialColumnEnum.NO_PLOT.value  # this special value should be last
}
column_to_contribution = {
    v: k for k, v in contribution_types_map.items()
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
        self.select_period_from_widget.options = time_range_options()
        self.select_period_from_widget.value = ''

        self.select_contribution_type_widget = pn.widgets.Select(
            name="Contributions:",
            options=contribution_types_map,
            value="n_commits",
            # style
            width=200,
            margin=(self.widget_top_margin, 0),  # last widget, use x margin of 0
        )

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
                            author_id: Optional[str] = None):
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
    ul.horizontal {
        list-style: none !important;
        display: flex;
        margin-left: 0px;
        padding-left: 2rem;
    }
    """
    filtered_df = filter_df_by_from_date(timeline_df, from_date_str)
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

    return pn.pane.HTML(
        '\n'.join(html_parts),
        stylesheets=[css],
        sizing_mode='stretch_width',
    )


class ContributionsPercHeader(TimelineView):
    author_id = param.String(None)
    from_date_str = param.String(allow_refs=True)  # allow_refs=True is here to allow widgets

    def __init__(self, **params):
        super().__init__(**params)

        # TODO: fix the bug with the output not updating on updated `from_date_str` widget
        self.contributions_perc_info_rx = pn.rx(contributions_perc_info)(
            timeline_df=self.data_store.timeline_df_rx,
            from_date_str=self.param.from_date_str.rx(),
            author_id=self.author_id,
        )

    def __panel__(self) -> pn.viewable.Viewable:
        return self.contributions_perc_info_rx.rx.value

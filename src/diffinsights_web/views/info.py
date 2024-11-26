import datetime

import panel as pn
import param
from dateutil.relativedelta import relativedelta

from diffinsights_web.datastore.timeline import frequency_names
from diffinsights_web.utils.humanize import html_date_humane
from diffinsights_web.views.plots.timeseries import SpecialColumn, TimeseriesPlot


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
    "Line types distribution [%]": SpecialColumn.LINE_TYPES_PERC.value,
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
    <strong>{contribution_type} over time</strong>
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

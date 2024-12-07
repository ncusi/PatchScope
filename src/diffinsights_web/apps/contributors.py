#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

import panel as pn

import diffinsights_web.utils.notifications as notifications
from diffinsights_web.datastore.timeline import TimelineDataStore
from diffinsights_web.datastore import find_dataset_dir
from diffinsights_web.utils.notifications import onload_callback
from diffinsights_web.views.authorsgrid import AuthorInfo, AuthorsGrid
from diffinsights_web.views.dataexplorer import TimelineJSONViewer, TimelinePerspective, \
    TimelineDataFrameEnum, perspective_pane
from diffinsights_web.views.info import ContributorsHeader, RepoPlotHeader, ContributionsPercHeader
from diffinsights_web.views.plots.timeseries import TimeseriesPlot
from diffinsights_web.widgets.caching import ClearCacheButton


logger = logging.getLogger("panel.contributors_graph")
pn.extension(
    "jsoneditor", "perspective",
    notifications=True,
    design="material", sizing_mode="stretch_width"
)
pn.state.notifications.position = 'top-center'

notifications.loaded = False  # module is not re-imported on reloading
pn.state.onload(onload_callback)

dataset_dir = find_dataset_dir()
data_store = TimelineDataStore(dataset_dir=dataset_dir)

page_header = ContributorsHeader(
    repo=data_store.select_repo_widget,
    freq=data_store.resample_frequency_widget,
    end_date=data_store.timeline_max_date_rx,
)
timeseries_plot = TimeseriesPlot(
    data_store=data_store,
    column_name=page_header.select_contribution_type_widget,
    from_date_str=page_header.select_period_from_widget,
)
timeseries_plot_header = RepoPlotHeader(
    freq=data_store.resample_frequency_widget,
    column_name=page_header.select_contribution_type_widget,
    plot=timeseries_plot,
)
contributions_perc_header = ContributionsPercHeader(
    data_store=data_store,
    from_date_str=page_header.select_period_from_widget,
)
authors_info_panel = AuthorInfo(
    data_store=data_store,
    authors_info_df=timeseries_plot.authors_info_df_rx,
)
authors_grid = AuthorsGrid(
    data_store=data_store,
    main_plot=timeseries_plot,
    authors_info_df=timeseries_plot.authors_info_df_rx,
    top_n=authors_info_panel.top_n_widget,
)

# Create the dashboard layout
template = pn.template.MaterialTemplate(
    site="PatchScope",
    title="Contributors Graph",  # TODO: make title dynamic
    favicon="favicon.svg",
    sidebar=[
        data_store,
        *authors_info_panel.widgets(),

        pn.layout.Divider(),  # - - - - - - - - - - - - -

        timeseries_plot.select_plot_theme_widget,
        ClearCacheButton(),
    ],
    main=[
        pn.Column(
            page_header,
        ),
        pn.Card(
            pn.Column(
                timeseries_plot_header,
                contributions_perc_header,
                timeseries_plot,
            ),
            collapsible=False, hide_header=True,
        ),
        authors_grid,
    ],
)
timeline_perspective = TimelinePerspective(data_store=data_store)
template.main.extend([
    pn.layout.Divider(),
    pn.Tabs(
        ('JSON', TimelineJSONViewer(data_store=data_store)),
        ('data', timeline_perspective.panel(TimelineDataFrameEnum.TIMELINE_DATA)),
        ('resampled', timeline_perspective.panel(TimelineDataFrameEnum.RESAMPLED_DATA)),
        ('by author+resampled', timeline_perspective.panel(TimelineDataFrameEnum.BY_AUTHOR_DATA)),
        (
            'authors info',
            perspective_pane(
                df=timeseries_plot.authors_info_df_rx,
                title=pn.rx("Authors info for repo={repo!r}, from={from_date!r}") \
                    .format(repo=data_store.select_repo_widget,
                            from_date=page_header.select_period_from_widget)
            )
        ),
        ('selected author', authors_info_panel),
    ),
])

# Serve the dashboard
template.servable()

if __name__ == "__main__":
    # Optionally run the application in a development server
    pn.serve(template, show=True)

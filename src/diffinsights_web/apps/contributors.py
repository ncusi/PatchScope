#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from pathlib import Path

import panel as pn

import diffinsights_web.utils.notifications as notifications
from diffinsights_web.datastore.timeline import TimelineDataStore, path_to_name
from diffinsights_web.datastore import find_dataset_dir
from diffinsights_web.utils.notifications import onload_callback
from diffinsights_web.views.authorsgrid import AuthorInfo, AuthorsGrid
from diffinsights_web.views.info import ContributorsHeader, RepoPlotHeader, ContributionsPercHeader
from diffinsights_web.views.plots.timeseries import TimeseriesPlot
from diffinsights_web.widgets.caching import ClearCacheButton


logger = logging.getLogger("panel.contributors_graph")
pn.extension(
    notifications=True,
    design="material", sizing_mode="stretch_width"
)
pn.state.notifications.position = 'top-center'

notifications.loaded = False  # module is not re-imported on reloading
pn.state.onload(onload_callback)

dataset_dir = find_dataset_dir()
timeline_data_store = TimelineDataStore(dataset_dir=dataset_dir)

page_header = ContributorsHeader(
    repo=timeline_data_store.select_repo_widget,
    freq=timeline_data_store.resample_frequency_widget,
    end_date=timeline_data_store.timeline_max_date_rx,
)
timeseries_plot = TimeseriesPlot(
    data_store=timeline_data_store,
    column_name=page_header.select_contribution_type_widget,
    from_date_str=page_header.select_period_from_widget,
)
timeseries_plot_header = RepoPlotHeader(
    freq=timeline_data_store.resample_frequency_widget,
    column_name=page_header.select_contribution_type_widget,
    plot=timeseries_plot,
)
contributions_perc_header = ContributionsPercHeader(
    data_store=timeline_data_store,
    from_date_str=page_header.select_period_from_widget,
)
authors_info_panel = AuthorInfo(
    data_store=timeline_data_store,
    authors_info_df=timeseries_plot.authors_info_df_rx,
)
authors_grid = AuthorsGrid(
    data_store=timeline_data_store,
    main_plot=timeseries_plot,
    authors_info_df=timeseries_plot.authors_info_df_rx,
    top_n=authors_info_panel.top_n_widget,
)


# handle URL params
def onload_update_query_args():
    onload_callback()
    pn.state.location.update_query(
        repo=path_to_name(Path(timeline_data_store.select_file_widget.value))
    )


def select_file_widget_watcher(*events):
    for event in events:
        if event.name == 'value':
            pn.state.location.update_query(
                repo=path_to_name(Path(event.new))
            )


if pn.state.location:
    pn.state.onload(
        onload_update_query_args
    )
    timeline_data_store.select_file_widget.param.watch(
        select_file_widget_watcher,
        ['value'],
        onlychanged=True,
    )
    repo_arg = pn.state.session_args.get("repo", [b""])[0].decode()
    if repo_arg in timeline_data_store.select_file_widget.options:
        # TODO: add logging
        timeline_data_store.select_file_widget.param.update(
            value=timeline_data_store.select_file_widget.options[repo_arg],
        )
        # NOTE: alternative would be to use
        # timeline_data_store.select_file_widget.value = timeline_data_store.select_file_widget.options[repo_arg]

    pn.state.location.sync(timeline_data_store.resample_frequency_widget, {'value': 'freq'})
    pn.state.location.sync(page_header.select_period_from_widget, {'value': 'from'})

# Create the dashboard layout
template = pn.template.MaterialTemplate(
    site="PatchScope",
    title="Contributors Graph",  # TODO: make title dynamic
    favicon="favicon.svg",
    collapsed_sidebar=True,
    sidebar=[
        timeline_data_store,
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

# Serve the dashboard
template.servable()

if __name__ == "__main__":
    # Optionally run the application in a development server
    pn.serve(template, show=True)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import panel as pn

import diffinsights_web.utils.notifications as notifications
from diffinsights_web.datastore.timeline import TimelineDataStore, ResampledTimelineDataStore, find_dataset_dir
from diffinsights_web.utils.notifications import onload_callback
from diffinsights_web.views.dataexplorer import TimelineJSONViewer, TimelinePerspective
from diffinsights_web.widgets.caching import ClearCacheButton


pn.extension(
    "jsoneditor", "perspective",
    notifications=True,
    design="material", sizing_mode="stretch_width"
)
pn.state.notifications.position = 'top-center'

notifications.loaded = False  # module is not re-imported on reloading
pn.state.onload(onload_callback)

dataset_dir = find_dataset_dir()
timeline_data_store = TimelineDataStore(dataset_dir=dataset_dir)
resampled_data_store = ResampledTimelineDataStore(
    data=timeline_data_store.timeline_df_rx,
    repo=timeline_data_store.select_repo_widget,
)
by_author_data_store = ResampledTimelineDataStore(
    data=timeline_data_store.timeline_df_rx,
    repo=timeline_data_store.select_repo_widget,
    group_by='author.email',
)

test_selector = pn.widgets.Select(
    name="test",
    options=["a", "b", "c"],
)

# Create the dashboard layout
template = pn.template.MaterialTemplate(
    site="diffannotator",
    title="Contributors Graph",  # TODO: make title dynamic
    favicon="favicon.svg",
    sidebar=[
        timeline_data_store,
        resampled_data_store,
        by_author_data_store,
        pn.layout.Divider(),
        test_selector,
        test_selector,
        ClearCacheButton(),
    ],
    main=[
        pn.pane.Markdown("# Contributions")
    ],
)
template.main.extend([
    pn.layout.Divider(),
    pn.Tabs(
        ('JSON', TimelineJSONViewer(data_store=timeline_data_store)),
        ('data', TimelinePerspective(data_store=timeline_data_store)),
    ),
])

# Serve the dashboard
template.servable()

if __name__ == "__main__":
    # Optionally run the application in a development server
    pn.serve(template, show=True)

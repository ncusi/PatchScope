#!/usr/bin/env python
# -*- coding: utf-8 -*-
import panel as pn

import diffinsights_web.utils.notifications as notifications
from diffinsights_web.datastore.timeline import TimelineDataStore, find_dataset_dir
from diffinsights_web.utils.notifications import onload_callback
from diffinsights_web.views.dataexplorer import TimelineJSONViewer
from diffinsights_web.widgets.caching import ClearCacheButton

pn.extension(
    "jsoneditor",
    notifications=True,
    design="material", sizing_mode="stretch_width"
)
pn.state.notifications.position = 'top-center'

notifications.loaded = False  # module is not re-imported on reloading
pn.state.onload(onload_callback)

dataset_dir = find_dataset_dir()
data_store = TimelineDataStore(dataset_dir=dataset_dir)

# Create the dashboard layout
template = pn.template.MaterialTemplate(
    site="diffannotator",
    title="Contributors Graph",  # TODO: make title dynamic
    favicon="favicon.svg",
    sidebar=[
        data_store,
        pn.layout.Divider(),
        ClearCacheButton(),
    ],
    main=[
        pn.pane.Markdown("# Contributions")
    ],
)
template.main.extend([
    pn.layout.Divider(),
    TimelineJSONViewer(data_store=data_store),
])

# Serve the dashboard
template.servable()

if __name__ == "__main__":
    # Optionally run the application in a development server
    pn.serve(template, show=True)

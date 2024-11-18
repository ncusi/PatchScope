#!/usr/bin/env python
# -*- coding: utf-8 -*-
import panel as pn

import diffinsights_web.utils.notifications as notifications
from diffinsights_web.utils.notifications import warning_notification, onload_callback


pn.extension(
    notifications=True,
    design="material", sizing_mode="stretch_width"
)
pn.state.notifications.position = 'top-center'

notifications.loaded = False  # module is not re-imported on reloading
pn.state.onload(onload_callback)
warning_notification("Example warning")

# Create the dashboard layout
template = pn.template.MaterialTemplate(
    site="diffannotator",
    title="Contributors Graph",  # TODO: make title dynamic
    favicon="favicon.svg",
    main=[
        pn.pane.Markdown("# Contributions")
    ],
)

# Serve the dashboard
template.servable()

if __name__ == "__main__":
    # Optionally run the application in a development server
    pn.serve(template, show=True)

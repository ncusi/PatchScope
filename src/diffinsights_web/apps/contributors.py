#!/usr/bin/env python
# -*- coding: utf-8 -*-
import panel as pn


pn.extension(
    design="material", sizing_mode="stretch_width"
)

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

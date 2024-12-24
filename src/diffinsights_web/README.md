# DiffInsights - web interface for analyzing DiffAnnotator results

The `src/diffinsights_web/` subdirectory in PatchScope sources
includes various web dashboards that demonstrate
how one can use the **`PatchScope`** project.

All web applications in this directory use
the [HoloViz Panel][Panel] framework.

In all cases, plots and diagrams shown in those web apps
are created from files generated with PatchScope scripts
from selected repository.

[Panel]: https://panel.holoviz.org/ "Panel: The Powerful Data Exploration & Web App Framework for Python"

## Contributors Graph

You can run this app with `panel serve src/diffinsights_web/apps/contributors.py`
from the top directory of PatchScope sources.

The demo of this app is also available at
<https://patchscope-9d05e7f15fec.herokuapp.com/contributors>.

This dashboard is meant to be
enhanced version of the Contributors subpage
in the Insights tab
for the GitHub repository
(example: <https://github.com/qtile/qtile/graphs/contributors>)

It provides plots (like weekly number of commits) for the whole selected repository,
and individually for each of the top-N most active authors.

## Author statistics

You can run this app with `panel serve src/diffinsights_web/apps/author.py`
from the top directory of PatchScope sources.

The demo of this app is also available at
<https://patchscope-9d05e7f15fec.herokuapp.com/author>.

This dashboard currently is a cross between plots from GitHub Insights,
but limited to selected user, with some extra plots that make sense
only for individual author.

Example of the latter is the heatmap plot that examines
what days of the week and which hours of day dominate
in given author contributions commit author date.

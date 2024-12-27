# Author Statistics

This dashboard shows various different plots
for selected author in selected repository in selected JSON data file.

It is somewhat similar to 
per-author part of the Contributors Graph part of GitHub Insights tab for a repository, 
or plots in the Overview tab for a given author / contributor on GitHub.

This dashboard app was created using HoloViz [Panel][] version 1.5.4.

## Running the app

You can run this app with `panel serve src/diffinsights_web/apps/author.py`
from the top directory of PatchScope sources.  You can get source code
from GitHub: <https://github.com/ncusi/PatchScope>.

The demo of this app is also available at
<https://patchscope-9d05e7f15fec.herokuapp.com/author>.

## Available plots

This app includes, as of PatchScope version **0.4.1**, the following plots:

- selected aggregation function (e.g. sum) over selected time period (e.g. weekly)
  of added ('+:count') and deleted ('-:count') lines in a commit, shown on one plot
- as above, but for selected line type (e.g. 'type.code'),
  or its overall contribution as ratio / percentage (e.g. 'type.code \[%]')
- contributions to patch size, namely added lines ('add'), deleted lines ('rem'),
  and how much of those were neighbouring changes and count as modified lines ('mod'),
  all on the same plot
- commit count over selected time period (e.g. week, making it weekly commit count)
- (bi)histogram of added ('+:count') and removed ('-:count') lines per commit
- (bi)histogram of added ('+:count') and removed ('-:count') lines per resample period
  (e.g. weekly)
- heatmap of types of contributions (line types) over date,
  separately for deleted lines (using Reds colormap)
  and added lines (using Greens colormap),
  as of **0.4.1** with fixed monthly frequency ('ME', <b>m</b>onth <b>e</b>nd)
- heatmap showing 2d distribution of total number of commits
  with marginal histograms, showing periodicity of contributions
  (uses author local time, assuming information about timezone was correct)

As of version **0.4.1** almost all plots are created using [Seaborn][] and/or
[Matplotlib][] libraries, and displayed using [Panel][]'s
[Matplotlib pane](https://panel.holoviz.org/reference/panes/Matplotlib.html),
with SVG rendering.
There are exceptions that use [hvPlot][] library (with some [HoloViews][] use),
with the [Bokeh][] backend.

Additionally, at the bottom of the main part of the page, after a horizontal
dividing line (a horizontal separator), there are a few informative panes,
as of **0.4.1** not yet grouped into single tabbed widget like in
[Contributors Graph app](contributors_graph.md):

- [Debugger widget](https://panel.holoviz.org/reference/widgets/Debugger.html)
  that shows show logs and errors from the running app
- [JSONEditor widget](https://panel.holoviz.org/reference/widgets/JSONEditor.html)
  in a 'view' mode, that shows the original JSON input data; you can search it
- [Tabulator widget](https://panel.holoviz.org/reference/widgets/Tabulator.html)
  that shows DataFrame with all the data extracted from JSON input file,
  and with the derived data; allows to sort and search each column
- [Perspective pane](https://panel.holoviz.org/reference/panes/Perspective.html)
  with data grouped / resampled over specified time period (e.g. 'W' for weekly)
  and aggregated with specified aggregation function (e.g. sum)

[Bokeh]: https://bokeh.org/
[HoloViews]: https://holoviews.org/
[hvPlot]: https://hvplot.holoviz.org/
[Matplotlib]: https://matplotlib.org/
[Panel]: https://panel.holoviz.org/
[Seaborn]: https://seaborn.pydata.org/

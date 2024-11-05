# TO DO List for Panel-base Demos for DiffAnnotator

This TODO list is about files (and planned files) in `notebooks/panel/`
subdirectory (and maybe, incidentally, also in planned `demo/panel/` directory).

All files discussed here, be it Jupyter Notebooks (`*.ipynb`) or Python scripts
(`*.py`), can and should be run with [Panel][], e.g. via `panel serve`.

[Panel]: https://panel.holoviz.org/ "HoloViz's Panel: The Powerful Data Exploration & Web App Framework for Python"


## TO DO List for `00-panel-simple-Matplotlib.ipynb` Jupyter Notebook

This Jupyter Notebook is meant to demo plotting with matplotlib in a Panel app.

- [ ] use throttled value of sliders in a way that is compatible
  with the button resetting both sliders to their default values;
  see [_Throttling, `pn.bind` and using button to reset values_][1]
  thread on HoloViz Discourse forum.

[1]: https://discourse.holoviz.org/t/throttling-pn-bind-and-using-button-to-reset-values/8341


## TO DO List for `01-timeline.ipynb` Jupyter Notebook

This Jupyter Notebook serves as a demo for analyzing the timeline,
that is what can be extracted from the `timeline.*.purpose-to-type.json`.

### General

- [ ] switch to interactive [Matplotlib panes][pane.Matplotlib] with the help
   of [ipympl][] (if it starts working correctly), or to some other interactive plots
   libraries
    - [hvPlot][] (`hvplot.pandas`, maybe `hvplot.xarray`),<br>
      using either Bokeh or Plotly backend
    - [Bokeh][]
    - [Plotly][]
    - [Vega][] via [Altair][] (possibly with [VegaFusion][] to provide
      serverside scaling, if there are more than 5000 rows of data)

[matplotlib]: https://matplotlib.org
[pane.Matplotlib]: https://panel.holoviz.org/reference/panes/Matplotlib.html
[seaborn]: https://seaborn.pydata.org/
[ipympl]: https://matplotlib.org/ipympl/
[plotnine]: https://plotnine.org/
[hvPlot]: https://hvplot.holoviz.org/
[Bokeh]: https://bokeh.org/
[Plotly]: https://plotly.com/python/
[Vega]: https://vega.github.io/
[Altait]: https://altair-viz.github.io/
[VegaFusion]: https://vegafusion.io/

### Bugs and issues

- [ ] resolve the issue with counts for `diff.n_rem`, `diff.n_mod`, and `diff.n_add`
  not matching counts for `-:count` and `+:count`
- [ ] make the app / notebook more robust with respect to where inside
  the directory structure `panel serve` is started (i.e. what is its working directory)
- [ ] fix the performance issue with re-resampling and thus re-computing -/+ \[%]
  multiple times after single change of selected column with a `Select` widget
- [ ] add / uncomment `@pn.cache` decorators to improve performance

### New panes

- [ ] possibly _optional_ pane or set of pane to help with debugging:
    - [ ] Debugger widget, plus the use of `logging` standard library
      (or solution compatible with it, like `structlog`)
    - [ ] JSONEditor widget in `mode="view"` to show the original JSON data
    - [ ] Tabular widget (which is replacement for DataFrame widget)
      to show all generated dataframes (original data, resampled data);<br>
      or Perspective pane (which is replacement for DataFrame pane)
- [ ] use Tqdm or other indicators (like Placeholder pane, or LoadingSpinner indicator)
  to show the information about current progress, and notify about work in progress

### New controls

- [ ] select one of available `timeline*.json` file with the Select or FileSelector widget
- [ ] upload custom `timeline*.json` file with FileInput and/or FileDropper
- [ ] select one of repositories in `timeline*.json`, if there is more than one
- [ ] select date range to plot and analyze
    - [ ] use DateRangeSlider widget coupled with DatetimeRangePicker to select date range;<br>
      default value would be the date range for a given author, the full range for widget
      would be maximum date range for all authors available in the JSON file
    - [ ] use Select widget to select one of pre-defined ranges, like in GitHub Insights,
      for example for all (full date range), last month, last 3 months, last 6 months,
      last 12 months, last 24 months
    - [ ] use RadioButtonGroup or ToggleGroup with `behavior="radio"` to switch
      between years, with default to the last year (today up to 1 year ago),
      like in GitHub Developer Overview page (perhaps if "Select Year" is selected)
- [ ] IntSlider widget to select figure size (or two sliders, one for height, one for width)<br>
  or rather make it work the one that exists in the notebook (instead of leaving it disabled)
- [ ] Select, RadioButtonGroup, ToggleGroup, or Switch to select between using 'author.date'
  or 'committer.date' as the index, and for resampling
- [ ] Toggle, or Select, or Switch to drop commits that are merges, or to drop commits
  that are either merges or root commits (leaving only commits with exactly 1 parent)
- [ ] switching between linear, logarithmic, symlog, logit, etc. scales:
    - [ ] Select, or Switch, Toggle, etc. to switch between linear and symlog scale
      for aggregated number of commits, aggregated number of lines, and for histograms thereof
      (scale of values i.e. bin sizes for histograms, i.e. x-axis)
    - [ ] Select, or Switch, Toggle, Checkbox, etc. to switch between linear and log/symlog
      scale for the counts of values in the histograms (i.e. y-axis)
    - [ ] Toggle/Switch, integrated into Card header, to switch between log (default)
      and linear scale for color (v-scale) for heatmap
    - [ ] _maybe_ Toggle, Switch, ToggleGroup, or another value in Select, to use
      the logit scale for \[%] of counts
- [ ] colors, colormaps, and color gradients
    - [ ] Select for choosing between a few selected options for colormaps for heatmap
      plots, like Reds/Greens, which would include a choice for banded colormap (i.e.
      no smooth transition between values, the color is quantized)
    - [ ] Toggle, ToggleGroup, Checkbox, or Switch to select between solid fill and
      gradient fill (see e.g. [StackOverflow: fill_between gradient](https://stackoverflow.com/questions/68002782/fill-between-gradient))


### New plots

- [ ] plots for patch size and/or patch spread metrics
- [ ] stacked area plot for -/+ line types, or for -/+ line types [%]
- [ ] Sankey plot (flow plot) diagram between file purpose and line type,
  author and line type, or directory structure and line type, etc.
- [ ] heatmap type of plot, with time with a week resolution on x-axis,
  and day of the week on the y-axis (or hour of day), similar to
  the heatmap plot in GitHub Developer Contributions
    - [ ] perhaps split into months, like in [Assayo](https://assayo.online/),
      or with end of months marked somehow in the year of activity
    - [ ] perhaps split into years, and laid out one below another, so that
      seasonal changes might be easier to find
    - [ ] Switch/Toggle to toggle between UTC dates, and localtime
      (with respect to day of the week)
- [ ] histogram of timezones (should usually be 1-2 timezones, due to DST,
  unless the developer in question travels between timezones, or moves) 
- [ ] histogram of UTC or local timezone times of authorship / commit,
  or lines, or files, aggregated over specified hours (if using localtime,
  split between work hours, maybe-work hours, night hours, free time - including weekends)


## TO DO List for `02-contributors_graph.py` Python script

Replicates GitHub Insights plots,
(see the _"Related projects"_ section in the main [`/README.md`](../../README.md) file),
but better.

Example: <https://github.com/qtile/qtile/graphs/contributors>.

See also the [TO DO List for `01-timeline.ipynb` Jupyter Notebook](#to-do-list-for-01-timelineipynb-jupyter-notebook).

### General

- [ ] Replace `warnings` global variable and `warning_notification()` function
  with a better mechanism, for example a proxy class/object for `pn.state.notifications`
- [ ] _maybe_ add a warning if no specified type of data files are found
- [ ] create stylesheet(s), replaces uses of inline styles
- [ ] extract common "magic" values into configuration variables
- [ ] allow to switch between full-repo yscale (current behavior),
      top N yscale, and each per-author subplot having their own yscale
- [ ] try to not use fixed heights and fixed widths
- [ ] rename 'resample' query parameter to 'freq', validate it

### Missing GitHub Insights features

- [x] make plot lines thicker on hover
- [ ] move #<i>N</i> to the end of the author card pane
- [ ] create app for examining author contributions (to a single repository),
      and link to it from author card (avatar, name+email)
- [ ] _maybe_ create app for listing commits in the repository, and link
      to commits by author from author card (number of commits information)
- [ ] _maybe_ add drop down menu to the end of author card header
  - [ ] view as table (in a modal)
  - [ ] download CSV
  - [x] ~~download PNG~~ Bokeh plots have "Save" tool (enabled)
        that can be used instead
- [ ] _maybe_ add support for GitHub profile avatar via querying for primary e-mail
      (see the `"avatar_url"` field in the response JSON):<br>
      <https://stackoverflow.com/questions/44888187/get-github-username-through-primary-email>

### Bugs and issues

- [ ] Switching between resample frequencies makes per-author plots
      to have yrange (-1, 1) until reload (**work around** added)


## Planned Jupyter Notebook: `03-compare.ipynb`

This Jupyter Notebook is intended to compare different plots between two selected
authors.  Note that the data file with stats that is read from needs to include data
for more than one developer.

-----

See also main [`/TODO.md`](../../TODO.md) file.<br>
See the _"Related projects"_ section in the main [`/README.md`](../../README.md) file.

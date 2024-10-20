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

### New plots

- [ ] plots for patch size and/or patch spread metrics
- [ ] stacked area plot for -/+ line types, or for -/+ line types [%]
- [ ] Sankey plot (flow plot) diagram between file purpose and line type,
  author and line type, or directory structure and line type, etc.
- [ ] ...

See also main [`/TODO.md`](../../TODO.md) file.
See the _"Related projects"_ section in the main [`/README.md`](../../README.md) file.


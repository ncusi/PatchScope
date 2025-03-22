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

Alternatively, you can start this app with `diffinsights-web <directory>`
after installing PatchScope using `pip`, and go to specific author
from the authors grid, after clicking on the author name or e-mail.

The demo of this app is also available at
<https://patchscope.mat.umk.pl/author>
and
<https://patchscope-9d05e7f15fec.herokuapp.com/author>,
but it might not run the most up-to-date version of the PatchScope.

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
with PNG or SVG rendering.
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

### Code frequency over time, for author

This plot shows, by default, the total number of added and deleted lines
over given period of time (weekly, semi-monthly, monthly, quarterly, etc.),
that is the sum of number of added and deleted lines in a commit over all commits
that were authored by given author in a given period of time.

Added lines are shown with <i>y</i>-axis pointing up, using green line color, while
deleted lines are shown with <i>y</i>-axis pointing down, using red line color.

Here is an example for qtile repository (from PatchScope version **0.4.1**):

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-line_counts-QE-sum.png)

It is step area plot; step function was selected to denote that it is aggregate
over given period of time - in the example above, over quarter (QE - quarter end).

Here is the same plot, but with smaller resample period, monthly (ME - month end):

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-line_counts-ME-sum.png)

And here is with even smaller resample period, weekly (W - week):

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-line_counts-W-sum.png)

This plot is very similar to the Code Frequency plot in GitHub Insights pane
for a repository, but the GitHub Code Frequency plot is for the whole repository,
not for selected author, and the resample frequency is fixed: weekly.

Here is an example for qtile repo from
<https://github.com/qtile/qtile/graphs/code-frequency>:

![](assets/screenshots/github-qtile_qtile-code_frequency.png)

This plot uses solid green line for additions, and dashed red line for deletions.
It literally uses negative values for deletions, instead of inverting
the y-axis.  It is an interactive plot - you can get exact values on hover.

Both the [Contributors Graph](contributors_graph.md) app
and the Contributors Graph part of the GitHub Insights tab for repository
include _separate_ plots for added and deleted lines.

For example, here is weekly per-author plot for additions from `contributors` app:<br>
![](assets/screenshots/patchscope-contributors-qtile-per_author-Tycho_Andersen-additions-W.png)<br>
and here is one from GitHub Insights (scaled to per-repo contributions):<br>
![](assets/screenshots/github-qtile_qtile-graphs_contributors-all-additions-tych0.png)


### Line type frequency over time, for author

The next plot is the 'line type / file purpose counts' plot
(though as of version **0.4.1**, only line type are turned on and available).
This uses the same type of plot as the previous one,
that its it shows contributions from added and deleted lines on the same plot,
with contribution from deleted lines shown on reversed y-axis.

The difference is where the data to plot comes from.  Instead of considering
each changed line, as in the case of the previous plot, you can select
what kind of lines you want to count.  The line types present in the
input data depend on the configuration of the annotation process (`diff-annotate`),
and  optionally on the configuration of the post-processing step (`diff-gather-stats`).

What counts as line of specific type also depends on the configuration of the
annotation process.  For `*.timeline.purpose-to-type.json` data files, the following
rules were applied (see also similar description in [Contributors Graph](contributors_graph.md)
documentation):

- if the changed file purpose (the changed line belong to) was either
  of "data", "documentation", "markup", "other", "project", or "test",
  then the line counts as that type,
- if line consists only of whitespace and comments, or is inside docstring,
  it counts as "documentation",
- otherwise it counts as "code".

This is not the only possible configuration.  For example, you might want
comments in "test" files to count as "documentation", and only lines with
some code count as "test".  This can be done with a line callback.

The following "columns" (line types) are available for the example data
files, as of PatchScope **0.4.1**:

- type.code
- type.documentation
- type.test
- type.data
- type.markup
- type.project
- type.other

GitHub Linguist uses the following categorization for _language_ types
(those are for the file as a whole; depending on configuration of the
annotation process, every changed line can be labelled as having that
type):

- data (for example: `*.afm`, `CODEOWNERS`, `*.csv`, `*.json`, `*.diff`,
  but it also includes some project files, like Pip Requirements: `requirements.txt`;
  "project" files are specified in PatchScope with custom rules), 
- programming (for example: `*.asm`, `*.c`, `*.cpp`, `*.py`,
  but it includes also some project files, like `CMakeLists.txt` and `Makefile`),
- markup (for example: `*.css`, `*.html`, `*.jinja`, `*.ipynb`, `*.tex`), 
- prose (for example: `*.po` (gettext), `*.md` (Markdown), `*.txt` (plain text)), 
- nil

Here is an example of the plot for 'type.data' changed lines (added and deleted
lines, plotted separately but on the same plot), the quarterly ('QE') count
('sum' as aggregation function), for selected author in selected repository:

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-line_type-type_data-QE-sum.png)

This plot is from PatchScope version **0.4.1**.

For each line type (like 'type.code', for example) there is also corresponding
line type percentage equivalent (like 'type.code \[%]', for example).
This percentage is computed as the number of added ('+') or deleted ('-')
lines of given type (kind), over total number of added or deleted lines.

Here is an example of the plot for 'type.code \[%]' (from version **0.4.1**
of PatchScope):

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-line_type-type_code_perc-QE-sum.png)

The figure above shows that for this author, in this specific repository,
changes to code dominate.  Note that cases where both percentages are zero
('+:type.code' and '-:type.code') means that for given period of time there
were no commits contributed by the selected author.

### Patch size components over time, for author

The definition of patch size (and its components) was taken from
the Defects4J-Dissection paper[^defects4j-dissection].

[^defects4j-dissection]: Victor Sobreira, Thomas Durieux, Fernanda Madeiral, Martin Monperrus, and Marcelo de Almeida Maia _"Dissection of a Bug Dataset: Anatomy of 395 Patches from Defects4J"_, SANER 2018, https://doi.org/10.1109/SANER.2018.8330203

The patch size metric is sum of the number of added, modified, and removed (deleted) lines.
Lines are considered _modified_ when sequences of removed lines are straight followed by added lines ~~(or vice versa).~~
To count each modified line, a pair of adjacent added and removed lines is needed.

Take for example the following diff, which is a part of commit
[46bf2086](https://github.com/qtile/qtile/commit/46bf2086273d52049d9b8c6ee528a3d5aeb16ee2)
in qtile repository (first hunk of changes):

```diff
diff --git a/test/test_hook.py b/test/test_hook.py
index effd70a9..e005ac68 100644
--- a/test/test_hook.py
+++ b/test/test_hook.py
@@ -27,14 +27,12 @@ import pytest

 import libqtile.log_utils
 import libqtile.utils
-from libqtile import hook
+from libqtile import config, hook, layout
+from libqtile.config import Match
 from libqtile.resources import default_config
-from test.conftest import BareConfig
+from test.conftest import BareConfig, dualmonitor
 from test.helpers import Retry

-# TODO: more tests required.
-# 1. Check all hooks that can be fired
-

 class Call:
     def __init__(self, val):
```

This diff consists of 3 sequences of changed lines (change groups,
or "chunks" using the term from Defects4j-Dissection paper[^defects4j-dissection]).
In 1st group there is 1 modified line and 1 added line,
in 2nd group there is 1 modified line, and
in 3rd group there are 3 deleted (removed) lines.
In total, for this hunk of changes in `test/test_hook.py` file,
the algorithm finds 3 removed lines, 2 modified lines, and 1 added line.

The 'patch sizes' plot (shown below) counts things a bit differently:
it counts modified lines and added lines up, adding to all '+' lines, and
it counts modified lines and removed lines down, adding to all '-' lines.

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-patch_sizes-QE.png)

This means that modified lines are kind of counted twice,
once pointing up (adding to added lines, to sum to '+' lines),
once pointing down (adding to removed lines, to sum to '-' lines).
On one hand, it means that the height of the plot is not equal to
the patch size; on the other hand it means that the plot looks
very similar to the code frequency over time or 'line counts' plot:

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-line_counts-QE-sum.png)

Both plots were created using PatchScope version **0.4.1**.

Note that it is not always that first deleted line corresponds to first added line,
creating modified line.  In the following diff (taken from commit
[1db6bab2](https://github.com/qtile/qtile/commit/1db6bab250eda20159b425de4378d27241b2997e)
in qtile repository):
```diff
diff --git a/libqtile/widget/notify.py b/libqtile/widget/notify.py
index a87281e5..8a1eec1f 100644
--- a/libqtile/widget/notify.py
+++ b/libqtile/widget/notify.py
@@ -219,5 +219,6 @@ class Notify(base._TextBox):
             self._invoke()

     def finalize(self):
-        notifier.unregister(self.update, on_close=self.on_close)
+        if notifier is not None:
+            notifier.unregister(self.update, on_close=self.on_close)
         base._TextBox.finalize(self)

```
it is the second added line that was modified (if we consider whitespace
changes to be a modification).

See also similar description in the [Contributors Graph](contributors_graph.md)
documentation.

This algorithm does not always give the correct results.  Take for example
the [928a0447 commit](https://github.com/qtile/qtile/commit/928a0447f52a24f0c39cc135cb958a551c3855bb)
from the qtile repository:

```diff
diff --git a/docs/manual/releasing.rst b/docs/manual/releasing.rst
index ff7b31eb..0b935ee0 100644
--- a/docs/manual/releasing.rst
+++ b/docs/manual/releasing.rst
@@ -39,9 +39,10 @@ Be sure that you GPG-sign (i.e. the ``-S`` argument to ``git commit``) this comm
 6. Make sure all of these actions complete as green. The release should show up
    in a few minutes after completion here: https://pypi.org/project/qtile/

-7. send a mail to qtile-dev@googlegroups.com; I sometimes just use
-   git-send-email with the release commit, but a manual copy/paste of the
-   release notes into an e-mail is fine as well. Additionally, drop a message
-   in IRC/Discord.
+7. Push your tag commit to master.
+
+8. Update `the release string
+   <https://github.com/qtile/qtile.org/blob/master/config.toml#L49>`_ on
+   qtile.org.

 8. Relax and enjoy a $beverage. Thanks for releasing!

```

The current version of the algorithm (as of PatchScope **0.4.1**),
when run on the git diff, says  that there are 4 modified lines, and 1 added line,
while in reality  this part was completely rewritten,
and the correct answer should be 4 deletions (removals) and 5 additions.


### Commit counts over time, for author

This plot shows number of commits made by selected author, per given period of time.
There is similar plot in authors grid part of GitHub Insights tab for a repository,
in Contributors Graph section, but in it this is always the weekly number of commits,
that is total number of commits in a given week.  For PatchScope, it is configurable
(via sidebar widgets).

Here is an example for qtile repository (from PatchScope version **0.4.1**),
for quarterly frequency ('QE'):

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-commit_counts-QE.png)

Here is the same case, but with the weekly frequency ('W') that GitHub Insights use:

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-commit_counts-W.png)

The very same plot is also available in the authors grid part of the
[Contributors Graph](contributors_graph.md) app (see the
"[Commits over time](contributors_graph.md#commits-over-time)" subsection),

![](assets/screenshots/patchscope-contributors-qtile-per_author-Tycho_Andersen-commits-W.png)

and in authors grid part of Contributors Graph part of GitHub Insights for repo:

![](assets/screenshots/github-qtile_qtile-graphs_contributors-all-commits-tych0.v2.png)

Note that in GitHub Insights case the plot scale can (!) be selected according to
the commit counts plot for the whole repository, like in the example below.

![](assets/screenshots/github-qtile_qtile-graphs_contributors-all-commits-tych0.v1.png)


### Histogram of −/+ counts per commit, for author

This plot shows (bi)histogram of distribution of numbers of added lines
('+:count') and of numbers of deleted lines ('-:count'), put together on
one plot, with '-:count' counting in negatives.

In this case it is histogram of line counts (added or deleted) per _commit_,
for all commits created by selected author.

Here is an example for qtile repository (from PatchScope version **0.4.1**):

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-histogram_of_line_counts_per_commit-bw=3-max_val=100.png)

The figura above is for the default values.  If we zoom a bit we can
see the trend (for this specific author, in this specific repository)
more clear (and with controls shown explicitly):

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-histogram_of_line_counts_per_commit-bw=1-max_val=35-with_controls.png)

This figure shows that statistically, larger additions are more common
than large deletions, but that small changes are most common.

This (bi)histogram does not show the correlation between the number of
deleted and added lines, though.


### Histogram of −/+ counts per resample period, for author

**TODO**


### Line types heatmap ±

All line types distribution plots show how many changed lines are of given type.
What counts as line of specific type depends on the configuration of the
annotation process, as described above.

The heatmap plot tries to show on a single plot the distribution of changes
with respect to line type (and whether line was added or deleted)
versus time.  You have time on x-axis, divided into resample frequency period
(as of PatchScope **0.4.1** it is always monthly aggregates: 'ME'), using selected
aggregation functions (by default it is 'sum'), with line type on y-axis,
and color denoting the aggregation of number of lines of specific type.

Here is an example from tensorflow repository:

![](assets/screenshots/patchscope-author-tensorflow-Yong_Tang-line_type-heatmap-ME-sum-cmap_log.png)

Note that as of PatchScope **0.4.1** defaults are specified for one specific
example to look nice, and might result in less readable output for other cases.

Differently from "[Line types heatmap ±\[%]](contributors_graph.md#line-types-heatmap-)",
in [Contributors Graph](contributors_graph.md) app, this heatmap plot shows line counts,
though using logarithmic color scale, rather than ± percentages (\[%]) of line types.

![](assets/screenshots/patchscope-contributors-qtile-per_author-Tycho_Andersen-line_types_heatmap-QE.png)

GitHub provides somewhat tangentially related heatmap on the authors profile page;
for example, here is heatmap of contributions for the same (GitHub) author
(<https://github.com/yongtang>) as in figure above:

![](assets/screenshots/github-yongtang_contributions_heatmap.png)

Here the profile contributions graph is a record of contributions given author
made to repositories on GitHub (not limited to given repository).

Issues, pull requests, and discussions will appear on ones contribution graph
on GitHub if they were opened in a standalone repository, not a fork.
Commits will appear on ones contributions graph if they meet all the following
conditions: email matches the GitHub account, they are made in standalone
repository, on repository's default branch or the `gh-pages` branch
(with some additional conditions).


### Periodic behavior, local time

This heatmap plot, together with its marginal histograms, is geared towards
detecting periodicity in selected authors behavior (in selected repository).
It plots total number of commits (a sum) that were created during specific
hour of the day (on x-axis) and specific day of the week (on y-axis).

It converts Unix timestamps to localtime date using the timezone data from commit
(assuming that timezone information is correctly configured); though this matters
more for the hour dimension than for the day of week dimension: see figures
below.

![](assets/hour_UTC_vs_hour_localtime-ezhulenev.png)

![](assets/day_of_week-localtime_vs_UTC-ezhulenev.png)

You can see that without switching to localtime one would get incorrect results
(results that looks to be incorrect).

Both of those figures above come from the `notebooks/panel/02-contributors_graph.ipynb`
Jupyter Notebook
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/ncusi/PatchScope/main?labpath=notebooks%2Fpanel%2F02-contributors_graph.ipynb).

This plot can be used to detect different behaviors.  For example,
the following plot shows contributions of an author that looks like
they perform during workdays (Monday to Friday), and during working hours,
with most work done 11-15:

![](assets/screenshots/patchscope-author-tensorflow-Eugene_Zhulenev-periodic_behavior_heatmap.png)

Here is the plot that shows contributions of an author which,
what looks like, perform their work outside working hours (16-01),
any day of the week:

![](assets/screenshots/patchscope-author-tensorflow-Yong_Tang-periodic_behavior_heatmap.png)

Here, though in different repository, is one that shows contributions
of the author that performs their work mostly during weekends (Saturday-Sunday)
at day hours (7-21), with some work done during workdays outside working hours.

![](assets/screenshots/patchscope-author-qtile-Tycho_Andersen-periodic_behavior_heatmap.png)

There is a similar plot in GitHub, namely the contributions heatmap
in the user's profile, though it is week of the month on x-axis
versus day of the week on y-axis (with week starting on Sunday),
for a selected year.

![](assets/screenshots/github-tych0_contributions_heatmap.png)

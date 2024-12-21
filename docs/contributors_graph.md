# Contributors Graph

This dashboard is meant to be
enhanced version of the Contributors subpage
in the Insights tab
for the GitHub repository
(example: <https://github.com/qtile/qtile/graphs/contributors>).

All examples are taken from **0.4.1** version of PatchScope.

## Running the app

You can run this app with `panel serve src/diffinsights_web/apps/contributors.py`
from the top directory of PatchScope sources.

The demo of this app is also available at
<https://patchscope-9d05e7f15fec.herokuapp.com/contributors>.


## Available plots

Contributors Graph dashboard provides plots (like weekly number of commits)
for the whole selected repository,
and individually for each of the top-N most active authors.

The GitHub Repo Insights offers the following plots<br>
<https://github.com/qtile/qtile/graphs/contributors>:

- Commits (commits over time)
- Additions (additions over time)
- Deletions (deletions over time)

The Contributors Graph in PatchScope's DiffInsights Web app
offers the following plots:

- Commits
- Additions
- Deletions
- Files changed
- Patch size (lines)
- Patch spreading (lines)
- Line types distribution \[%]<br>
  (area plot)
- Line types heatmap ±\[%]
- Flow from path to line type<br>
  (Sankey diagram, not over time)
- No plot

### Commits over time

This plot shows number of commits per given period of time.
For GitHub Insights, it is weekly number of commits,
that is total number of commits in a given week.
For PatchScope, it is configurable (via sidebar widgets).

The GitHub Insights version looks like the following:

![](assets/screenshots/github-qtile_qtile-graphs_contributors-all-commits.png)

The PatchScope Contributors Graph version looks like this<br>
taken from **0.4.1** version of PatchScope,
modified to remove line types percentage info:

![](assets/screenshots/patchscope-contributors-qtile-all-commits_plot.png)

Both plots are created for the same repository;
plots created by GitHub are "live",
plots created by PatchScope are based on annotations taken at some fixed point of time.
That is one of the reasons why numbers of commits per author doesn't match
between those two apps (services).

## Ad-hoc exploration with Perspectives

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

### Additions and deletions over time

This plot shows total number of added or deleted lines over given period of time,
that is the sum of number of added/deleted lines in a commit over all commits
that were authored in a given period of time (by default: over week).

This information is extracted from unified diff of changes in the commit (patch).
Note that changing a line in this method of counting shows as deleting
the old version, and adding a new version of a line.

For example, in the following [diff from the `tqdm` repository][335308-diff]
```diff
diff --git a/README.rst b/README.rst
index 7823c4b..9323c52 100644
--- a/README.rst
+++ b/README.rst
@@ -3,8 +3,8 @@ Unidiff

 Simple Python library to parse and interact with unified diff data.

-.. image:: https://travis-ci.org/matiasb/python-unidiff.svg?branch=master
-    :target: https://travis-ci.org/matiasb/python-unidiff
+.. image:: https://www.travis-ci.com/matiasb/python-unidiff.svg?branch=master
+    :target: https://travis-ci.com/matiasb/python-unidiff

 Installing unidiff
 ------------------
```
there are 2 deleted lines and 2 added lines in a single commit (patch).

[335308-diff]: https://github.com/matiasb/python-unidiff/commit/3353080f357a36c53d21c2464ece041b100075a1#diff-7b3ed02bc73dc06b7db906cf97aa91dec2b2eb21f2d92bc5caa761df5bbc168f

The GitHub Insights version of this plot looks like the following
(for the additions):

![](assets/screenshots/github-qtile_qtile-graphs_contributors-all-additions.png)

Note that the grid of per-author plots is now sorted by the number of added lines
(the "++" line), though in this case it is the same order as sorted by the number
of commits.

GitHub Insights draws all plots using the same line color.

The PatchScope Contributors Graph version of the added lines plot looks like this<br>
taken from **0.4.1** version of PatchScope,
modified to remove line types percentage info:

![](assets/screenshots/patchscope-contributors-qtile-all-additions_plot.png)

PatchScope's DiffInsights Web app draws
deletions using the red line color, and additions using the green line color,
just like the color when syntax-highlighting diffs (in most cases).

### Files changed over time

This plot shows the sum over given period of time (over week by default)
of number of files changed by the commit (or a patch).  The previous example
diff involved only a single file.

Note: This is not a number of unique files that were changed within given period
(for example within given week).

Here is how it looks in PatchScope (version **0.4.1**):

![](assets/screenshots/patchscope-contributors-qtile-all-files_changed.png)

Note that it counts different _file name_ in a commit (or a patch),
excluding special case of `/dev/null`.  This means that file rename
counts as changing two files for the purposes of this plot.

## Ad-hoc exploration with Perspectives

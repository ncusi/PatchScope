# TO DO List for `02-contributors_graph.py` Python script

Replicates GitHub Insights plots,
(see the _"Related projects"_ section in the main [`/README.md`](../../README.md) file),
but better.

Example: <https://github.com/qtile/qtile/graphs/contributors>.

See also the [TO DO List for `01-timeline.ipynb` Jupyter Notebook](#to-do-list-for-01-timelineipynb-jupyter-notebook).

## General

- [ ] Replace `warnings` global variable and `warning_notification()` function
  with a better mechanism, for example a proxy class/object for `pn.state.notifications`
- [ ] _maybe_ add a warning if no specified type of data files are found
- [ ] create stylesheet(s), replaces uses of inline styles
- [ ] extract common "magic" values into configuration variables
- [ ] allow to switch between full-repo yscale (current behavior),
      top N yscale, and each per-author subplot having their own yscale
- [ ] try to not use fixed heights and fixed widths
- [ ] rename 'resample' query parameter to 'freq', validate it

## Missing GitHub Insights features

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

## Bugs and issues

- [x] Switching between resample frequencies makes per-author plots
      to have yrange (-1, 1) until reload
- [ ] In per-author plot, missing values creates "jumps" instead of being filled with 0;
      this might be the question of the order of grouping (to be tested)
- [ ] When adding histogram on the margin of the main plot,
      the main plot no longer stretches full (remaining) width of the page.

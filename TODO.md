# TO DO List for Diff Annotator package

- [x] cleanup
    - [x] cleanup annotate.py
    - [x] test annotate.py code
    - [x] test annotate.py script
    - [x] cleanup languages.py
    - [x] cleanup lexer.py
    - [x] move from [click][] to [typer][] for handling CLI parameters
    - [x] add docstring for all files
- [x] make it a separate package
    - [x] directory structure
    - [x] 'pyproject.toml' (and _optionally_ 'setup.py')
    - [x] 'README.md'
    - [x] 'LICENSE' (MIT License)
    - [ ] _maybe_ 'MANIFEST.in'
    - [x] separate repository on GitHub
    - [x] move `__version__` to ~~`__init__.py`~~ `config.py`
         (see also ["version at runtime" in setuptools_scm docs](https://setuptools-scm.readthedocs.io/en/stable/usage/#version-at-runtime)
          and ["Single-sourcing the package version" in Python Packaging User Guide](https://packaging.python.org/en/latest/guides/single-sourcing-package-version/))
    - [ ] add `docs/` directory (for man pages, and maybe API documentation)
      - [ ] use [MkDocs][] or [Material for MkDocs][mkdocs-material] for general documentation
      - [ ] generate API documentation using [mkdocstrings][]
      - [ ] generate documentation for scripts using [mkdocs-typer][]
            ([typer][] is used for parsing CLI arguments)
      - [ ] _maybe_ generate manpages from MkDocs with [mkdocs-manpage][] (at least for scripts)
      - [ ] _maybe_ include gallery of examples with [mkdocs-gallery](https://smarie.github.io/mkdocs-gallery/)
      - [ ] _maybe_ CLI demos with [Asciinema][], or one of the alternatives, like
            [shelldemo][], [Terminalizer][], [ttyrec][] (and possibly also [ttygif][])
    - [ ] _maybe_ use build tool like Poetry, Hatch, PDM, Rye, uv, Flit,...
    - [ ] _maybe_ use in HaPy-Bug (python_bug_dataset) [via a GitHub URL][1]
- [x] ~~3~~ 4 scripts _(their names may change in the future)_ - see `[project.scripts]` section
  in [`pyproject.toml`](pyproject.toml)
    - [x] `diff-generate` (from [`generate_patches.py`](src/diffannotator/generate_patches.py))
    - [x] `diff-annotate` (from [`annotate.py`](src/diffannotator/annotate.py))
    - [x] `diff-gather-stats` (from [`gather_data.py`](src/diffannotator/gather_data.py))
    - [ ] `diff-augment` - augment JSON files with data from Git or from GitHub
- [ ] make it possible to use each script features from Python
  (see for example `process_single_bug()` function in [`annotate.py`](src/diffannotator/annotate.py))
  and document such use (in `docs/`, in function docstring, in file docstring, in doctests)
- [ ] improve common handling of command line parameters for all scripts
    - [ ] _maybe_ make it possible to use configuration files to set parameters for CLI
      (similarly to [Hydra][]) with [typer-config][] (e.g. `my-typer-app --config config.yml`)
    - [ ] _maybe_ implement options common to all scripts, like `--version`,
      putting their implementation `__init__.py`,
      and make use of "_Options Anywhere_" and "_Dependency Injection_" capabilities
      that [typer-tools][] adds
    - [ ] _maybe_ implement `--log-file` (defaults to '<script-name>.log', supports '-' for stderr)
      and `--log-level` options, the latter with the help of [click-loglevel][]
      and [Typer support for Click custom type](https://typer.tiangolo.com/tutorial/parameter-types/custom-types/#type-parser)
- [x] add logging, save logged information to a `*.log` (or `*.err` and `*.messages`):
      currently uses [logging][] module from standard library.
    - [ ] limit information logged to console to ERROR or higher, or CRITICAL only
    - [ ] _maybe_ if consider using [colorlog][] for colored log on console
    - [ ] _maybe_ allow structured JSON logging (e.g. if log file name ends with *.json)
          with [python-json-logger][]
    - [ ] use `logger.exception()` in exception handlers, in place of `logger.error()`
    - [ ] _maybe_ consider using alternative tools:
      - [loguru][] (possibly with [pytest-loguru](https://github.com/mcarans/pytest-loguru),
        or see [Replacing `caplog` fixture from `pytest` library](https://loguru.readthedocs.io/en/stable/resources/migration.html#replacing-caplog-fixture-from-pytest-library)
        in the loguru documentation)
      - [structlog][] (possibly with [pytest-structlog](https://github.com/wimglenn/pytest-structlog) plugin,
        or use [structlog tools for testing](https://www.structlog.org/en/stable/testing.html))
      - ...

## TO DO List for `diff-generate` script

This script can be used to generate patches (*.patch and *.diff files)
from a given repository, in the format suitable for later analysis:
annotating with `diff-annotate`, and computing statistics with `diff-gather-stats`.

However, you can also create annotations directly from the repository
with `diff-annotate from-repo` subcommand.

- [ ] improvements and new features for `generate_patches.py`
    - [ ] configure what and where to output
        - [x] `--use-fanout` 
          (e.g. save result in 'c0<b>/</b>dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff'
          instead of in '0001-Create-.gitignore-file.patch');<br>
          **NOTE**: this required switching from using `git format-patch`
          to using `git log -p`, and currently does not save the commit message.

## TO DO List for `diff-annotate` script

This script can be used to annotate existing dataset (patch files in subdirectories),
or selected subset of commits (of changes in commits) in given repository.

The result of annotation is saved in JSON files, one per patch / commit.

- [ ] improvements and new features for `annotate.py`
    - [x] subcommands
        - [x] `patch` - annotate a given single patch file
        - [x] `dataset` - annotate all patches in a given dataset (directory with directories with patches)
        - [x] `from-repo` - annotate changesets of given selected revisions in a given Git repository
    - [x] parse whole pre-image and post-image files
          (only via Git currently; ~~or via GitHub / GitLab / ...~~)
    - [ ] configurable file type
        - [x] global option `--ext-to-language` (the API it uses already existed)
        - [x] global option `--filename-to-language` (using new API)
        - [ ] global option `--glob-to-language` (using new API)
        - [x] global option `--pattern-to-purpose` (using new API)
        - [ ] (optionally?) use [`wcmatch.pathlib`](https://facelessuser.github.io/wcmatch/pathlib/)
          to be able to use `**` in patterns (with `globmatch` and `pathlib.GLOBSTAR`)
    - [ ] option to limit analyzing changes to only "production code" changes,
      for example with `--production-code-only`, or `--file-purpose-limit`, etc.
    - [ ] support [.gitattributes overrides of GitHub Linguist][2]
    - [x] optionally use Python clone of [github/linguist][], namely [retanoj/linguist][], installed from GitHub,
          with `--use-pylinguist` (note: [install requires libmagic-dev and libicu-dev libraries](https://github.com/douban/linguist/issues/25))
        - [x] make it use newer version of `languages.yml` by default
        - [ ] _maybe_ use `Language.detect(name=file_name, data=file_contents)`,
          or `FileBlob(file_name).language.name` (_deprecated_) to detect language based on file contents
          if extension is not enough to determine it
    - [ ] optionally use Python wrapper around [github/linguist][], ~~namely [scivision/linguist-python][],~~
          with `--use-ghlinguist` (e.g. via [RbCall](https://github.com/yohm/rb_call),
          or ~~via [rython](https://pypi.org/project/rython/)~~,
          or other technique) 
    - [x] configurable line annotation based on file ~~type~~ purpose
        - [x] `PURPOSE_TO_ANNOTATION` global variable
        - [x] global option `--purpose-to-annotation` in [`annotate.py`](src/diffannotator/annotate.py) script
          - [ ] do not modify the global variable `PURPOSE_TO_ANNOTATION`,
            reuse the code from `diff-gather-stats timeline --purpose-to-annotation`
    - [ ] configurable line annotation based on tokens
    - [x] computing patch/diff size and spread, following
          _"[Dissection of a bug dataset: Anatomy of 395 patches from Defects4J][dissection-defects4j-paper]"_
          (and extending it) - independent implementation
        - [x] _patch size_ counting added ('+'), removed ('-'), and **modified** ('!') lines,
              with simplified changed lines detection:<br>
              "Lines are considered modified when sequences of removed lines are straight followed by added lines
              (or vice versa). Thus, to count each modified line, a pair of added and removed lines is needed."
        - [x] _patch spreading_ - counting number of chunks / groups:<br>
              "A chunk is a sequence of continuous changes in a file, consisting of the combination
              of addition, removal, and modification of lines."
        - [x] _patch spreading_ - sum of spreading of chunks:<br>
              "number of lines interleaving chunks in a patch", per file<br>
              (counting inter-hunk distances)
        - [x] _patch spreading_ - number of modified source files
        - [ ] _patch spreading_ - number of modified classes (_**not planned**_)
        - [ ] _patch spreading_ - number of modified methods \[and functions] (_**not planned**_)
        - [x] check the Python (and JavaScript) code used by work mentioned above, available at
              <https://github.com/program-repair/defects4j-dissection>,
              ~~and maybe use it~~ (copy, ~~or import from PyPI/GitHub, or include as submodule and import~~):
              it calls `defect4j` binary from <https://github.com/rjust/defects4j>
              (Java code, Ant build system, with Perl wrappers - for Java code only)
    - [ ] retrieving and adding commit metadata
        - [x] from Git repository - for 'from-repo'
        - [ ] from *.message files - for 'dataset' (see BugsInPy, HaPy-Bugs)
        - [x] from `git log -p` generated *.diff files - for 'dataset'
        - [ ] from `git format-patch` generated \*.patch/\*.diff files - for 'dataset'
        - [ ] from Git (or GitHub) repository provided via CLI option - for 'dataset'
    - [ ] configuration file (*.toml, *.yaml, *.json, *.ini, *.cfg, or *.py);<br>
      maybe using [Hydra][] (see [_Using Typer and Hydra together_][3]),
      maybe using [typer-config][] (e.g. `my-typer-app --config config.yml`),
      maybe using [Dynaconf][],
      maybe using [configparser][] standard library
      (see also: files read by [rcfile](https://pypi.org/project/rcfile/) package,
      or better use [platformdirs](https://pypi.org/project/platformdirs/)
      or [appdirs](https://pypi.org/project/appdirs/))
    - [ ] documentation on how to use API, and change behavior
    - [ ] configure output format (and what to output)
        - [x] for `from-repo` subcommand: `--use-fanout` 
          (e.g. save in 'c0<b>/</b>dcf39b046d1b4ff6de14ac99ad9a1b10487512.json',
          instead of in 'c0dcf39b046d1b4ff6de14ac99ad9a1b10487512.json')
        - [x] for `dataset` subcommand: `--uses-fanout`
          to process the result of generating patches with `--use-fanout`
        - [ ] for `from-repo` and `dataset`: `--output-file=<filename>`
          to save everything into single JSON or JSON Lines file
    - [ ] _maybe_ configuration options
    - [ ] _maybe_ configuration callbacks (in Python), like in [git-filter-repo][]
        - [x] `AnnotatedPatchedFile.line_callback` static field
        - [x] global option `--line-callback` in [`annotate.py`](src/diffannotator/annotate.py) script
    - [ ] _maybe_ generate skeleton, like a framework, like in [Scrapy][scrapy]
    - [ ] _maybe_ provide an API to generate processing pipeline, like in [SciKit-Learn][sklearn]

## TO DO List for `diff-gather-stats` script

This script and its subcommands can compute various statistics and metrics
from patch annotation data generated by the `diff-annotate` script.

It saves extracted insights in a single file; currently only JSON is
supported.  Different subcommands use different schemas and save different
data.

- [ ] improvements and new features for `gather_data.py`
    - [ ] docstring for `common()` function
    - [ ] `purpose-counter` subcommand
      - [ ] rename to `dataset-summary` (and include other metrics)
      - [ ] draw Venn diagram of patches that contain added, removed and/or modified lines,
        like on Fig. 1 of _"[Dissection of a bug dataset: Anatomy of 395 patches from Defects4J][dissection-defects4j-paper]"_
        - [matplotlib-venn[shapely]](https://github.com/konstantint/matplotlib-venn) or
          [matplotlib_set_diagrams](https://matplotlib-set-diagrams.readthedocs.io/), or
        - [upsetplot](https://upsetplot.readthedocs.io/)
      - [ ] draw Venn / Euler diagram, or upsetplot, of patches that unidiff contain
        added and/or removed lines; see above
      - [ ] table or DataFrame with descriptive statistics for patch size and spreading,
        like on Table 1 in _"[Dissection...][dissection-defects4j-paper]"_<br>
        - patch size: \# Added lines, \# Removed lines, \# Modified lines, Patch size
        - patch spreading: \# Chunks (Groups), Spreading, \# Files, ~~\# Classes~~, ~~\# Methods~~
        - statistics: min, 25%, 50%, 75%, 90%, 95%, max
      - [ ] _if missing_, table or DataFrame with statistics
        of dataset and patch size: \# Patches/Bugs/Commits, \# Files, \# Lines
        (however the last one is determined: sum of '+' and '-' lines, max, average,...)
        like in the first third of the table on Fig. 1(b) "dataset characteristics"
        in unpublished _"[HaPy-Bug – Human Annotated Python Bug Resolution Dataset][HaPy-Bug-paper]"_
        paper
      - [ ] _maybe_ number of patches/bugs/commits for each project,
        like on Table 1 in _"[BugsInPy:...][BugsInPy-paper]"_
        - [ ] _maybe_ augmented with project data:
          LoC (lines of code, e.g. via
          [SLOCCount](https://dwheeler.com/sloccount/) in Perl,
          [loccount](https://gitlab.com/esr/loccount) in Go,
          [pygount](https://pygount.readthedocs.io/) in Python with Pygments),
          Test LoC, \# Tests, \# Stars
          (but see _"[The Fault in Our Stars: An Analysis of GitHub Stars as an Importance Metric for Web Source Code](https://casa.rub.de/forschung/publikationen/detail/the-fault-in-our-stars-an-analysis-of-github-stars-as-an-importance-metric-for-web-source-code)"_)
          - [ ] _maybe_ exponential fit, half life in years, to
            % of commit still present in code base over time (KM estimate of survival function),
            like [Git-of-Theseus](https://github.com/erikbern/git-of-theseus/)
            (_"[The half-life of code & the ship of Theseus](https://erikbern.com/2016/12/05/the-half-life-of-code.html)"_,
            see _Half-life by repository_ section)
      - [ ] _maybe_ with Timeframe, \# Bugs, \# Commits,
        like on Table 3 in _[Herbold et al.][Herbold-paper]_
      - [ ] statistics of assigned line labels over all data (automatic, human consensus),
        like in Table 4 in _[Herbold et al.][Herbold-paper]_:
        - labels in rows (bug fix, test, documentation, refactoring,..., no consensus, total),
        - all changes, production code, other code in columns - number of lines, \% of lines
          (\% of lines is also used in second third of table in Fig. 1(b), "line annotations",
          in _"[HaPy Bug - ...][HaPy-Bug-paper]"_ unpublished paper)
      - [ ] robust statistics of assigned line labels over all data (automatic,...)
        like in table in Fig. 2(a) in _[Herbold et al.][Herbold-paper]_:
        - labels in rows (bug fix, test, documentation, refactoring,..., no consensus, total),
        - overall (all changes), production code in columns - subdivided into
          median, MAD (Median Absolute Deviation from median), CI (Confidence Interval), >0 count
      - [ ] histogram of bug fixing lines percentage per commit (overall, production code)
        like in Fig. 2(b,c) in _[Herbold et al.][Herbold-paper]_
      - [ ] boxplot, (or boxenplot, violin plot, or scatterplot, or beeswarm plot)
        of percentages of line labels per commit (overall, production code)
        like in Fig. 2(b,c) in _[Herbold et al.][Herbold-paper]_
        and in Fig. 1(d) in _"[HaPy Bug - ...][HaPy-Bug-paper]"_ - "distribution
        of number of line types divided by all changes made in the bugfix"
      - [ ] _maybe_ hexgrid colormap showing relationship between the number of lines changed
        in production code files and the percentage of bug fixing lines
        ~~and lines without consensus~~ like in Fig. 9 in _[Herbold et al.][Herbold-paper]_.
        The plot has 
        - percentage of bugfixing lines ~~(or lines without consensus)~~ on X axis (0.0..1.0),
        - \# Lines changed  on Y axis using logscale (10^0..10^4),
        - and log10(\# Commits) ~~or log10(\# Issues)~~ as the hue / color (10^0..10^3, mostly),
        - with the regression line for a linear relationship between the variables overlaid,<br>
          and the <i>r</i>-value i.e. Pearson's correlation coefficient
      - [ ] _maybe_ the table of observed label combinations;
        the Table 8 in the appendix of _[Herbold et al.][Herbold-paper]_
        is for lines without consensus, but we may put lines in a single commit / patch;
        instead of the table, [UpSet Chart](https://python-graph-gallery.com/venn-diagram/#UpSet%20Chart)
        / [UpSet: Visualizing Intersecting Sets](https://upset.app/)
        may be used (using [`upsetplot`](https://upsetplot.readthedocs.io/) library/package,
        or older [`pyupset`](https://github.com/ImSoErgodic/py-upset) for Python)
      - [x] add `--output` option - currently supports only the JSON format
        - [ ] support for `-` as file name for printing to stdout
    - [ ] `purpose-per-file` subcommand
      - [ ] table, horizontal bar plot, or pie chart - of % of file purposes
        in the dataset, like bar plot in left part of Fig. 1(c)
        "percentage of lines by annotated file type"
        in _"[HaPy Bug - ...][HaPy-Bug-paper]"_ unpublished paper
      - [ ] composition of different line labels for different file types,
        using horizontal stacked bar plot of percentages, or many pie charts,
        like the stacked bar plot on the right part of Fig. 1(c)
        "breakdown of line types by file type" in _"[HaPy Bug - ...][HaPy-Bug-paper]"_;<br>
        though note that for some file types all lines are considered to be specific type,
        and that this plot might be more interesting for human-generated line types,
        rather than for line types generated by `diff-annotate` tool
    - [ ] `lines-stats` subcommand
      - [ ] fix handling of `'commit_metadata'` field (skip it)
    - [ ] `timeline` subcommand
      - [ ] _maybe_ create pandas.DataFrame and save as Parquet, Feather, HDF5, or pickle
      - [ ] _maybe_ resample / groupby (see `notebooks/`)
      - [ ] print information about results of `--purpose-to-annotation`
      - [ ] include information about patch size and spread metrics
    - [ ] store only basename of the dataset in \*.json output, not the full path
    - [ ] global option `--output-format` (json, _maybe_ jsonlines, csv, parquet,...)
    - [ ] global options `--bugsinpy-layout`, `--from-repo-layout`, `--uses-fanout`
      (mutually exclusive), configuring where the script searches for annotation data;
      print errors if there is a mismatch of expectations vs reality (if detectable)
    - [ ] option or subcommand to output flow diagram
      (here the flow could be from file purpose to line type,
      or from directory structure (with different steps) to line type or file purpose)<br>
      using:
      - [ ] [Mermaid][] diagramming language (optionally wrapped in Markdown block)
      - [ ] [Plotly][] (for Python) `plotly.graph_objects.Sankey()`
        / `plotly.express.parallel_categories()` (or `plotly.graph_objects.Parcats()`), or<br>
        [HoloViews][] `holoviews.Sankey()` - with Bokeh and matplotlib backends, or<br>
        [pySankey](https://github.com/anazalea/pySankey) - which uses matplotlib,
        but is limited to simple two divisions flow diagram
    - [ ] option or subcommand to generate ASCII-art chart in terminal;<br>
      perhaps using [Rich][] (used by typer by default) or  [Textual][],
      or just [Colorama][] - perhaps with [tabulate](https://pypi.org/project/tabulate/)
      or [termtables](https://pypi.org/project/termtables/).  Possibilities:
      - pure Python: horizontal bar, created by repeating a character N times, like in
        [How to Create Stunning Graphs in the Terminal with Python](https://medium.com/@SrvZ/how-to-create-stunning-graphs-in-the-terminal-with-python-2adf9d012131)
      - [terminalplot](https://github.com/kressi/terminalplot) - only XY plot with '*', minimalistic
      - [asciichartpy](https://pypi.org/project/asciichartpy/) - only XY plot, somewhat configurable, uses Node.js [asciichart](https://github.com/kroitor/asciichart)
      - [uniplot](https://github.com/olavolav/uniplot) - XY plots using Unicode, fast, uses NumPy
      - [termplot](https://github.com/justnoise/termplot) - XY plots and histograms, somewhat flexible
      - [termplotlib](https://github.com/nschloe/termplotlib) - XY plots (using gnuplot), horizontal and vertical histograms
      - [termgraph](https://github.com/sgeisler/termgraph) - candle stick graphs drawn using Unicode box drawing characters, with [Colorama][] used for colors
      - [plotille](https://github.com/tammoippen/plotille) - XY plots, scatter plots, histograms and heatmaps in the terminal using braille dots
      - [termcharts](https://github.com/Abdur-RahmaanJ/termcharts/) - bar, pie, and doughnut charts, with [Rich][] compatibility
      - [plotext](https://github.com/piccolomo/plotext) - scatter, line, bar, histogram and date-time plots (including candlestick), with support for error bars and confusion matrices
      - [matplotlib-sixel](https://github.com/koppa/matplotlib-sixel) - a matplotlib backend which outputs sixel graphics onto the terminal (`matplotlib.use('module://matplotlib-sixel')`)

[click]: https://click.palletsprojects.com/
[typer]: https://typer.tiangolo.com/
[typer-config]: https://maxb2.github.io/typer-config/latest/
[typer-tools]: https://pypi.org/project/typer-tools/
[click-loglevel]: https://github.com/jwodder/click-loglevel
[git-filter-repo]: https://htmlpreview.github.io/?https://github.com/newren/git-filter-repo/blob/docs/html/git-filter-repo.html#CALLBACKS
[scrapy]: https://docs.scrapy.org/en/latest/intro/tutorial.html#creating-a-project
[sklearn]: https://scikit-learn.org/stable/modules/compose.html
[Hydra]: https://hydra.cc/
[Dynaconf]: https://www.dynaconf.com/
[configparser]: https://docs.python.org/3/library/configparser.html
[Mermaid]: https://mermaid.js.org/
[Plotly]: https://plotly.com/python/
[HoloViews]: https://holoviews.org/index.html
[Rich]: https://github.com/Textualize/rich
[Textual]: https://github.com/Textualize/textual
[Colorama]: https://github.com/tartley/colorama

[logging]: https://docs.python.org/3/library/logging.html "logging — Logging facility for Python"
[colorlog]: https://github.com/borntyping/python-colorlog "python-colorlog: A colored formatter for the python logging module"
[python-json-logger]: https://github.com/madzak/python-json-logger "python-json-logger: Json Formatter for the standard python logger"
[loguru]: https://loguru.readthedocs.io/en/stable/index.html "Loguru: Python logging made (stupidly) simple"
[structlog]: https://www.structlog.org/en/stable/ "Structlog: Structured Logging"

[MkDocs]: https://www.mkdocs.org/ "MkDocs: Project documentation with Markdown"
[mkdocs-material]: https://squidfunk.github.io/mkdocs-material/ "Material for MkDocs: Documentation framework on top of MkDocs"
[mkdocstrings]: https://mkdocstrings.github.io/ "mkdocstrings: Automatic documentation from sources, for MkDocs"
[mkdocs-manpage]: https://pawamoy.github.io/mkdocs-manpage/ "MkDocs Manpage: MkDocs plugin to generate a manpage from the documentation site"
[mkdocs-typer]: https://github.com/bruce-szalwinski/mkdocs-typer "mkdocs-typer: An MkDocs extension to generate documentation for Typer command line applications"
[Asciinema]: https://asciinema.org/ "Asciinema - Record and share your terminal sessions, the simple way"
[Terminalizer]: https://www.terminalizer.com/ "Terminalizer: Record your terminal and generate animated gif images or share a web player"
[ttyrec]: http://0xcc.net/ttyrec/ "ttyrec: a tty recorder"
[ttygif]: https://github.com/icholy/ttygif "ttygif: Convert terminal recordings to animated gifs"
[shelldemo]: https://github.com/pawamoy/shelldemo "pawamoy/shelldemo: Run a set of Bash commands as if typed by a robo- I mean, a person"

[github/linguist]: https://github.com/github/linguist
[douban/linguist]: https://github.com/douban/linguist
[retanoj/linguist]: https://github.com/retanoj/linguist
[scivision/linguist-python]: https://github.com/scivision/linguist-python

[1]: https://stackoverflow.com/questions/70387750/how-to-manage-sub-projects-in-python
[2]: https://github.com/github-linguist/linguist/blob/master/docs/overrides.md#using-gitattributes
[3]: https://stackoverflow.com/questions/70811640/using-typer-and-hydra-together

[dissection-defects4j-paper]: https://doi.org/10.1109/SANER.2018.8330203 "Sobreira et al.: 'Dissection of a bug dataset: Anatomy of 395 patches from Defects4J', SANER 2018"
[BugsInPy-paper]: https://doi.org/10.1145/3368089.3417943 "'BugsInPy: a database of existing bugs in Python programs to enable controlled testing and debugging studies', ESEC/FSE 2020"
[Herbold-paper]: https://doi.org/10.1007/s10664-021-10083-5 "Herbold et al.: 'A fine-grained data set and analysis of tangling in bug fixing commits', ESE 2022"
[HaPy-Bug-paper]: https://github.com/ncusi/python_cve_dataset_paper/ "'HaPy-Bug – Human Annotated Python Bug Resolution Dataset' (private repo with the paper)"

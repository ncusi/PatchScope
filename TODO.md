# TO DO List for Diff Annotator package

- [ ] cleanup
    - [x] cleanup annotate.py
    - [x] test annotate.py code
    - [x] test annotate.py script
    - [x] cleanup languages.py
    - [x] cleanup lexer.py
    - [x] _maybe_ move from [click][] to [typer][]
    - [ ] add docstring for all files
- [x] make it a separate package
    - [x] directory structure
    - [x] 'pyproject.toml' (and _optionally_ 'setup.py')
    - [x] 'README.md'
    - [x] 'LICENSE' (MIT License)
    - [ ] _maybe_ 'MANIFEST.in'
    - [x] separate repository on GitHub
    - [ ] move `__version__` to `__init__.py`
         (see also ["version at runtime" in setuptools_scm docs](https://setuptools-scm.readthedocs.io/en/stable/usage/#version-at-runtime)
          and ["Single-sourcing the package version" in Python Packaging User Guide](https://packaging.python.org/en/latest/guides/single-sourcing-package-version/))
    - [ ] add `docs/` directory (for man pages, and maybe API documentation)
      - [ ] use [MkDocs][] or [Material for MkDocs][mkdocs-material] for general documentation
      - [ ] generate API documentation using [mkdocstrings][]
      - [ ] _maybe_ generate manpages from MkDocs with [mkdocs-manpage][] (at least for scripts)
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
    - [ ] support [.gitattributes overrides of GitHub Linguist][2]
    - [x] optionally use Python clone of [github/linguist][], namely [retanoj/linguist][], installed from GitHub,
          with `--use-pylinguist` (note: [install requires libmagic-dev and libicu-dev libraries](https://github.com/douban/linguist/issues/25))
        - [x] make it use newer version of `languages.yml` by default 
    - [ ] optionally use Python wrapper around [github/linguist][], ~~namely [scivision/linguist-python][],~~
          with `--use-ghlinguist` (e.g. via [RbCall](https://github.com/yohm/rb_call),
          or ~~via [rython](https://pypi.org/project/rython/)~~,
          or other technique) 
    - [x] configurable line annotation based on file ~~type~~ purpose
        - [x] `PURPOSE_TO_ANNOTATION` global variable
        - [x] global option `--purpose-to-annotation` in [`annotate.py`](src/diffannotator/annotate.py) script
    - [ ] configurable line annotation based on tokens
    - [x] computing patch/diff size and spread, following
          _"[Dissection of a bug dataset: Anatomy of 395 patches from Defects4J](https://doi.org/10.1109/SANER.2018.8330203)"_
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
    - [ ] global option `--output-format` (json, _maybe_ jsonlines, csv, parquet,...)
    - [ ] option or subcommand to output flow diagram using 
      [Mermaid][] diagramming language (optionally wrapped in Markdown block)
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
[git-filter-repo]: https://htmlpreview.github.io/?https://github.com/newren/git-filter-repo/blob/docs/html/git-filter-repo.html#CALLBACKS
[scrapy]: https://docs.scrapy.org/en/latest/intro/tutorial.html#creating-a-project
[sklearn]: https://scikit-learn.org/stable/modules/compose.html
[Hydra]: https://hydra.cc/
[Dynaconf]: https://www.dynaconf.com/
[configparser]: https://docs.python.org/3/library/configparser.html
[Mermaid]: https://mermaid.js.org/
[Rich]: https://github.com/Textualize/rich
[Textual]: https://github.com/Textualize/textual
[Colorama]: https://github.com/tartley/colorama

[MkDocs]: https://www.mkdocs.org/ "MkDocs: Project documentation with Markdown"
[mkdocs-material]: https://squidfunk.github.io/mkdocs-material/ "Material for MkDocs: Documentation framework on top of MkDocs"
[mkdocstrings]: https://mkdocstrings.github.io/ "mkdocstrings: Automatic documentation from sources, for MkDocs"
[mkdocs-manpage]: https://pawamoy.github.io/mkdocs-manpage/ "MkDocs Manpage: MkDocs plugin to generate a manpage from the documentation site"
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

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
    - [ ] _maybe_ use build tool like Poetry, Hatch, PDM, Rye, uv, Flit,...
    - [ ] _maybe_ use in HaPy-Bug (python_bug_dataset) [via a GitHub URL][1]
- [x] ~~3~~ 4 scripts _(their names may change in the future)_ - see `[project.scripts]` section
  in [`pyproject.toml`](pyproject.toml)
    - [x] `diff-generate` (from [`generate_patches.py`](src/diffannotator/generate_patches.py))
    - [x] `diff-annotate` (from [`annotate.py`](src/diffannotator/annotate.py))
    - [x] `diff-gather-stats` (from [`gather_data.py`](src/diffannotator/gather_data.py))
    - [ ] `diff-augment` - augment JSON files with data from Git or from GitHub
- [ ] improvements and new features for `generate_patches.py`
    - [ ] configure what and where to output
        - [x] `--use-fanout` 
          (e.g. save result in 'c0<b>/</b>dcf39b046d1b4ff6de14ac99ad9a1b10487512.diff'
          instead of in '0001-Create-.gitignore-file.patch');<br>
          **NOTE**: this required switching from using `git format-patch`
          to using `git log -p`, and currently does not save the commit message.
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

[github/linguist]: https://github.com/github/linguist
[douban/linguist]: https://github.com/douban/linguist
[retanoj/linguist]: https://github.com/retanoj/linguist
[scivision/linguist-python]: https://github.com/scivision/linguist-python

[1]: https://stackoverflow.com/questions/70387750/how-to-manage-sub-projects-in-python
[2]: https://github.com/github-linguist/linguist/blob/master/docs/overrides.md#using-gitattributes
[3]: https://stackoverflow.com/questions/70811640/using-typer-and-hydra-together

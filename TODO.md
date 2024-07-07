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
    - [ ] _maybe_ use build tool like Poetry, Hatch, PDM, Rye, uv, Flit,...
    - [ ] _maybe_ use in HaPy-Bug (python_bug_dataset) [via a GitHub URL][1]
- [ ] improvements and new features
    - [ ] parse whole pre-image and post-image files
          (via Git, or via GitHub / GitLab / ...)
    - [ ] configurable file type
        - [x] global option `--ext-to-language` (the API it uses already existed)
    - [ ] support [.gitattributes overrides of GitHub Linguist][2]
    - [x] configurable line annotation based on file ~~type~~ purpose
        - [x] `PURPOSE_TO_ANNOTATION` global variable
        - [x] global option `--purpose-to-annotation` in [`annotate.py`](src/diffannotator/annotate.py) script
    - [ ] configurable line annotation based on tokens
    - [ ] configuration file (*.toml, *.yaml, *.json, *.ini, *.cfg, or *.py)
    - [ ] documentation on how to use API, and change behavior
    - [ ] configure output format (and what to output)
    - [ ] _maybe_ configuration options
    - [ ] _maybe_ configuration callbacks (in Python), like in [git-filter-repo][]
        - [x] `AnnotatedPatchedFile.line_callback` static field
        - [x] global option `--line-callback` in [`annotate.py`](src/diffannotator/annotate.py) script
    - [ ] _maybe_ generate skeleton, like a framework, like in [Scrapy][scrapy]
    - [ ] _maybe_ provide an API to generate processing pipeline, like in [SciKit-Learn][sklearn]

[click]: https://click.palletsprojects.com/
[typer]: https://typer.tiangolo.com/
[git-filter-repo]: https://htmlpreview.github.io/?https://github.com/newren/git-filter-repo/blob/docs/html/git-filter-repo.html#CALLBACKS
[scrapy]: https://docs.scrapy.org/en/latest/intro/tutorial.html#creating-a-project
[sklearn]: https://scikit-learn.org/stable/modules/compose.html

[1]: https://stackoverflow.com/questions/70387750/how-to-manage-sub-projects-in-python
[2]: https://github.com/github-linguist/linguist/blob/master/docs/overrides.md#using-gitattributes

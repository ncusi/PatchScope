# TO DO List for Diff Annotator package

- [ ] cleanup
    - [x] cleanup annotate.py
    - [x] test annotate.py code
    - [ ] test annotate.py script
    - [ ] cleanup languages.py
    - [ ] cleanup lexer.py
    - [ ] _maybe_ move from [click][] to [typer][]
    - [ ] add docstring for all files
- [ ] make it a separate package
    - [ ] directory structure
    - [ ] 'pyproject.toml' (and _optionally_ 'setup.py')
    - [ ] 'README.md'
    - [ ] 'LICENSE' (MIT License)
    - [ ] _maybe_ 'MANIFEST.in'
    - [ ] separate repository on GitHub
    - [ ] _maybe_ use build tool like Poetry, Hatch, PDM, Rye, uv, Flit,...
    - [ ] _maybe_ use in HaPy-Bug (python_bug_dataset) [via a GitHub URL][1]
- [ ] improvements and new features
    - [ ] parse whole pre-image and post-image files
          (via Git, or via GitHub / GitLab / ...)
    - [ ] configurable file type
    - [ ] support [.gitattributes overrides of GitHub Linguist][2]
    - [x] configurable line annotation based on file type
    - [ ] configurable line annotation based on tokens
    - [ ] configuration file (*.toml, *.yaml, *.json, *.ini, *.cfg, or *.py)
    - [ ] documentation on how to use API, and change behavior
    - [ ] configure output format (and what to output)
    - [ ] _maybe_ configuration options
    - [ ] _maybe_ configuration callbacks (in Python)
    - [ ] _maybe_ generate skeleton, like a framework

[click]: https://click.palletsprojects.com/
[typer]: https://typer.tiangolo.com/

[1]: https://stackoverflow.com/questions/70387750/how-to-manage-sub-projects-in-python
[2]: https://github.com/github-linguist/linguist/blob/master/docs/overrides.md#using-gitattributes
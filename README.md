[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)

# Diff Annotator

Annotates files and lines of diffs (patches) with their purpose and type,
and performs statistical analysis on the generated annotation data.

## Development

### Virtual environment

To avoid dependency conflicts, it is strongly recommended to create
a [virtual environment][venv], for example with:
```commandline
python -m venv .venv
```

This needs to be done only once, from top directory of the project.
For each session, you should activate the environment:
```commandline
source .venv/bin/activate
```

Using virtual environment, either directly like shown above, or
by using `pipx`, might be required if you cannot install system
packages, but Python is configured in a very specific way:

> error: externally-managed-environment
>
> × This environment is externally managed

[venv]: https://python.readthedocs.io/en/stable/library/venv.html

### Installing the package in editable mode

To install the project in editable mode (from top directory of this repo):
```commandline
python -m pip install -e .
```

To be able to also run test, use:
```commandline
python -m pip install --editable .[dev]
```

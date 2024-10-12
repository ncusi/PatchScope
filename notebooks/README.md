# Jupyter Notebooks

This directory contains Jupyter Notebooks used to compute and visualize data
generated with the help of this package.

This directory includes the following notebooks:

- [`01-gather_data-explore.ipynb`](./01-gather_data-explore.ipynb)
  analyzes and visualizes results of running `diff-gather-stats`
  (source: [`gather_data.py`](../src/diffannotator/gather_data.py))
  and it's various subcommands, using annotations generated with
  `diff-annotate from-repo`.

## Running notebooks

If needed, install required packages with
```commandline
python -m pip install --upgrade -r notebooks/requirements.txt
```
when in the top directory of the project (or use simply
[`requirements.txt`](./requirements.txt) when in `notebooks/`
directory, that is in this directory).

It is recommended to use virtual environment, see the information in
the main `README.md` file: [_Virtual environment_](../README.md#virtual-environment).

Once installed, launch JupyterLab with:
```commandline
jupyter lab
```

## Development

You can install recommended packages with
```commandline
python -m pip install --upgrade -r notebooks/requirements-dev.txt
```
when in the top directory of the project (or use simply
[`requirements-dev.txt`](./requirements-dev.txt) when in `notebooks/`
directory, that is in this directory).

The [`.gitignore`](.gitignore) file, [`.gitattributes`](.gitattributes) file,
and [`requirements.txt`](requirements.txt) and [`requirements-dev.txt`](requirements-dev.txt)
files are local to this directory, and are about Jupyter Notebooks that are
here.

You can use `nbdime` for diffing and merging of Jupyter notebooks.
The `.gitattribute` file is committed to the repository, but it needs Git config
to work.  You can add it with the following command (after installing `nbdime`):
```commandline
nbdime config-git --enable
```
See [_Git integration_](https://nbdime.readthedocs.io/en/latest/vcs.html#git-integration)
section in the nbdime documentation.

Try to commit notebooks in a well-defined and consistent state,
for example by restarting the kernel and re-running all cells
before committing.

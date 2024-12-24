# Jupyter Notebooks

This directory contains Jupyter Notebooks used to compute and visualize data
generated with the help of this package.

This directory includes the following notebooks:

- [`01-gather_data-explore.ipynb`](./01-gather_data-explore.ipynb)
  analyzes and visualizes results of running `diff-gather-stats`
  (source: [`gather_data.py`](../src/diffannotator/gather_data.py))
  and it's various subcommands, using annotations generated with
  `diff-annotate from-repo`.

## `panel` and `bokeh` subdirectories

The **`bokeh/`** subdirectory contains some Python scripts that
create various interactive plots to visualize annotation results.
Plots are created using the [Bokeh][][^bokeh] library.

[^bokeh]: Bokeh is an interactive visualization library for modern web browsers.

The **`panel/`** subdirectory contains Jupyter notebooks (`*.ipynb`)
and Python scripts (`*.py`), which use [Panel][][^panel] (member of the [HoloViz][] ecosystem)
to explore various way of interactively visualizing and analysing
annotation results; though some are there just to explore [Panel][] features.
See its [`panel/README.md`](./panel/README.md).

[^panel]: Panel is an open-source Python library designed to streamline the development of robust tools, dashboards, and complex applications entirely within Python.

[Bokeh]: https://bokeh.org/
[Panel]: https://panel.holoviz.org/
[HoloViz]: https://holoviz.org/

## `experiments` subdirectory

The **`experiments/` subdirectory contains Jupyter notebooks that are part
of comparing automatic line annotations from this tool (PatchScope), with
different datasets that include manual line annotations.

- [`00-HaPy_Bug-Paper.ipynb`](./experiments/00-HaPy_Bug-Paper.ipynb)
  reproduces results in the HaPy-Bug paper[^hapy-bug].
- [`01-compare_annotations.ipynb`](./experiments/01-compare_annotations.ipynb)
  compares automatic annotations from PatchScope with manual annotations
  in BugsInPy subset of HaPy-Bug dataset.
- [`02-compare_annotations_Herbold.ipynb`](./experiments/02-compare_annotations_Herbold.ipynb)
  compares automatic annotations from PatchScope with manual annotations
  from Herbold et al. paper[^herbold].

[^hapy-bug]: Piotr Przymus, Mikołaj Fejzer, Jakub Narębski, Radosław Woźniak, Łukasz Halada, Aleksander Kazecki, Mykhailo Molchanov and Krzysztof Stencel _"HaPy-Bug – Human Annotated Python Bug Resolution Dataset"_ (2024)

[^herbold]: Steffen Herbold et al. _"A fine-grained data set and analysis of tangling in bug fixing commits"_ https://doi.org/10.1007/s10664-021-10083-5

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

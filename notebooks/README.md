# Jupyter Notebooks

This directory contains Jupyter Notebooks used to compute and visualize data
generated with the help of this package.

This directory includes the following notebooks:

- ...

## Running notebooks

If needed, install required packages with
```commandline
python -m pip install --upgrade -r requirements.txt
```
It is recommended to use virtual environment, see the information in
the main `README.md` file: [_Virtual environment_](../README.md#virtual-environment).

Once installed, launch JupyterLab with:
```commandline
jupyter lab
```

## Development

You can install recommended packages with
```commandline
python -m pip install --upgrade -r requirements-dev.txt
```

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
See 
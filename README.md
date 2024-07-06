[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)
[![EditorConfig](https://img.shields.io/badge/Editor%20Config-E0EFEF?logo=editorconfig&logoColor=000)](https://editorconfig.org/)
[![Maturity badge - level 1](https://img.shields.io/badge/Maturity-Level%201%20--%20New%20Project-yellow.svg)](https://github.com/tophat/getting-started/blob/master/scorecard.md)

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

## Related

Here are some related projects that can also be used
to extract development statistics from project or a repository.

Command line and terminal interface tools:

- [`git-quick-stats`](https://git-quick-stats.sh/)
  is a simple and efficient way to access various statistics in a git repository
- [`git-stats`](https://github.com/IonicaBizau/git-stats)
  provides local git statistics, including GitHub-like contributions calendars
- [`git_dash.sh`](https://github.com/darul75/git_dash) is a command-line shell script
  for generating a Git metrics dashboard directly in your terminal
- [`heatwave`](https://github.com/james-stoup/heatwave)
  visualizes your git commits with a heat map in the terminal,
  similar to how GitHub's heat map looks
- [`statscat`](https://github.com/z1cheng/statscat)
  is a CLI tool to get statistics of your all git repositories
- [hxtools](http://inai.de/projects/hxtools/) by Jan Engelhardt
  is a collection of small tools and scripts, which include
  `git-author-stat` (commit author statistics of a git repository),
  `git-blame-stat` (per-line author statistics), and
  `git-revert-stats` (reverting statistics)
- [git-fame](https://github.com/casperdcl/git-fame) (in Python) and
  [git-fame-rb](https://github.com/oleander/git-fame-rb) (in Ruby)
  are command-line tools to pretty-print Git repository collaborators
  sorted by contributions
- [`git-of-theseus`](https://github.com/erikbern/git-of-theseus) is a set of scripts
  to analyze how a Git repo grows over time.
  -See [The half-life of code & the ship of Theseus](https://erikbern.com/2016/12/05/the-half-life-of-code.html)
      by Erik Bernhardsson (2016).
- GitHub [Linguist](https://github.com/github-linguist/linguist)
  can also be used from the command line, using the `github-linguist` executable
  to generate repository's languages stats
  (the language breakdown by percentage and file size),
  also for selected revision
- [cregit](https://github.com/cregit/cregit)
  is a tool for helping to find and analyse code credits
  (unify identities, find contribution by token,
  extract metadata into a SQLite database, etc.)
- [git-metrics](https://github.com/Praqma/git-metrics) tool
  is a set of util scripts to scrape data from git repositories
  to help teams improve (metrics such as lead time and open branches)

Tools to generate HTML dashboard, or providing an interactive web application:

- [GitStats](https://github.com/akashraj9828/gitstats)
  is an open source GitHub contribution analyzer, providing live dashboard;<br>
  **note** that [gitstats.me](https://gitstats.me/) no longer works
  (the domain is parked for sale)
- [`repostat`](https://github.com/vifactor/repostat)
  is Git repository analyser and HTML-report generator
  with [NVD3](https://nvd3.org/)-driven interactive metrics visualisations;<br>
  **note** that demo site <https://repostat.imfast.io/> no longer works
  - [NVD3.js](https://nvd3.org/) is an attempt to build re-usable charts
    and chart components for [d3.js](http://d3js.org/)
- [Repositorch](https://github.com/kirnosenko/Repositorch)
  is a Git repository analysis engine written in C#;
  it recommends using Docker Compose to install
  ([Repositorch on Docker Hub](https://hub.docker.com/r/kirnosenko/repositorch))<br>
  no demo site, but there is "[How to use Repositorch](https://www.youtube.com/watch?v=Rd5R0BbFdGA)"
  video on YouTube
- [Githru](https://github.com/githru/githru) is an interactive visual analytics system
  that enables developers to effectively understand the context of development history
  through the [interactive exploration of Git and GitHub metadata (demo)](https://githru.github.io/demo/).
  It uses [novel techniques (paper)](https://arxiv.org/abs/2009.03115) (graph reconstruction,
  clustering, and Context-Preserving Squash Merge (CSM) methods) to abstract
  a large-scale Git commit graph.

Visualizations for a specific repository:

- [A Git history visualization page](https://git-history.jpalmer.dev/)
  by Jeff Palmer shows _"An Interactive Development History"_ of Git:
  project and contributor statistics, relative cumulative contributions
  by contributor, and aggregated commits by contributor by month
  with milestone annotations.
  Jeff wrote [an associated blog post](https://jpalmer.dev/2021/05/interactive-git-history/)
  about how he created the visualization.
- [`gitdm`](https://github.com/npalix/gitdm) (the "git data miner")
  is the tool that Greg KH and Jonathan Corbet have used
  to create statistics on where kernel patches come from.
  Written in Python.  Original at `git://git.lwn.net/gitdm.git`

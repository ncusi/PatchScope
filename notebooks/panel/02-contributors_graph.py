import datetime
import json
import logging
from pathlib import Path
from typing import Optional

# data analysis
import numpy as np
import pandas as pd

# dashboard
import panel as pn

# plotting
import hvplot.pandas  # noqa


logger = logging.getLogger("panel.contributors_graph")
pn.extension("jsoneditor",
             design="material", sizing_mode="stretch_width")

DATASET_DIR = 'data/examples/stats'


def find_dataset_dir() -> Optional[Path]:
    for TOP_DIR in ['', '..', '../..']:
        #print(f"find_dataset_dir(): {TOP_DIR}")
        full_dir = Path(TOP_DIR).joinpath(DATASET_DIR)

        if full_dir.is_dir():
            #print(f"find_dataset_dir(): found {full_dir}")
            return full_dir

    return None


def find_timeline_files(dataset_dir: Optional[Path]) -> list[Path]:
    if dataset_dir is None:
        #print(f"find_timeline_files({dataset_dir=}): []")
        return []
    else:
        # assuming naming convention for file names
        #print(f"find_timeline_files({dataset_dir=}): searching...")
        res = {
            str(path.stem): str(path) 
            for path in dataset_dir.glob('*.timeline.*.json')
        }
        #print(f" -> {res}")
        return res


@pn.cache
def get_timeline_data(json_path: Path) -> dict:
    logger.debug(f"[@pn.cache] get_timeline_data() for {json_path=}")
    with open(json_path, mode='r') as json_fp:
        return json.load(json_fp)


def find_repos(timeline_data: dict):
    return list(timeline_data.keys())


select_file_widget = pn.widgets.Select(name="input JSON file", options=find_timeline_files(find_dataset_dir()))

get_timeline_data_rx = pn.rx(get_timeline_data)(
    json_path=select_file_widget,
)
find_repos_rx = pn.rx(find_repos)(
    timeline_data=get_timeline_data_rx,
)
select_repo_widget = pn.widgets.Select(name="repository", options=find_repos_rx, disabled=len(find_repos_rx.rx.value) <= 1)

html_head_text_rx = pn.rx("""
<h1>Contributors to {repo}</h1>
""").format(repo=select_repo_widget)

if pn.state.location:
    pn.state.location.sync(select_file_widget, {'value': 'file'})
    pn.state.location.sync(select_repo_widget, {'value': 'repo'})

template = pn.template.MaterialTemplate(
    site="diffannotator",
    title="Contributors Graph",  # TODO: make title dynamic
    sidebar_width=350,
    sidebar=[
        select_file_widget,
        select_repo_widget,
    ],
    main=[
        pn.Column(
            pn.pane.HTML(html_head_text_rx),
        )
    ]
)
template.servable()

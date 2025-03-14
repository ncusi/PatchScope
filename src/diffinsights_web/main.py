#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path

import panel as pn
import typer
from typing_extensions import Annotated

from diffinsights_web import datastore


app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def main(
    dataset_dir: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Path to directory with *.timeline.*.json files",
        )
    ],
):
    datastore.DATASET_DIR = str(dataset_dir)

    # NOTE: imports must be after setting diffinsights_web.datastore.DATASET_DIR
    from diffinsights_web.apps.author import template as author_app
    from diffinsights_web.apps.contributors import template as contributors_app

    # run the application in a development server
    pn.serve(
        {
            'contributors': contributors_app,
            'author': author_app,
        },
        address="0.0.0.0",
        port=7860,
        websocket_origin="*",
        show=False,

        # NOTE: missing equivalents of --reuse-sessions, --global-loading-spinner
    )


if __name__ == "__main__":
    main()

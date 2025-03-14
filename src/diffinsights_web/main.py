#!/usr/bin/env python
# -*- coding: utf-8 -*-
import panel as pn

from diffinsights_web.apps.author import template as author_app
from diffinsights_web.apps.contributors import template as contributors_app


def main():
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

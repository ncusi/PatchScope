import datetime
import hashlib
import json
import logging
import os
import re
from collections import namedtuple
from io import StringIO
from pathlib import Path
from textwrap import dedent
from typing import Optional
from urllib.parse import urlencode

# data analysis
import pandas as pd

# dashboard
import panel as pn
import param

from panel_mermaid import MermaidDiagram, MermaidConfiguration

pn.extension()

# See https://mermaid.js.org/schemas/config.schema.json
class MermaidSankeyConfiguration(pn.viewable.Viewer, pn.widgets.WidgetBase):
    """An interactive Widget for editing the Mermaid JS configuration for Sankey diagram.

    See https://mermaid.js.org/schemas/config.schema.json
    See https://mermaid.js.org/config/schema-docs/config.html#definitions-group-sankeydiagramconfig

    Example:

    >>> config = MermaidSankeyConfiguration()

    You can use it as a *reference value* for the MermaidDiagram:

    >>> diagram = MermaidDiagram(
    ...    object="sankey-beta\\n\\n%% source,target,value\\n...",
    ...    configuration=config,
    ... )
    """
    # based on MermaidConfiguration from panel_mermaid
    # https://github.com/awesome-panel/panel-mermaid/blob/main/src/panel_mermaid/mermaid.py
    value: dict = param.Dict(
        constant=True,
        doc="""The Mermaid JS configuration for Sankey diagram.""",
    )

    showValues: bool = param.Boolean(
        default=True,
        doc="""Toggle to display or hide values along with title."""
    )
    linkColor: str = param.Selector(
        default="gradient",
        objects=["source", "target", "gradient"],
        doc=dedent(
            """
            The color of the links in the Sankey diagram:

            - `source` - link will be of a source node color
            - `target` - link will be of a target node color
            - `gradient` - link color will be smoothly transient between source and target node colors
            - hex code of color, like `#a1a1a1` (unsupported)
            """
        )
    )
    nodeAlignment: str = param.Selector(
        default="justify",
        objects=["left", "right", "center", "justify"],
        doc=dedent(
            """
            Defines graph layout of Sankey diagram:

            - `left` - Align all inputs to the left.
            - `right` - Align all outputs to the right.
            - `center` - Like `left`, except that nodes without any incoming links are moved as right as possible.
            - `justify` - Like `left`, except that nodes without any outgoing links are moved to the far right.
            """
        )
    )
    width: int = param.Integer(
        default=600,
        bounds=(0, None),
        doc="""Height of the diagram""",
    )
    height: int = param.Integer(
        default=400,
        bounds=(0, None),
        doc="""Width of the diagram""",
    )
    useMaxWidth: bool = param.Boolean(
        default=False,
        doc=dedent(
            """\
            When this flag is set to `True`, the height and width is set to 100%
            and is then scaled with the available space.
            If set to `False`, the absolute space required is used.
            """
        ),
    )
    prefix: str = param.String(
        default="",
        doc="""The prefix to use for values""",
    )
    suffix: str = param.String(
        default="",
        doc="""The suffix to use for values""",
    )

    def __init__(self, **params):
        super().__init__(**params)

    @param.depends(
        "showValues", "linkColor", "nodeAlignment",
        "useMaxWidth", "width", "height", "prefix", "suffix",
        watch=True, on_init=True
    )
    def _update_value(self):
        value = {
            'sankey': {
                "showValues": self.showValues,
                "linkColor": self.linkColor,
                "nodeAlignment": self.nodeAlignment,
                "useMaxWidth": self.useMaxWidth,
                "width": self.width,
                "height": self.height,
                "prefix": self.prefix,
                "suffix": self.suffix,
            },
        }
        value['sankey'] = {
            key: val
            for key, val in value['sankey'].items()
            if val is not None and val != self.param[key].default
        }
        if not value['sankey']:
            value = {}

        with param.edit_constant(self):
            self.value = value

    def widgets(self):
        return [
            self.param.showValues,
            self.param.linkColor,
            self.param.nodeAlignment,
            self.param.useMaxWidth,
            self.param.width,
            self.param.height,
            self.param.prefix,
            self.param.suffix,
        ]

    def __panel__(self):
        return pn.Column(
            *self.widgets()
        )


configuration = MermaidSankeyConfiguration(
    showValues = False,
)
print(repr(configuration))
print(configuration.value)
diagram = MermaidDiagram(
    object=dedent(
        """
        sankey-beta

        %% source,target,value
        Electricity grid,Over generation / exports,104.453
        Electricity grid,Heating and cooling - homes,113.726
        Electricity grid,H2 conversion,27.14
        """
    ),
    configuration=configuration,
    update_value=True,
    width=800,
    height=400,
)

pn.FlexBox(
    configuration,
    pn.Column(
        diagram,
        #diagram.param.update_value,
        pn.widgets.FileDownload(
            file=pn.bind(StringIO, diagram.param.value), filename="diagram.svg"
        ),
    ),
).servable()


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

from panel_mermaid import MermaidDiagram, MermaidConfiguration

pn.extension()

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
    configuration={
        'sankey': {
            'width':  800,
            'height': 400,
            'showValues': False,
        },
    },
    update_value=True,
    width=800,
    height=400,
)

pn.Column(
    diagram,
    #diagram.param.update_value,
    pn.widgets.FileDownload(
        file=pn.bind(StringIO, diagram.param.value), filename="diagram.svg"
    ),
).servable()


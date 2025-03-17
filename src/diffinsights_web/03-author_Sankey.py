import datetime
import hashlib
import json
import logging
import os
import re
from collections import namedtuple
from io import StringIO
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

# data analysis
import pandas as pd

# dashboard
import panel as pn

from panel_mermaid import MermaidDiagram, MermaidConfiguration

pn.extension()

configuration = MermaidConfiguration(look="handDrawn", theme="forest")
diagram = MermaidDiagram(
    object=(
        """
        graph LR
            A[Hello] --> B[Panel] --> E[World]
            A-->C(Mermaid) --> E ;
        """
    ),
    configuration=configuration,
    update_value=True,
)

pn.FlexBox(
    configuration,
    diagram,
    #diagram.param.update_value,
    pn.widgets.FileDownload(
        file=pn.bind(StringIO, diagram.param.value), filename="diagram.svg"
    ),
).servable()


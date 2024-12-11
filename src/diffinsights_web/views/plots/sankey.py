from pathlib import Path
from typing import Optional

import holoviews as hv
import pandas as pd
import panel as pn
import param

from diffinsights_web.datastore.linesstats import LinesStatsDataStore


def sankey_plot_from_triples(sankey_data: list[tuple[str, str, int]],
                             width: int = 800,
                             height: int = 400) -> hv.Sankey:
    return hv.Sankey(sankey_data).opts(
        edge_color_index=1,
        width=width,
        height=height,
    )


def sankey_plot_from_df(sankey_df: pd.DataFrame,
                        width: int = 800,
                        height: int = 400) -> hv.Sankey:
    return hv.Sankey(
        sankey_df[['from', 'to', 'count']]
    ).opts(
        # formatting
        label_position='outer',
        node_color='index',
        edge_color_index=1,
        # size
        width=width,
        height=height,
        # tools
        default_tools=[],
        # active_tools=['hover'],  # does not work, causes strange error
        tools=[
            'pan',
            'box_zoom',
            'save',
            'reset',
            'hover',
        ],
    )


def plot_sankey(sankey_df: pd.DataFrame,
                data_store: LinesStatsDataStore,
                width: int = 1000,
                height: int = 400):
    if isinstance(sankey_df, param.rx):
        sankey_df = sankey_df.rx.value

    timeseries_file = data_store.timeseries_file

    if sankey_df is None or len(sankey_df) == 0:  # or df.shape[0]
        return pn.pane.HTML(
            "<p>No data needed to create Sankey diagram found for "
            f"<tt>{Path(timeseries_file).name!r}</tt></p>")
    else:
        #print(f"plot_sankey(): {type(sankey_data)=}")
        return pn.Column(
            data_store,
            sankey_plot_from_df(sankey_df, width, height),
        )


class SankeyPlot(pn.viewable.Viewer):
    data_store = param.ClassSelector(class_=LinesStatsDataStore)
    # allow_refs=True is here to allow widgets
    from_date_str = param.String(allow_refs=True)  # TODO: implement support for it

    def __init__(self, **params):
        super().__init__(**params)

        self.plot_sankey_rx = pn.rx(plot_sankey)(
            sankey_df=self.data_store.sankey_df_rx,
            data_store=self.data_store,
            #timeseries_file=self.data_store.param.timeseries_file.rx(),
        )

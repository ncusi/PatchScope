from typing import Optional

import holoviews as hv
import panel as pn
import param

from diffinsights_web.datastore.linesstats import LinesStatsDataStore


def sankey_plot_from_triples(sankey_data: list[tuple[str, str, int]],
                             width: int = 800,
                             height: int = 400) -> hv.Sankey:
    return hv.Sankey(sankey_data).opts(
        edge_color_index=1,
        width=width,
        height=height
    )


def plot_sankey(sankey_data: Optional[list[tuple[str, str, int]]],
                timeline_file: str,
                width: int = 800,
                height: int = 400):
    if sankey_data is None:
        return pn.pane.HTML(f"No data needed to create Sankey diagram found for {timeline_file!r}")
    else:
        return sankey_plot_from_triples(sankey_data, width, height)


class SankeyPlot(pn.viewable.Viewer):
    data_store = param.ClassSelector(class_=LinesStatsDataStore)
    # allow_refs=True is here to allow widgets
    from_date_str = param.String(allow_refs=True)  # TODO: implement support for it

    def __init__(self, **params):
        super().__init__(**params)

        self.plot_sankey_rx = pn.rx(plot_sankey(
            sankey_data=self.data_store.sankey_data_rx,
            timeline_file=self.data_store.timeline_file,
        ))

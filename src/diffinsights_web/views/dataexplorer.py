import panel as pn

from diffinsights_web.views import TimelineView


class TimelineJSONViewer(TimelineView):
    def __panel__(self):
        return pn.widgets.JSONEditor(
            value=self.data_store.timeline_data_rx,
            mode='view',
            menu=True, search=True,
            width_policy='max',
            height=500,
        )

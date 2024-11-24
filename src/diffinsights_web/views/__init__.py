import panel as pn
import param

from diffinsights_web.datastore.timeline import TimelineDataStore


class TimelineView(pn.viewable.Viewer):
    """Base class for different views that display data from TimelineDataStore"""
    data_store = param.ClassSelector(class_=TimelineDataStore)

    def __init__(self, **params):
        super().__init__(**params)

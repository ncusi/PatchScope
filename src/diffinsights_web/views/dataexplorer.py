import panel as pn
import param

from diffinsights_web.datastore.timeline import ResampledTimelineDataStore
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


class TimelinePerspective(TimelineView):
    title = param.String(
        None,  # NOTE: `None` means generate value in constructor
        allow_refs=True,  # allow for reactive expressions:
        # https://param.holoviz.org/user_guide/References.html#other-reference-types
    )

    def __init__(self, **params):
        super().__init__(**params)

        if self.title is None:
            self.title = pn.rx("Perspective: repo={repo!r}") \
                .format(repo=self.data_store.select_repo_widget)

    def __panel__(self):
        return pn.pane.Perspective(
            self.data_store.timeline_df_rx,
            title=self.title,
            editable=False,
            width_policy='max',
            height=500,
        )


# TODO?: remove this code duplication
class ResampledTimelinePerspective(pn.viewable.Viewer):
    data_store = param.ClassSelector(class_=ResampledTimelineDataStore)

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        return pn.pane.Perspective(
            self.data_store.resampled_timeline_rx,
            title=self.data_store.title,
            editable=False,
            width_policy='max',
            height=500,
        )

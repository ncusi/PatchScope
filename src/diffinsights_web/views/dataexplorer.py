from enum import Enum

import panel as pn

from diffinsights_web.views import TimelineView


class TimelineDataFrameEnum(Enum):
    TIMELINE_DATA = 'data'
    RESAMPLED_DATA = 'resampled'
    BY_AUTHOR_DATA = 'by author+resampled'


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
    def panel(self, dataframe: TimelineDataFrameEnum = TimelineDataFrameEnum.TIMELINE_DATA):
        if dataframe == TimelineDataFrameEnum.RESAMPLED_DATA:
            df_rx = self.data_store.resampled_timeline_all_rx
            title = pn.rx("Perspective: repo={repo!r}, resample={resample!r} all") \
                .format(repo=self.data_store.select_repo_widget, resample=self.data_store.resample_frequency_widget)
        elif dataframe == TimelineDataFrameEnum.BY_AUTHOR_DATA:
            df_rx = self.data_store.resampled_timeline_by_author_rx
            title = pn.rx("Perspective: repo={repo!r}, resample={resample!r} by author") \
                .format(repo=self.data_store.select_repo_widget, resample=self.data_store.resample_frequency_widget)
        else:
            # dataframe == TimelineDataFrameEnum.TIMELINE_DATA:
            df_rx = self.data_store.timeline_df_rx
            title = pn.rx("Perspective: repo={repo!r}") \
                .format(repo=self.data_store.select_repo_widget)

        return pn.pane.Perspective(
            df_rx,
            title=title,
            editable=False,
            width_policy='max',
            height=500,
        )

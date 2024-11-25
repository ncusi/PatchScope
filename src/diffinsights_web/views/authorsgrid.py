from typing import Optional

import pandas as pd
import panel as pn
import param

from diffinsights_web.datastore.timeline import author_timeline_df
from diffinsights_web.views import TimelineView
from diffinsights_web.views.dataexplorer import perspective_pane


def authors_list(authors_df: pd.DataFrame,
                 top_n: Optional[int] = None) -> list[str]:
    # TODO: return mapping { "[name] <[email]>": "[email]",... },
    #       instead of returning list of emails [ "[email]",... ]
    if top_n is None:
        return authors_df.index.to_list()
    else:
        return authors_df.head(top_n).index.to_list()


class AuthorInfo(TimelineView):
    # NOTE: without `allow_refs=True`, there is a bug in 'param'(?) when trying to create warning
    authors_info_df = param.ClassSelector(class_=pd.DataFrame, allow_refs=True)

    def __init__(self, **params):
        super().__init__(**params)

        # might be not a Select widget
        self.top_n_widget = pn.widgets.Select(
            name="top N",
            options=[4, 10, 32],
            value=4,
        )

        self.authors_list_rx = pn.rx(authors_list)(
            authors_df=self.authors_info_df,
            top_n=self.top_n_widget,
        )
        self.select_author_widget = pn.widgets.Select(
            name="author",
            options=self.authors_list_rx,
        )
        self.author_timeline_df_rx = pn.rx(author_timeline_df)(
            resample_by_author_df=self.data_store.resampled_timeline_by_author_rx,
            author_id=self.select_author_widget,
        )

    def widgets(self) -> list[pn.viewable.Viewable]:
        return [
            self.top_n_widget,
        ]

    def __panel__(self) -> pn.viewable.Viewable:
        return pn.Column(
            self.select_author_widget,
            perspective_pane(
                df=self.author_timeline_df_rx,
                title=pn.rx("repo={repo!r}, author={author!r}").format(
                    repo=self.data_store.select_repo_widget,
                    author=self.select_author_widget,
                ),
            ),
        )

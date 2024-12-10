from collections import namedtuple
from typing import Optional

import pandas as pd
import panel as pn
import param

from diffinsights_web.datastore.timeline import author_timeline_df
from diffinsights_web.utils.avatars import gravatar_url
from diffinsights_web.utils.humanize import html_int_humane
from diffinsights_web.views import TimelineView
from diffinsights_web.views.dataexplorer import perspective_pane
from diffinsights_web.views.info import ContributionsPercHeader
from diffinsights_web.views.plots.timeseries import TimeseriesPlotForAuthor, TimeseriesPlot


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
            options=[2, 4, 10, 32],
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
        self.top_n_widget.param.watch(
            fn=lambda _: self._update_select_author_widget(),
            parameter_names=['value'],
            what='value',
            onlychanged=True,
        )

    @param.depends('authors_info_df', watch=True)
    def _update_select_author_widget(self):
        self.select_author_widget.options = authors_list(
            authors_df=self.authors_info_df,
            top_n=self.top_n_widget.value,
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


def author_info(authors_df: pd.DataFrame, author: str) -> str:
    author_s: pd.Series = authors_df.loc[author]

    if not author:
        return "{unknown}"

    # TODO: replace inline style with the use of `stylesheets=[stylesheet]`
    # uses minus sign '−', rather than dash '-'
    return f"""
    <span style="color: rgb(89, 99, 110);">{html_int_humane(author_s.loc['n_commits'])}&nbsp;commits</span>
    <span class="additionsDeletionsWrapper">
    <span class="color-fg-success" style="color: #1a7f37">{html_int_humane(int(author_s.loc['p_count']))}&nbsp;++</span>
    <span class="color-fg-danger"  style="color: #d1242f">{html_int_humane(int(author_s.loc['m_count']))}&nbsp;−−</span>
    </span>
    """


class AuthorsGrid(TimelineView):
    main_plot = param.ClassSelector(class_=TimeseriesPlot, allow_refs=True)
    # NOTE: needed only because of @params.depends works only with _parameters_
    # TODO: replace with a .rx.watch(...), or @pn.depends(...), or something
    authors_info_df=param.ClassSelector(class_=pd.DataFrame, allow_refs=True)
    top_n = param.Integer(default=4, allow_refs=True)

    def __init__(self, **params):
        #print(f"AuthorsGrid::__init__(self, **{params=})")
        super().__init__(**params)

        #self.authors_info_df = self.main_plot.authors_info_df_rx

        self.authors_grid = pn.layout.GridBox(
           ncols=2,
        )
        self.update_authors_grid()

    def __panel__(self) -> pn.viewable.Viewable:
        return self.authors_grid

    def authors_cards(self):
        #print("RUNNING AuthorsGrid::authors_cards()")
        result: list[pn.layout.Card] = []
        avatar_size = 20  # TODO: make it configurable, eg. via param

        # TODO: pass `field_names` or `Row` as parameters
        RowT = namedtuple(typename='Pandas', field_names=['Index', 'n_commits', 'p_count', 'm_count', 'author_name'])
        row: RowT
        #print(f"{self.authors_info_df.columns=}")
        for i, row in enumerate(self.authors_info_df.head(self.top_n).itertuples(), start=1):
            #print(f"{i=}, {row=}")
            result.append(
                pn.layout.Card(
                    pn.Column(
                        pn.FlexBox(
                            # author.name <author.email>, using most common author.name
                            pn.pane.HTML(
                                '<div class="author">'
                                f'<img src="{gravatar_url(row.Index, avatar_size)}"'
                                f' width="{avatar_size}" height="{avatar_size}" alt="" /> '
                                f'{row.author_name} &lt;{row.Index}&gt;'
                                '</div>'
                            ),
                            # position in the top N list
                            pn.pane.HTML(f'<div class="chip">#{i}</div>', width=20),
                            # FlexBox parameters:
                            # https://css-tricks.com/snippets/css/a-guide-to-flexbox/
                            # https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_flexible_box_layout/Basic_concepts_of_flexbox
                            flex_direction="row",
                            flex_wrap="nowrap",
                            justify_content="space-between",
                            align_items="baseline",
                            gap="1 rem",
                            # layoutable parameters
                            sizing_mode='stretch_width',
                            width_policy="max",
                            # width=300,
                            # styles={"width": "100%"}
                        ),
                        pn.pane.HTML(
                            # TODO: pass tuple instead
                            author_info(
                                authors_df=self.authors_info_df,
                                author=row.Index
                            )
                        ),
                        ContributionsPercHeader(
                            data_store=self.data_store,
                            from_date_str=self.main_plot.param.from_date_str.rx(),
                            author_id=row.Index,
                            show_descr=True,
                        ),
                        TimeseriesPlotForAuthor(
                            data_store=self.data_store,
                            main_plot=self.main_plot,
                            author_email=row.Index,
                        ),
                    ),
                    hide_header=True,
                    collapsible=False,
                )
            )

        return result

    # NOTE: cannot use 'data_store.resampled_timeline_by_author_rx' as dependency, because of
    #       AttributeError: Attribute 'resampled_timeline_by_author_rx' could not be resolved on <TimelineDataStore ...>
    # NOTE: with `on_init=True`, it looks like this method is run before __init__, and therefore
    #       AttributeError: 'AuthorsGrid' object has no attribute 'authors_grid'
    # NOTE: updated twice when changing JSON file, but only once when changing top_n, or contributions
    @param.depends('authors_info_df', 'top_n', watch=True)
    def update_authors_grid(self) -> None:
        ## DEBUG
        #print(f"RUNNING update_authors_grid(), with repo={self.data_store.select_repo_widget.value}, top_n={self.top_n},...")

        self.authors_grid.clear()
        self.authors_grid.extend(
            self.authors_cards()
        )

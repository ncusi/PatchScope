import numpy as np
import pandas as pd
import hvplot.pandas  # noqa


def add_split_localtime(timeline_df: pd.DataFrame) -> pd.DataFrame:
    timeline_df['hour_UTC'] = timeline_df['author_date'].dt.hour
    # TODO: replace with a single .apply call, or with something more performant
    timeline_df['author_date_local'] = timeline_df[['author.timestamp', 'author.tz_info']].apply(
        lambda x: pd.Timestamp.fromtimestamp(x['author.timestamp'], tz=x['author.tz_info']).tz_localize(None),
        axis='columns',
    ).astype('datetime64[ns]')
    # NOTE: currently unused
    timeline_df['hour_localtime'] = timeline_df[['author.timestamp', 'author.tz_info']].apply(
        lambda x: pd.Timestamp.fromtimestamp(x['author.timestamp'], tz=x['author.tz_info']).hour,
        axis='columns',
    )
    timeline_df['day_name_localtime'] = timeline_df[['author.timestamp', 'author.tz_info']].apply(
        lambda x: pd.Timestamp.fromtimestamp(x['author.timestamp'], tz=x['author.tz_info']).day_name(),
        axis='columns',
    )

    return timeline_df


day_name_order_map = {
    'Monday': 1,
    'Tuesday': 2,
    'Wednesday': 3,
    'Thursday': 4,
    'Friday': 5,
    'Saturday': 6,
    'Sunday': 7,
}
day_name_to_dayofweek = {k: v-1 for k,v in day_name_order_map.items()}


def plot_periodicity_heatmap(
    timeline_df_author: pd.DataFrame,
    width: int = 600, height: int = 250,
    off_size: int = 125,
):
    #print(f"RUNNING plot_periodicity_heatmap(timeline_df_author=<{hex(id(timeline_df_author))}>, "
    #      f"{width=}, {height=}, {off_size=}):")
    #print(f"  {timeline_df_author.columns=}")
    plot_heatmap = timeline_df_author.hvplot.heatmap(
        x='author_date_local.hour',
        y='author_date_local.dayofweek',
        C='n_commits',
        cmap='blues',
        #title=f'repo={repo}, author={author}, n_commits',
        grid=True,
        # square=True,
        # NOTE: WARNING:param.HeatMapPlot76829: HeatMap element index is not unique ???
        reduce_function=np.sum,
        # interactivity
        tools=[
            'box_zoom',
            'save',
            'reset',
            'hover',
        ],
    ).opts(
        # aspect=1,
        width=width, height=height,
        # interactivity
        default_tools=[],
        invert_yaxis=True,
    )
    #print(plot_heatmap)

    day_name_date_local_s = timeline_df_author['author_date_local'].dt.day_name() \
        .value_counts(sort=False) \
        .sort_index(
            ascending=False,
            key=lambda x: x.map(day_name_order_map)
        ).reindex(
            # matches ascending=False
            ['Sunday', 'Saturday', 'Friday', 'Thursday', 'Wednesday', 'Tuesday', 'Monday'],
            fill_value=0,
        )
    #print(f"  {day_name_date_local_s=}")

    day_name_date_local_df = pd.DataFrame({
        'n_commits': day_name_date_local_s,
        'weekend': [True, True, False, False, False, False, False],
    })
    #print(f"  {day_name_date_local_df=}")
    day_name_date_local_df['color'] = '#8888ff'
    day_name_date_local_df.loc[day_name_date_local_df['weekend'], 'color'] = '#ff6666'
    day_name_date_local_df['dayofweek'] = day_name_date_local_df.index.map(day_name_to_dayofweek)

    plot_author_2b = day_name_date_local_df.hvplot.barh(
        x='dayofweek', y='n_commits', color='color',
        title=f"histogram of commits by day of week local",
        #invert_yaxis=True,
    )

    hour_date_local_s = timeline_df_author['author_date_local'].dt.hour \
        .value_counts(sort=False) \
        .sort_index(
        ascending=True,
    ).reindex(range(24), fill_value=0)
    hour_hist_2b = hour_date_local_s.hvplot.bar(
        title=f"histogram of commits by hour local",
    )

    # NOTE: plot_author_2b.redim(dayofweek='author date: day of week') changes order of rows (???)
    plot = plot_heatmap \
    << plot_author_2b.redim(dayofweek='author_date_local.dayofweek', n_commits='commits').opts(
        width=off_size, height=height, show_grid=True,
        title=f"histogram of commits by day of week local",
    ) \
    << hour_hist_2b.redim(author_date_local='author date: local hour').opts(
        height=off_size, width=width,  show_grid=True,
        title=f"histogram of commits by hour local",
    )

    return plot

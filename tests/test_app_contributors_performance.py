import io

import pytest

param = pytest.importorskip("param")
pn = pytest.importorskip("panel")

from diffinsights_web.datastore import timeline
from diffinsights_web.views import info
from diffinsights_web.views.plots import timeseries
from diffinsights_web.apps.contributors import template, dataset_dir, timeline_data_store


@pytest.fixture
def app():
    return template


@pytest.mark.slow
def test_contributors_run_performance(app, benchmark):
    #for k, v in app.param.objects().items():
    #    print(f"{app.__class__.name}.{k} = {repr(v.default)} ({type(v)})")

    #print(template)
    #for e in template.sidebar:
    #    print(e)
    #print(template.sidebar[0][0])
    #print(template.sidebar[0][0].value)

    ## Failed attempt 1.
    #     @pn.cache
    #     def get_timeline_df(timeline_data: dict, repo: str) -> pd.DataFrame:
    # >       init_df = pd.DataFrame.from_records(timeline_data[repo])
    # E       KeyError: 'hellogitworld'
    #with pn.io.hold():
    #    template.sidebar[0][1].value = 'qtile'
    #    template.sidebar[0][0].value = str(dataset_dir.joinpath('qtile.timeline.purpose-to-type.json'))

    ## Failed attempt 2.
    #     @pn.cache
    #     def get_timeline_df(timeline_data: dict, repo: str) -> pd.DataFrame:
    # >       init_df = pd.DataFrame.from_records(timeline_data[repo])
    # E       KeyError: 'hellogitworld'
    #with param.parameterized.batch_call_watchers(timeline_data_store):
    #    timeline_data_store.select_file_widget.value = str(dataset_dir.joinpath('qtile.timeline.purpose-to-type.json'))
    #    timeline_data_store.select_repo_widget.value = 'qtile'

    ## Failed attempt 3.
    # AttributeError: The value of a derived expression cannot be set.
    #timeline_data_store.timeline_data_rx.rx.value = \
    #    get_timeline_data(dataset_dir.joinpath('qtile.timeline.purpose-to-type.json'))

    ## Failed attempt 4.
    # KeyError: 'hellogitworld'
    #timeline_data_store.select_file_widget.param.update(
    #    value=str(dataset_dir.joinpath('qtile.timeline.purpose-to-type.json')),
    #)

    print(template.sidebar[0][0].value)
    timeline_data_store.select_file_widget.param.update(
        value=str(dataset_dir.joinpath('qtile.timeline.purpose-to-type.json')),
    )
    print(template.sidebar[0][0].value)

    # Benchmark the time it takes to render the Panel app
    def render_app():
        buffer = io.StringIO()
        pn.state.clear_caches()
        pn.io.save.save(app, filename=buffer, embed=True)
        return buffer.getvalue()

    # Run the benchmark (no caching)
    # --------------------------------------------------- benchmark: 1 tests -------------------------------
    # repo (time in s)     Min     Max    Mean  StdDev  Median     IQR  Outliers     OPS  Rounds  Iterations
    # ------------------------------------------------------------------------------------------------------
    # 'hellogitworld'   1.4775  2.8561  2.1144  0.5713  1.9781  0.9547       2;0  0.4730       5           1
    # 'qtiles'          1.6314  2.0680  1.7746  0.1812  1.7147  0.2475       1;0  0.5635       5           1
    # 'tensorflow'      1.4393  2.1075  1.8422  0.2583  1.8559  0.3392       2;0  0.5428       5           1
    # ------------------------------------------------------------------------------------------------------
    result = benchmark(render_app)

    # Optional: Add an assertion for maximum acceptable render time (in seconds)
    assert result is not None, "App rendering failed"


# add `benchmark` fixture as parameter when performing benchmark (single use)
def test_contributors_steps_performance():
    ## TimelineDataStore
    json_path = dataset_dir.joinpath('qtile.timeline.purpose-to-type.json')
    # --------------------------------------------------------- benchmark: 1 tests ---------------------------------
    # (time in ms)        Min       Max      Mean  StdDev    Median      IQR  Outliers     OPS  Rounds  Iterations
    # --------------------------------------------------------------------------------------------------------------
    #                100.0428  122.8066  109.2786  7.8773  108.8854  13.8551       4;0  9.1509       9           1
    # --------------------------------------------------------------------------------------------------------------
    # timeline_data = benchmark(
    #     timeline.get_timeline_data,
    #     json_path=json_path,
    # )
    timeline_data = timeline.get_timeline_data(
        json_path=json_path,
    )
    # (time in ms)   105.3941  129.7154  113.6983  8.6321  110.7477  11.2657       1;0  8.7952       7           1
    timeline_df = timeline.get_timeline_df(
        json_path=json_path,
        timeline_data=timeline_data,
        repo='qtile',
    )
    # (time in us)    62.2000  886.7000   95.1186 53.6248   71.9000  42.7000   240;117  10.5132   2086           1
    timeline_max_date = timeline.get_max_date(
        timeline_df=timeline_df,
    )
    # (time in us)    34.6000  451.8999   43.8494 20.1701   35.3000  11.5000   532;534  22.8054   6378           1
    pm_count_cols = timeline.get_pm_count_cols(
        timeline_df,
    )
    # (time in ms)    46.2870   77.5715   55.3805  9.0224   53.0321   9.8213       3;1  18.0569     14           1
    resampled_timeline_all = timeline.resample_timeline(
        timeline_df=timeline_df,
        resample_rate='W',
        pm_count_cols=pm_count_cols,
    )
    # (time in ms)   103.5246  167.7835  129.6302  25.7041  124.3033  38.6812       2;0  7.7143       5           1
    resampled_timeline_by_author = timeline.resample_timeline(
        timeline_df=timeline_df,
        resample_rate='W',
        group_by='author.email',
        pm_count_cols=pm_count_cols,
    )

    ## TimeseriesPlot
    # (time in us)     1.5999  3,468.3000  2.3201  28.3839  1.8000  0.1001    6;3106      431.0178   14948           1
    value_range = timeline.get_value_range(
        timeline_df=resampled_timeline_all,
        column='n_commits',  # vs 'timeline|n_commits'
    )
    date_range = timeline.get_date_range(
        timeline_df=timeline_df,
        from_date_str='',
    )
    # (time in ms)    57.3498  82.5244  67.2200  8.6832  64.4541  7.6014       2;1  14.8765       6           1
    authors_info_df = timeline.authors_info_df(
        timeline_df=timeline_df,
        column='n_commits',
        from_date_str='',
    )
    # (time in ms)    24.2087  74.8452  44.0435  12.2897  41.6401  15.0689       8;1  22.7048      23           1
    plot_commits = timeseries.plot_commits(
        resampled_df=resampled_timeline_all,
        column='n_commits',
        from_date_str='',
    )

    ## RepoPlotHeader
    #                   Min         Max     Mean   StdDev   Median      IQR  Outliers  OPS (Kops/s)  Rounds  Iterations
    # (time in us)  22.9999  2,036.5000  45.3154  46.5184  31.7000  30.4000   350;262       22.0675   10061           1
    sampling_info = info.sampling_info(
        resample_freq='W',
        column='n_commits',
        frequency_names_map=timeline.frequency_names,
        min_max_date=date_range,
    )

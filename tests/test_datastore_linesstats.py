import pytest

from diffinsights_web.datastore import find_dataset_dir
from diffinsights_web.datastore.timeline import TimelineDataStore
from diffinsights_web.datastore.linesstats import LinesStatsDataStore

param = pytest.importorskip("param")
panel = pytest.importorskip("panel")


def test_timeseries_file_no_such_file():
    data_store = LinesStatsDataStore(
        name='test_repo_name_no_such_file',
        dataset_dir=find_dataset_dir(),
        timeseries_file='does-not-exist',
    )

    # DEBUG
    #print(f"{data_store=}")
    #print(f"{data_store.lines_stats_data_rx=}")
    #print(f"{data_store.lines_stats_data_rx._obj=}")
    #print(f"{data_store.lines_stats_data_rx._operation=}")
    #print(f"{data_store.lines_stats_data_rx.rx.value=}")

    actual = data_store.lines_stats_data_rx.rx.value
    assert actual is None, \
        "LinesDataStore returns None if lines-stats file does not exist"


def test_timeseries_file_from_widget_default_value():
    dataset_dir = find_dataset_dir()
    data_store = TimelineDataStore(dataset_dir=dataset_dir)

    lines_stats = LinesStatsDataStore(
        dataset_dir='.',  # should be ignored, not tested
        timeseries_file=data_store.select_file_widget,
    )

    actual = lines_stats.lines_stats_data_rx.rx.value
    assert actual is None or isinstance(actual, dict), \
        "No crashes, returned something for value from widget"


def test_timeseries_file_hellogitworld():
    lines_stats = LinesStatsDataStore(
        dataset_dir='data/examples/stats',  # directory part, relative to top directory of project
        timeseries_file='hellogitworld.timeline.purpose-to-type.json',  #filename part
    )
    actual = lines_stats.lines_stats_data_rx.rx.value

    assert isinstance(actual, dict), \
        "correctly found lines-stats file, retrieved data, did not return None"
    assert 'data/examples/annotations/hellogitworld' in actual, \
        "hellogitworld lines-stats file came from hellogitworld annotations"
    assert 'hellogitworld' in actual['data/examples/annotations/hellogitworld'], \
        "data nicknamed 'hellogitworld' in hellogitworld lines-stats file"

    data = actual['data/examples/annotations/hellogitworld']['hellogitworld']
    assert len(data.keys()) > 0, \
        "there is data from multiple files with annotation data"


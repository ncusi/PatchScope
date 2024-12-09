import pytest

from diffinsights_web.datastore import find_dataset_dir
from diffinsights_web.datastore.timeline import TimelineDataStore
from diffinsights_web.datastore.linesstats import LinesStatsDataStore, sorted_changed_files, \
    limit_count_to_selected_files, path_to_dirs_only_counter, reduce_sankey_from_tail, reduce_sankey_thin_out

hv = pytest.importorskip("holoviews")
param = pytest.importorskip("param")
panel = pytest.importorskip("panel")


def test_timeseries_file_no_such_file():
    data_store = LinesStatsDataStore(
        name='test_repo_name_no_such_file',
        dataset_dir=find_dataset_dir(),
        timeseries_file='does-not-exist',
        repo_name='repo-does-not-exist',
    )

    # DEBUG
    #print(f"{data_store=}")
    #print(f"{data_store.lines_stats_data_rx=}")
    #print(f"{data_store.lines_stats_data_rx._obj=}")
    #print(f"{data_store.lines_stats_data_rx._operation=}")
    #print(f"{data_store.lines_stats_data_rx.rx.value=}")

    actual = data_store.lines_stats_data_rx.rx.value
    assert actual is None, \
        "LinesDataStore returns None for data if lines-stats file does not exist"

    actual = data_store.lines_stats_counter_rx.rx.value
    assert actual is None, \
        "LinesDataStore returns None for counter if lines-stats file does not exist"

    actual = data_store.sankey_data_rx.rx.value
    assert actual is None, \
        "LinesDataStore returns None for Sankey data if lines-stats file does not exist"


def test_timeseries_file_from_widget_default_value():
    dataset_dir = find_dataset_dir()
    data_store = TimelineDataStore(dataset_dir=dataset_dir)

    lines_stats = LinesStatsDataStore(
        dataset_dir='.',  # should be ignored, not tested
        timeseries_file=data_store.select_file_widget,
        repo_name=data_store.select_repo_widget,
    )

    actual = lines_stats.lines_stats_data_rx.rx.value
    assert actual is None or isinstance(actual, dict), \
        "No crashes, returned something for value from widget"


def test_timeseries_file_hellogitworld():
    lines_stats = LinesStatsDataStore(
        dataset_dir='data/examples/stats',  # directory part, relative to top directory of project
        timeseries_file='hellogitworld.timeline.purpose-to-type.json',  # filename part
        repo_name='hellogitworld',
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

    actual = lines_stats.lines_stats_counter_rx.rx.value
    #print(f"{len(actual)=}")
    #print(f"{actual.keys()=}")
    assert ('README.txt', 'type.documentation') in actual, \
        "there were changes marked as documentation lines to 'README.txt' file"
    assert actual[('README.txt', 'type.documentation')] > 0, \
        "there were non-zero amount of changes marked as documentation to 'README.txt' file"
    assert ('README.txt', 'type.code') not in actual, \
        "there were no changes marked as code lines to 'README.txt' file"

    actual = sorted_changed_files(lines_stats.lines_stats_counter_rx.rx.value)
    assert actual[0] == 'src/Main.groovy', \
        "file with most changes was 'src/Main.groovy'"

    selected_files = actual[:3]
    actual = limit_count_to_selected_files(
        lines_stats_counter=lines_stats.lines_stats_counter_rx.rx.value,
        files=selected_files,
    )
    assert len(actual) >= len(selected_files), \
        "at least one counter entry for each file"

    counter_limited = actual
    actual = sorted_changed_files(counter_limited)
    assert actual == selected_files, \
        "list of files after filtering is filter list, if filter list is from counter"

    actual = path_to_dirs_only_counter(counter_limited)
    assert ('.', 'src') in actual, \
        "path from top dir to 'src' subdirectory present"
    assert ('src', 'type.code') in actual, \
        "'src/Main.groovy' lines of code contributions changed to 'src' contributions"


    starting_counter = actual
    actual = reduce_sankey_from_tail(starting_counter)
    assert len(actual) < len(starting_counter), \
        "removed at least one node from Sankey diagram"
    # TODO: check that it removed only last level

    actual = reduce_sankey_thin_out(starting_counter, threshold_ratio=0.5)
    assert len(actual) < len(starting_counter), \
        "removed at least one node from Sankey diagram"
    # TODO: add more checks

    actual = lines_stats.sankey_data_rx.rx.value
    assert len(actual) > 0, \
        "there is something to create Sankey diagram from"


def test_switch_repos_same_file():
    lines_stats = LinesStatsDataStore(
        dataset_dir='data/examples/stats',  # directory part, relative to top directory of project
        timeseries_file='hellogitworld.timeline.purpose-to-type.json',  # filename part
        repo_name='hellogitworld',
    )
    actual = lines_stats.lines_stats_data_rx.rx.value

    assert isinstance(actual, dict), \
        "correctly found lines-stats file, retrieved data, did not return None"

    lines_stats.timeseries_file = 'does-not-exist-directly'
    actual = lines_stats.lines_stats_data_rx.rx.value
    assert actual is None, \
        "switching to not-existing file clears retrieved data, makes it None"

    actual = lines_stats.lines_stats_counter_rx.rx.value
    assert actual is None, \
        "switching to not-existing file clears stats counter, makes it None"

    actual = lines_stats.sankey_data_rx.rx.value
    assert actual is None, \
        "switching to not-existing file clears computed sankey data, makes it None"


# TODO: add test for sankey_triples_from_counter() and sankey_counter_from_triples()

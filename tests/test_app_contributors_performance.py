import io

import pytest

from diffinsights_web.datastore.timeline import get_timeline_data

param = pytest.importorskip("param")
pn = pytest.importorskip("panel")

from diffinsights_web.apps.contributors import template, dataset_dir, timeline_data_store


@pytest.fixture
def app():
    return template

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

    #print(template.sidebar[0][0].value)

    # Benchmark the time it takes to render the Panel app
    def render_app():
        buffer = io.StringIO()
        pn.state.clear_caches()
        pn.io.save.save(app, filename=buffer, embed=True)
        return buffer.getvalue()

    # Run the benchmark
    result = benchmark(render_app)

    # Optional: Add an assertion for maximum acceptable render time (in seconds)
    assert result is not None, "App rendering failed"

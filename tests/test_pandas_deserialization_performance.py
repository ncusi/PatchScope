from pathlib import Path

import pytest

param = pytest.importorskip("param")  # for diffinsights_web.datastore.timeline
pn = pytest.importorskip("panel")     # for diffinsights_web.datastore
pd = pytest.importorskip("pandas")    # also used explicitly

from diffinsights_web.datastore import find_dataset_dir
from diffinsights_web.datastore.timeline import get_timeline_data, get_timeline_df


dataset_dir = find_dataset_dir()
save_path_base = 'qtile.timeline.purpose-to-type'


@pytest.fixture
def qtile_dataframe() -> pd.DataFrame:
    """Returns `timeline_df` dataframe for 'qtile' repo, parsing JSON data file"""
    # TODO: make this fixture parameterizable with JSON file path
    json_path = dataset_dir.joinpath(f"{save_path_base}.json")
    timeline_data = get_timeline_data(
        json_path=json_path,
    )
    timeline_df = get_timeline_df(
        json_path=json_path,
        timeline_data=timeline_data,
        repo='qtile',
    )
    return timeline_df


# -------------------------------------------------------------------------------- benchmark: 8 tests ------------------------------------------------------------------------------------------
# Name (time in ms)                 Min                Max               Mean            StdDev             Median               IQR            Outliers       OPS            Rounds  Iterations
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# from_pickle                    7.0632 (1.0)      13.2599 (1.0)       8.9747 (1.0)      1.6802 (1.0)       8.6302 (1.0)      2.5256 (1.27)         17;0  111.4248 (1.0)          46           1
# from_feather                   8.0850 (1.14)     15.6302 (1.18)      9.6521 (1.08)     1.7003 (1.01)      8.8682 (1.03)     1.9838 (1.0)           7;1  103.6040 (0.93)         43           1
# from_parquet[pyarrow]         18.6293 (2.64)     33.6198 (2.54)     22.1781 (2.47)     4.6693 (2.78)     19.5050 (2.26)     5.5288 (2.79)          3;1   45.0896 (0.40)         19           1
# from_pickle_gz                21.8022 (3.09)     30.3714 (2.29)     24.6883 (2.75)     2.8099 (1.67)     23.8436 (2.76)     4.7604 (2.40)          7;0   40.5050 (0.36)         24           1
# from_parquet[fastparquet]     27.3906 (3.88)     49.8179 (3.76)     32.4216 (3.61)     6.1958 (3.69)     29.3228 (3.40)     9.2433 (4.66)          6;0   30.8437 (0.28)         23           1
# from_hdf[fixed]               32.6708 (4.63)     51.3473 (3.87)     37.8668 (4.22)     5.8916 (3.51)     34.5773 (4.01)     7.0123 (3.53)          5;1   26.4083 (0.24)         23           1
# from_pickle_xz                44.3694 (6.28)     69.9600 (5.28)     48.6162 (5.42)     7.6785 (4.57)     45.2685 (5.25)     2.1864 (1.10)          2;3   20.5693 (0.18)         19           1
# from_hdf[table]               48.5612 (6.88)     63.3302 (4.78)     53.6635 (5.98)     4.9581 (2.95)     52.1295 (6.04)     7.0313 (3.54)          4;0   18.6347 (0.17)         17           1
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#
# Legend:
#   Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
#   OPS: Operations Per Second, computed as 1 / Mean



def test_bench_from_pickle(tmp_path: Path, qtile_dataframe: pd.DataFrame, benchmark):
    save_path = tmp_path / f"{save_path_base}.pkl"
    qtile_dataframe.to_pickle(save_path)

    df = benchmark(
        pd.read_pickle,
        save_path,
    )
    assert isinstance(df, pd.DataFrame), "recovered DataFrame"


def test_bench_from_pickle_gz(tmp_path: Path, qtile_dataframe: pd.DataFrame, benchmark):
    save_path = tmp_path / f"{save_path_base}.pkl.gz"
    qtile_dataframe.to_pickle(save_path, compression="infer")

    df = benchmark(
        pd.read_pickle,
        save_path,
        compression = "infer",
    )
    assert isinstance(df, pd.DataFrame), "recovered DataFrame"


def test_bench_from_pickle_xz(tmp_path: Path, qtile_dataframe: pd.DataFrame, benchmark):
    save_path = tmp_path / f"{save_path_base}.pkl.xz"
    qtile_dataframe.to_pickle(save_path, compression="infer")

    df = benchmark(
        pd.read_pickle,
        save_path,
        compression = "infer",
    )
    assert isinstance(df, pd.DataFrame), "recovered DataFrame"

@pytest.mark.parametrize("format", ["fixed", "table"])
def test_bench_from_hdf(tmp_path: Path, qtile_dataframe: pd.DataFrame, format, benchmark):
    pytest.importorskip("tables")

    save_path = tmp_path / f"{save_path_base}.{format}.hdf5"
    qtile_dataframe.to_hdf(save_path, key="df", format=format)

    df = benchmark(
        pd.read_hdf,
        save_path,
        key="df",
    )
    assert isinstance(df, pd.DataFrame), "recovered DataFrame"


def test_bench_from_feather(tmp_path: Path, qtile_dataframe: pd.DataFrame, benchmark):
    pytest.importorskip("pyarrow")

    save_path = tmp_path / f"{save_path_base}.feather"
    qtile_dataframe.to_feather(save_path)

    df = benchmark(
        pd.read_feather,
        save_path,
    )
    assert isinstance(df, pd.DataFrame), "recovered DataFrame"


@pytest.mark.parametrize("engine", ["pyarrow", "fastparquet"])
def test_bench_from_parquet(tmp_path: Path, qtile_dataframe: pd.DataFrame, engine, benchmark):
    pytest.importorskip(engine)

    save_path = tmp_path / f"{save_path_base}.{engine}.parquet"
    qtile_dataframe.to_parquet(save_path, engine=engine)

    df = benchmark(
        pd.read_parquet,
        save_path,
        engine=engine,
    )
    assert isinstance(df, pd.DataFrame), "recovered DataFrame"


@pytest.mark.skip("unable to infer dtype on column 'author_date'; xarray cannot serialize arbitrary Python objects")
@pytest.mark.parametrize("engine", ["h5netcdf", "netCDF4"])
def test_bench_from_netcdf(tmp_path: Path, qtile_dataframe: pd.DataFrame, engine, benchmark):
    xr = pytest.importorskip("xarray")
    pytest.importorskip(engine)
    engine = engine.lower()

    save_path = tmp_path / f"{save_path_base}.{engine}.nc"
    qtile_ds = xr.Dataset.from_dataframe(qtile_dataframe)
    qtile_ds.to_netcdf(save_path, engine=engine)

    def read_netcdf(path, eng='netcdf4'):
        return xr.open_dataset(
            path,
            engine=eng,
        ).to_dataframe()

    df = benchmark(
        read_netcdf,
        save_path,
        eng=engine,
    )
    assert isinstance(df, pd.DataFrame), "recovered DataFrame"


@pytest.mark.skip('Invalid datetime unit in metadata string "[ns, UTC]", from "author_date" dtype: datetime64[ns, UTC]')
def test_bench_from_npz(tmp_path: Path, qtile_dataframe: pd.DataFrame, benchmark):
    sf = pytest.importorskip("static_frame")

    dtypes = qtile_dataframe.dtypes.apply(
        lambda x: 'str' if x.name == 'object' else x.name
    ).to_dict()

    save_path = tmp_path / f"{save_path_base}.npz"
    qtile_f = sf.Frame.from_pandas(qtile_dataframe, dtypes=dtypes)
    qtile_f.to_npz(save_path)

    def read_npz(path):
        return sf.from_npz(
            path,
        ).to_pandas()

    df = benchmark(
        read_npz,
        save_path,
    )
    assert isinstance(df, pd.DataFrame), "recovered DataFrame"

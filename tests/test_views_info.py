import datetime

# https://docs.pytest.org/en/stable/how-to/skipping.html#skipping-on-a-missing-import-dependency
import pytest
pandas = pytest.importorskip("pandas")
param = pytest.importorskip("param")
panel = pytest.importorskip("panel")

from diffinsights_web.views.info import time_range_options


def test_time_range_options():
    # 2020.12.01
    end_date = datetime.date(year=2020, month=12, day=1)
    actual = time_range_options(end_date=end_date)
    expected = {
        'All': '',  #     '2020.12.01' <-- end date
        'Last month':     '2020.11.01',
        'Last 3 months':  '2020.09.01',
        'Last 6 months':  '2020.06.01',
        'Last 12 months': '2019.12.01',
        'Last 24 months': '2018.12.01',
    }
    assert actual == expected, \
        "correctly computes dates with given delta from end_date"

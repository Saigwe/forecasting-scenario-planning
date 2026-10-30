import numpy as np
import pytest

from forecasting.data import generate
from forecasting.models import backtest, forecast_with_interval, seasonal_naive
from forecasting.planning import PRODUCTIVE_HOURS_PER_FTE_WEEK, TARGET_OCCUPANCY, Scenario, required_fte, scenario_fte
from forecasting.run import run


def test_seasonal_naive_repeats_last_year_scaled():
    y = np.tile(np.arange(52, dtype=float) + 100, 3)
    fc = seasonal_naive(y, 52)
    assert np.allclose(fc, y[-52:])          # no growth -> exactly last year


def test_backtest_prefers_seasonal_models_on_seasonal_data():
    y = generate().query("queue == 'Bookings'").contacts.to_numpy(dtype=float)
    naive, ma = backtest(y, "seasonal_naive"), backtest(y, "moving_average")
    assert naive.wape < ma.wape
    assert naive.wape < 0.10


def test_interval_contains_point_forecast():
    y = generate().query("queue == 'Payments'").contacts.to_numpy(dtype=float)
    r = backtest(y, "seasonal_naive")
    point, lo, hi = forecast_with_interval(y, "seasonal_naive", 13, r.errors)
    assert np.all(lo <= point) and np.all(point <= hi)


def test_fte_maths():
    # 1,000 contacts x 6 min = 100 hours of work
    expected = 100 / (PRODUCTIVE_HOURS_PER_FTE_WEEK * TARGET_OCCUPANCY)
    assert required_fte(1000, 360) == pytest.approx(expected)
    assert scenario_fte(1000, 360, Scenario("x", volume_change=0.1, aht_change=-0.1)) == pytest.approx(expected * 0.99)


def test_end_to_end_outputs(tmp_path):
    res = run(tmp_path)
    assert set(res["plan"].queue) == {"Payments", "Bookings", "Account Security"}
    assert res["accuracy"].selected.sum() == 3
    assert (res["accuracy"][res["accuracy"].selected].wape_pct < 10).all()
    assert (tmp_path / "planning_memo.md").exists() and (tmp_path / "forecast.png").exists()

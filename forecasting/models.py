"""Candidate forecasting models and rolling-origin backtesting."""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing

SEASON = 52


def seasonal_naive(y: np.ndarray, h: int) -> np.ndarray:
    """Same week last year, scaled by the year-on-year change of the last 13 weeks."""
    last_year = y[-SEASON:]
    growth = y[-13:].sum() / y[-SEASON - 13:-SEASON].sum()
    return np.array([last_year[i % SEASON] for i in range(h)]) * growth


def moving_average(y: np.ndarray, h: int, window: int = 8) -> np.ndarray:
    return np.repeat(y[-window:].mean(), h)


def holt_winters(y: np.ndarray, h: int) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(y, trend="add", damped_trend=True, seasonal="mul",
                                   seasonal_periods=SEASON).fit(optimized=True)
    return fit.forecast(h)


def trend_fourier(y: np.ndarray, h: int, harmonics: int = 3, recent: int = 104) -> np.ndarray:
    """Log-linear trend plus Fourier yearly seasonality, fitted by least squares on the last two years."""
    y_fit = y[-recent:]
    t = np.arange(len(y) - len(y_fit), len(y) + h)

    def design(tt):
        cols = [np.ones_like(tt, dtype=float), tt.astype(float)]
        for k in range(1, harmonics + 1):
            cols += [np.sin(2 * np.pi * k * tt / 52.18), np.cos(2 * np.pi * k * tt / 52.18)]
        return np.column_stack(cols)

    x = design(t)
    coef, *_ = np.linalg.lstsq(x[: len(y_fit)], np.log(y_fit), rcond=None)
    return np.exp(x[len(y_fit):] @ coef)


MODELS = {"seasonal_naive": seasonal_naive, "moving_average": moving_average, "holt_winters": holt_winters,
          "trend_fourier": trend_fourier}


@dataclass(frozen=True)
class BacktestResult:
    model: str
    wape: float      # weighted absolute percentage error
    bias: float      # (forecast - actual) / actual, summed
    errors: np.ndarray  # forecast / actual - 1 per point, for intervals


def backtest(y: np.ndarray, model: str, horizon: int = 13, folds: int = 4) -> BacktestResult:
    """Rolling-origin evaluation: refit at each origin and forecast the next `horizon` weeks."""
    f = MODELS[model]
    abs_err = actual_sum = signed = 0.0
    ratios = []
    for k in range(folds, 0, -1):
        origin = len(y) - k * horizon
        fc, actual = f(y[:origin], horizon), y[origin:origin + horizon]
        abs_err += np.abs(fc - actual).sum()
        signed += (fc - actual).sum()
        actual_sum += actual.sum()
        ratios.extend(fc / actual - 1)
    return BacktestResult(model, abs_err / actual_sum, signed / actual_sum, np.array(ratios))


def forecast_with_interval(y: np.ndarray, model: str, h: int, errors: np.ndarray, level: float = 0.8):
    """Point forecast plus an empirical interval from backtest errors (no distributional assumption)."""
    point = MODELS[model](y, h)
    lo_q, hi_q = np.quantile(errors, [(1 - level) / 2, 1 - (1 - level) / 2])
    # forecast = actual * (1 + e)  =>  actual = forecast / (1 + e)
    return point, point / (1 + hi_q), point / (1 + lo_q)

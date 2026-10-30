"""Three years of weekly contact volume for three support queues: trend, yearly seasonality, a December peak and noise."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

QUEUES = {
    # queue: (base weekly volume, weekly growth, seasonal amplitude, december peak, AHT seconds)
    "Payments": (4200, 0.0035, 0.18, 0.35, 420),
    "Bookings": (6800, 0.0015, 0.30, 0.10, 360),
    "Account Security": (2100, 0.0060, 0.08, 0.05, 600),
}
START = pd.Timestamp("2023-10-02")  # Mondays
WEEKS = 156


def generate(out_dir: str | Path | None = None, seed: int = 21) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    weeks = pd.date_range(START, periods=WEEKS, freq="W-MON")
    rows = []
    for queue, (base, growth, amp, dec_peak, aht) in QUEUES.items():
        t = np.arange(WEEKS)
        seasonal = 1 + amp * np.sin(2 * np.pi * (weeks.dayofyear.to_numpy() - 80) / 365.25)
        december = 1 + dec_peak * ((weeks.month == 12) & (weeks.day <= 24)).astype(float)
        level = base * (1 + growth) ** t * seasonal * december
        volume = np.round(level * rng.normal(1, 0.04, WEEKS)).astype(int)
        rows.append(pd.DataFrame({"week": weeks, "queue": queue, "contacts": volume, "aht_seconds": aht}))
    df = pd.concat(rows, ignore_index=True)
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        df.to_csv(Path(out_dir) / "weekly_contacts.csv", index=False)
    return df

"""Backtest, pick the best model per queue, forecast 26 weeks and plan headcount: python -m forecasting.run"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .data import generate  # noqa: E402
from .models import MODELS, backtest, forecast_with_interval  # noqa: E402
from .planning import SCENARIOS, required_fte, scenario_fte  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HORIZON = 26


def run(out_dir: Path = ROOT / "output", data: pd.DataFrame | None = None) -> dict:
    data = generate(ROOT / "data") if data is None else data
    out_dir.mkdir(parents=True, exist_ok=True)
    accuracy, forecasts, plan = [], {}, []
    fig, axes = plt.subplots(len(data.queue.unique()), 1, figsize=(10, 8), sharex=True)

    for ax, (queue, g) in zip(axes, data.groupby("queue", sort=False)):
        y = g.contacts.to_numpy(dtype=float)
        aht = g.aht_seconds.iloc[-1]
        results = {m: backtest(y, m) for m in MODELS}
        best = min(results.values(), key=lambda r: r.wape)
        for r in results.values():
            accuracy.append({"queue": queue, "model": r.model, "wape_pct": round(100 * r.wape, 1),
                             "bias_pct": round(100 * r.bias, 1), "selected": r.model == best.model})
        point, lo, hi = forecast_with_interval(y, best.model, HORIZON, best.errors)
        future = pd.date_range(g.week.iloc[-1] + pd.Timedelta(weeks=1), periods=HORIZON, freq="W-MON")
        forecasts[queue] = pd.DataFrame({"week": future, "forecast": point, "low_80": lo, "high_80": hi,
                                         "fte": [required_fte(v, aht) for v in point],
                                         **{f"fte_{s.name}": [scenario_fte(v, aht, s) for v in point]
                                            for s in SCENARIOS}})

        current_fte = required_fte(y[-13:].mean(), aht)
        peak = point.max()
        row = {"queue": queue, "model": best.model, "wape_pct": round(100 * best.wape, 1),
               "fte_needed_now": round(current_fte, 1)}
        for s in SCENARIOS:
            row[f"peak FTE: {s.name}"] = round(scenario_fte(peak, aht, s), 1)
        row["peak_week"] = future[int(np.argmax(point))].date().isoformat()
        plan.append(row)

        ax.plot(g.week, y, color="#5B6770", lw=1, label="Actual")
        ax.plot(future, point, color="#1F3A5F", lw=2, label=f"Forecast ({best.model})")
        ax.fill_between(future, lo, hi, color="#1F3A5F", alpha=0.15, label="80% interval")
        ax.set_title(f"{queue}  ·  backtest error {best.wape:.1%}", fontsize=10)
        ax.legend(loc="upper left", fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "forecast.png", dpi=120)
    plt.close(fig)

    acc_df, plan_df = pd.DataFrame(accuracy), pd.DataFrame(plan)
    acc_df.to_csv(out_dir / "backtest_accuracy.csv", index=False)
    pd.concat(forecasts, names=["queue"]).reset_index(level=0).to_csv(out_dir / "forecast.csv", index=False)
    summary = write_memo(plan_df, acc_df, forecasts, out_dir)
    return {"accuracy": acc_df, "plan": plan_df, "forecasts": forecasts, "summary": summary}


def write_memo(plan: pd.DataFrame, acc: pd.DataFrame, forecasts: dict, out_dir: Path) -> dict:
    names = [s.name for s in SCENARIOS]
    now_by_q = dict(zip(plan.queue, plan.fte_needed_now))
    now = sum(now_by_q.values())
    # Queues peak in different weeks, so the combined requirement is the max of the weekly total, not a sum of peaks.
    weekly = pd.DataFrame({q: f.set_index("week")["fte"] for q, f in forecasts.items()})
    totals = weekly.sum(axis=1)
    peaks = {n: pd.DataFrame({q: f.set_index("week")[f"fte_{n}"] for q, f in forecasts.items()}).sum(axis=1).max()
             for n in names}
    # The most stretched queue at its own peak, and who has spare capacity that same week.
    own_gap = (weekly.max() - pd.Series(now_by_q))
    short_q = own_gap.idxmax()
    peak_week = weekly[short_q].idxmax()
    gap = (weekly.loc[peak_week] - pd.Series(now_by_q)).round(1)
    spare_q = gap.drop(short_q).idxmin()
    move = round(min(gap[short_q], max(0, -gap[spare_q])))
    hire = max(0, round(gap[short_q] - move))
    rows = "\n".join(
        "| " + " | ".join([str(r["queue"]), str(r["fte_needed_now"])] + [str(r[f"peak FTE: {n}"]) for n in names]
                          + [str(r["peak_week"]), f"{r['model']} ({r['wape_pct']}%)"]) + " |"
        for r in plan.to_dict("records"))
    header = "| Queue | FTE needed now | " + " | ".join(f"Peak FTE: {n}" for n in names) + " | Peak week | Model (backtest error) |"
    sep = "|" + "---|" * (4 + len(names))
    naive = acc[acc.model == "seasonal_naive"].wape_pct.mean()
    chosen = acc[acc.selected].wape_pct.mean()
    (out_dir / "planning_memo.md").write_text(f"""# Support capacity plan: next 26 weeks

**Bottom line:** today's workload needs **{now:.0f} FTE**, and the total requirement over the next 26 weeks stays
between **{totals.min():.0f} and {totals.max():.0f} FTE**. The pressure point is **{short_q}**: in the week of
**{peak_week:%d %B %Y}** it needs **{gap[short_q]:+.0f} FTE** over today, while **{spare_q}** needs
**{gap[spare_q]:+.0f}** that same week.

**Decisions needed:**
1. **Cross-train {move} {spare_q} agents to cover {short_q}** before {peak_week:%B}, using spare capacity rather than new hires.
   {"Hire " + str(hire) + " more FTE now (lead time about 8 weeks)." if hire else "That covers the base forecast with no net hiring."}
2. **Fund self-service as the growth hedge.** If volume runs 15% above forecast the peak needs
   **{peaks[names[1]]:.0f} FTE**; cutting handle time 10% brings that to **{peaks[names[2]]:.0f}**, worth
   **{peaks[names[1]] - peaks[names[2]]:.0f} FTE** that we would otherwise have to hire.

## By queue

{header}
{sep}
{rows}

## How far to trust it

Each queue's model was chosen by backtesting: refit at 4 past points and forecast 13 weeks ahead each time. The
selected models average **{chosen:.1f}% error**, against {naive:.1f}% for a "same week last year" baseline. The
shaded band in the chart is an 80% interval built from those real backtest errors.

![Forecast](forecast.png)

*Assumptions: 37.5-hour week, 30% shrinkage, 80% target occupancy. FTE figures are workload-based; an Erlang C model
per interval would refine them for service-level targets.*
""", encoding="utf-8")
    return {"now": now, "peak_week": peak_week, "peaks": peaks, "short": short_q, "spare": spare_q, "move": move}


if __name__ == "__main__":
    res = run()
    print(res["plan"].to_string(index=False))

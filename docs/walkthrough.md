# 3-minute walkthrough: Forecasting & Scenario Planning

A timed script for a Loom recording of about 3 minutes (screen plus camera bubble, 1080p). Say it in your own words; the lines are a guide, not a teleprompter.

**Open these tabs before you press record:** README, `output/forecast.png`, `forecasting/models.py`, `output/backtest_accuracy.csv`, `forecasting/planning.py`, `output/planning_memo.md`, `tests/test_forecasting.py`, GitHub Actions.

| Time | On screen | What to say |
|---|---|---|
| 0:00–0:20 | Portfolio card, then the README headline | A forecast is only useful when it changes a decision. This one says: cover next quarter's pressure point by cross-training 5 agents and hiring 1, not a hiring wave. |
| 0:20–0:40 | `output/forecast.png` | Three support queues with three years of synthetic weekly volume, each forecast 26 weeks ahead with an 80% interval. |
| 0:40–1:10 | `forecasting/models.py` | Four candidates: seasonal naive, the baseline every model must beat; a moving average; damped Holt-Winters; and a trend with yearly Fourier terms. Each queue picks its model by a rolling-origin back-test, four origins, 13 weeks ahead. |
| 1:10–1:30 | `output/backtest_accuracy.csv` | Selected models average 3.3 to 4.6% error against 8 to 20% for a moving average; overall 4.0% against 4.9% for same-week-last-year. The intervals come from those real back-test errors. |
| 1:30–1:55 | `forecasting/planning.py` | Volume becomes FTE: volume times handle time, divided by productive hours and occupancy. The assumptions, a 37.5-hour week, 30% shrinkage and 80% occupancy, are explicit constants. |
| 1:55–2:20 | `output/planning_memo.md`: by queue | Queues peak in different weeks, so it doesn't add the peaks. In March, Account Security needs 6 more FTE while Bookings needs 5 fewer, so cross-train first. |
| 2:20–2:40 | Memo: scenarios | The hedge: if growth runs 15% above forecast, self-service that trims handle time 10% is worth 15 FTE we'd otherwise hire. |
| 2:40–3:00 | `tests/`, then the README top | Five tests cover the baseline, model selection on seasonal data, the intervals and the FTE maths. An Erlang C model per interval is the next refinement. Links are under the video. |

## Recording checklist
- Close email, chat and notifications. Zoom the browser to 125% so code is readable.
- Run `python -m forecasting.run` once before recording so the outputs are fresh.
- Keep to one take per section; Loom lets you trim. Aim for 2:45 to 3:10.
- Show real numbers on screen as you say them; never estimate on camera.
- Say "synthetic weekly volumes" when you introduce the data. This is a skills demonstration, not a rebuild of client work.

## After recording
1. Copy the Loom share link.
2. In `README.md`, replace the walkthrough line with `- [x] [3-minute Loom walkthrough](<your Loom link>)` and add the link under the title.
3. Add the link to this project's card on saigwe.github.io.

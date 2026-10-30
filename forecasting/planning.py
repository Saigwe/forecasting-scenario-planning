"""Turn a volume forecast into headcount, and compare scenarios."""
from __future__ import annotations

from dataclasses import dataclass

PRODUCTIVE_HOURS_PER_FTE_WEEK = 37.5 * (1 - 0.30)   # 30% shrinkage: leave, training, meetings, sickness
TARGET_OCCUPANCY = 0.80                              # sustainable share of logged-in time spent handling contacts


@dataclass(frozen=True)
class Scenario:
    name: str
    volume_change: float = 0.0   # e.g. +0.15 for 15% more contacts than forecast
    aht_change: float = 0.0      # e.g. -0.10 for automation cutting handle time 10%


SCENARIOS = [
    Scenario("Base forecast"),
    Scenario("Growth +15%", volume_change=0.15),
    Scenario("Growth +15% with self-service (-10% AHT)", volume_change=0.15, aht_change=-0.10),
]


def required_fte(weekly_contacts: float, aht_seconds: float) -> float:
    workload_hours = weekly_contacts * aht_seconds / 3600
    return workload_hours / (PRODUCTIVE_HOURS_PER_FTE_WEEK * TARGET_OCCUPANCY)


def scenario_fte(weekly_contacts: float, aht_seconds: float, s: Scenario) -> float:
    return required_fte(weekly_contacts * (1 + s.volume_change), aht_seconds * (1 + s.aht_change))

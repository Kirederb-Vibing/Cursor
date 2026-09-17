from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Iterable


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


def charge_date(year: int, month: int, rule: str, day: int | None) -> date:
    last = monthrange(year, month)[1]
    if rule == "first":
        return date(year, month, 1)
    if rule == "last":
        return date(year, month, last)
    chosen = min(max(int(day or 1), 1), 31)
    return date(year, month, min(chosen, last))


def month_matches(month: int, cadence: str, anchor_month: int) -> bool:
    if cadence == "monthly":
        return True
    offset = (month - anchor_month) % 12
    if cadence == "quarterly":
        return offset % 3 == 0
    if cadence == "semiannual":
        return offset % 6 == 0
    if cadence == "yearly":
        return month == anchor_month
    raise ValueError(f"Ukendt kadence: {cadence}")


def occurrence_dates(
    *,
    cadence: str,
    charge_rule: str,
    charge_day: int | None,
    anchor_month: int,
    starts_on: date,
    ends_on: date | None,
    window_start: date,
    window_end: date,
) -> list[date]:
    """Return charge dates in [window_start, window_end] that also respect starts_on/ends_on.

    A subscription with ends_on=None continues indefinitely until it is removed.
    """
    if window_end < window_start:
        return []
    active_start = max(window_start, starts_on)
    active_end = window_end if ends_on is None else min(window_end, ends_on)
    if active_end < active_start:
        return []

    dates: list[date] = []
    year, month = active_start.year, active_start.month
    while (year, month) <= (active_end.year, active_end.month):
        if month_matches(month, cadence, anchor_month):
            charged = charge_date(year, month, charge_rule, charge_day)
            if active_start <= charged <= active_end:
                dates.append(charged)
        year, month = add_months(year, month, 1)
    return dates


def iter_horizon_months(start: date, months: int) -> Iterable[tuple[int, int]]:
    year, month = start.year, start.month
    for _ in range(months):
        yield year, month
        year, month = add_months(year, month, 1)

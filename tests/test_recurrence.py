from datetime import date

from app.recurrence import charge_date, occurrence_dates


def test_last_day_of_february_leap_and_non_leap():
    assert charge_date(2026, 2, "last", None) == date(2026, 2, 28)
    assert charge_date(2028, 2, "last", None) == date(2028, 2, 29)


def test_day_31_clamps_to_month_length():
    assert charge_date(2026, 4, "day_of_month", 31) == date(2026, 4, 30)
    assert charge_date(2026, 1, "day_of_month", 31) == date(2026, 1, 31)


def test_first_of_month():
    assert charge_date(2026, 9, "first", 15) == date(2026, 9, 1)


def test_monthly_without_end_continues():
    dates = occurrence_dates(
        cadence="monthly",
        charge_rule="day_of_month",
        charge_day=17,
        anchor_month=1,
        starts_on=date(2024, 1, 17),
        ends_on=None,
        window_start=date(2026, 1, 1),
        window_end=date(2026, 3, 31),
    )
    assert dates == [date(2026, 1, 17), date(2026, 2, 17), date(2026, 3, 17)]


def test_quarterly_from_january():
    dates = occurrence_dates(
        cadence="quarterly",
        charge_rule="first",
        charge_day=None,
        anchor_month=1,
        starts_on=date(2026, 1, 1),
        ends_on=None,
        window_start=date(2026, 1, 1),
        window_end=date(2026, 12, 31),
    )
    assert [d.month for d in dates] == [1, 4, 7, 10]


def test_semiannual_and_yearly():
    half = occurrence_dates(
        cadence="semiannual",
        charge_rule="day_of_month",
        charge_day=15,
        anchor_month=1,
        starts_on=date(2026, 1, 1),
        ends_on=None,
        window_start=date(2026, 1, 1),
        window_end=date(2026, 12, 31),
    )
    year = occurrence_dates(
        cadence="yearly",
        charge_rule="day_of_month",
        charge_day=12,
        anchor_month=3,
        starts_on=date(2026, 3, 12),
        ends_on=None,
        window_start=date(2026, 1, 1),
        window_end=date(2027, 12, 31),
    )
    assert [d.month for d in half] == [1, 7]
    assert year == [date(2026, 3, 12), date(2027, 3, 12)]


def test_removed_via_end_date_stops():
    dates = occurrence_dates(
        cadence="monthly",
        charge_rule="first",
        charge_day=None,
        anchor_month=1,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 2, 15),
        window_start=date(2026, 1, 1),
        window_end=date(2026, 6, 30),
    )
    assert dates == [date(2026, 1, 1), date(2026, 2, 1)]

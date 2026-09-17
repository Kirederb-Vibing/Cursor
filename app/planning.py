from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

from sqlmodel import Session, select

from app.formatting import format_dkk, format_date, month_label
from app.models import Account, HouseholdSettings, Mortgage, Person, RecurringItem
from app.recurrence import add_months, iter_horizon_months, occurrence_dates
from app.tax import march_payout_estimate


@dataclass
class Occurrence:
    date: date
    item_id: int
    kind: str
    name: str
    amount_ore: int
    signed_ore: int
    person_id: int | None
    from_account_id: int | None
    to_account_id: int | None
    category: str


@dataclass
class MonthBucket:
    year: int
    month: int
    label: str
    income_ore: int = 0
    expense_ore: int = 0
    external_ore: int = 0
    internal_ore: int = 0
    net_ore: int = 0
    occurrences: list[Occurrence] = field(default_factory=list)


def signed_amount(kind: str, amount_ore: int) -> int:
    if kind == "income":
        return amount_ore
    if kind in {"expense", "external_transfer"}:
        return -amount_ore
    return 0


def item_occurrences(item: RecurringItem, window_start: date, window_end: date) -> list[Occurrence]:
    if not item.active:
        return []
    dates = occurrence_dates(
        cadence=item.cadence,
        charge_rule=item.charge_rule,
        charge_day=item.charge_day,
        anchor_month=item.anchor_month or item.starts_on.month,
        starts_on=item.starts_on,
        ends_on=item.ends_on,
        window_start=window_start,
        window_end=window_end,
    )
    signed = signed_amount(item.kind, item.amount_ore)
    return [
        Occurrence(
            date=when,
            item_id=item.id or 0,
            kind=item.kind,
            name=item.name,
            amount_ore=item.amount_ore,
            signed_ore=signed,
            person_id=item.person_id,
            from_account_id=item.from_account_id,
            to_account_id=item.to_account_id,
            category=item.category or "",
        )
        for when in dates
    ]


def collect_occurrences(
    items: Iterable[RecurringItem], window_start: date, window_end: date
) -> list[Occurrence]:
    found: list[Occurrence] = []
    for item in items:
        found.extend(item_occurrences(item, window_start, window_end))
    found.sort(key=lambda row: (row.date, row.kind, row.name))
    return found


def _empty_months(today: date, months: int) -> dict[tuple[int, int], MonthBucket]:
    buckets: dict[tuple[int, int], MonthBucket] = {}
    for year, month in iter_horizon_months(today.replace(day=1), months):
        buckets[(year, month)] = MonthBucket(
            year=year, month=month, label=month_label(year, month).capitalize()
        )
    return buckets


def build_plan(
    session: Session,
    *,
    today: date | None = None,
    months: int = 12,
    person_id: int | None = None,
) -> dict:
    today = today or date.today()
    month_start = today.replace(day=1)
    end_year, end_month = add_months(today.year, today.month, months - 1)
    from calendar import monthrange

    window_end = date(end_year, end_month, monthrange(end_year, end_month)[1])
    items = session.exec(select(RecurringItem)).all()
    if person_id is not None:
        items = [item for item in items if item.person_id == person_id or item.person_id is None]
    occurrences = collect_occurrences(items, month_start, window_end)
    buckets = _empty_months(today, months)
    for occ in occurrences:
        bucket = buckets.get((occ.date.year, occ.date.month))
        if not bucket:
            continue
        bucket.occurrences.append(occ)
        if occ.kind == "income":
            bucket.income_ore += occ.amount_ore
        elif occ.kind == "expense":
            bucket.expense_ore += occ.amount_ore
        elif occ.kind == "external_transfer":
            bucket.external_ore += occ.amount_ore
        elif occ.kind == "internal_transfer":
            bucket.internal_ore += occ.amount_ore
        bucket.net_ore += occ.signed_ore

    people = session.exec(select(Person).order_by(Person.name)).all()
    accounts = session.exec(select(Account).order_by(Account.name)).all()
    person_map = {p.id: p for p in people}
    account_map = {a.id: a for a in accounts}

    balances = forecast_accounts(accounts, occurrences, today)
    upcoming_transfers = [
        occ
        for occ in occurrences
        if occ.kind in {"internal_transfer", "external_transfer"} and occ.date >= today
    ][:12]
    upcoming_charges = [occ for occ in occurrences if occ.date >= today][:16]

    this_month = buckets.get((today.year, today.month))
    next_y, next_m = add_months(today.year, today.month, 1)
    next_month = buckets.get((next_y, next_m))

    tax = household_tax(session, today.year)
    settings = session.get(HouseholdSettings, 1)

    return {
        "today": today,
        "settings": settings,
        "months": list(buckets.values()),
        "occurrences": occurrences,
        "people": people,
        "accounts": accounts,
        "person_map": person_map,
        "account_map": account_map,
        "balances": balances,
        "upcoming_transfers": upcoming_transfers,
        "upcoming_charges": upcoming_charges,
        "this_month": this_month,
        "next_month": next_month,
        "tax": tax,
        "person_id": person_id,
    }


def forecast_accounts(
    accounts: list[Account], occurrences: list[Occurrence], today: date
) -> list[dict]:
    rows = []
    for account in accounts:
        start_balance = account.opening_balance_ore
        projected = start_balance
        next_move = None
        for occ in occurrences:
            if occ.date < today:
                continue
            delta = 0
            if occ.from_account_id == account.id:
                delta -= occ.amount_ore
            if occ.to_account_id == account.id:
                delta += occ.amount_ore
            if delta:
                projected += delta
                if next_move is None:
                    next_move = occ
        rows.append(
            {
                "account": account,
                "opening_ore": start_balance,
                "projected_ore": projected,
                "next_move": next_move,
            }
        )
    return rows


def household_tax(session: Session, tax_year: int) -> dict:
    settings = session.get(HouseholdSettings, 1)
    mortgages = session.exec(select(Mortgage)).all()
    estimates = []
    total_payout = 0
    total_interest = 0
    total_value = 0
    for mortgage in mortgages:
        estimate = march_payout_estimate(
            tax_year=tax_year,
            remaining_principal_ore=mortgage.remaining_principal_ore,
            interest_rate_pct=mortgage.interest_rate_pct,
            contribution_rate_pct=mortgage.contribution_rate_pct,
            annual_interest_override_ore=mortgage.annual_interest_override_ore,
            forskud_interest_ore=mortgage.forskud_interest_ore,
            property_value_ore=mortgage.property_value_ore,
            municipal_tax_pct=settings.municipal_tax_pct if settings else 25.05,
            church_tax_pct=settings.church_tax_pct if settings else 0.0,
            is_couple=settings.is_couple if settings else True,
        )
        estimates.append({"mortgage": mortgage, "estimate": estimate})
        total_payout += estimate.estimated_march_payout_ore
        total_interest += estimate.annual_interest_ore
        total_value += estimate.rentefradrag_value_ore
    return {
        "year": tax_year,
        "payout_label": f"marts {tax_year + 1}",
        "estimates": estimates,
        "total_payout_ore": total_payout,
        "total_interest_ore": total_interest,
        "total_value_ore": total_value,
    }


def occurrence_public(occ: Occurrence, person_map, account_map) -> dict:
    return {
        "date": occ.date.isoformat(),
        "date_label": format_date(occ.date),
        "item_id": occ.item_id,
        "kind": occ.kind,
        "name": occ.name,
        "amount_ore": occ.amount_ore,
        "amount_dkk": occ.amount_ore / 100,
        "amount_label": format_dkk(occ.amount_ore),
        "signed_ore": occ.signed_ore,
        "person_id": occ.person_id,
        "person": person_map.get(occ.person_id).name if occ.person_id in person_map else None,
        "from_account_id": occ.from_account_id,
        "from_account": (
            account_map.get(occ.from_account_id).name if occ.from_account_id in account_map else None
        ),
        "to_account_id": occ.to_account_id,
        "to_account": (
            account_map.get(occ.to_account_id).name if occ.to_account_id in account_map else None
        ),
        "category": occ.category,
    }

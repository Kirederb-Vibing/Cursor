from __future__ import annotations

import secrets
from datetime import date

from sqlmodel import Session, select

from app.models import Account, HouseholdSettings, Mortgage, Person, RecurringItem
from app.tax import DEFAULT_MUNICIPAL_TAX_PCT


def ensure_settings(session: Session) -> HouseholdSettings:
    settings = session.get(HouseholdSettings, 1)
    if settings is None:
        settings = HouseholdSettings(
            id=1,
            name="Min husstand",
            is_couple=True,
            municipal_tax_pct=DEFAULT_MUNICIPAL_TAX_PCT,
            api_key=secrets.token_urlsafe(24),
        )
        session.add(settings)
        session.commit()
        session.refresh(settings)
    elif not settings.api_key:
        settings.api_key = secrets.token_urlsafe(24)
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


def rotate_api_key(session: Session) -> str:
    settings = ensure_settings(session)
    settings.api_key = secrets.token_urlsafe(24)
    session.add(settings)
    session.commit()
    return settings.api_key


def seed_demo(session: Session, *, force: bool = False) -> None:
    settings = ensure_settings(session)
    existing = session.exec(select(Person)).first()
    if existing and not force:
        return
    if force:
        for model in (RecurringItem, Mortgage, Account, Person):
            for row in session.exec(select(model)).all():
                session.delete(row)
        session.commit()

    anna = Person(name="Anna", color="#0f5c4c", yearly_gross_ore=48_000_000)
    bo = Person(name="Bo", color="#7a3e12", yearly_gross_ore=42_000_000)
    session.add(anna)
    session.add(bo)
    session.commit()
    session.refresh(anna)
    session.refresh(bo)

    lon_anna = Account(name="Løn Anna", kind="checking", opening_balance_ore=1_240_000)
    lon_bo = Account(name="Løn Bo", kind="checking", opening_balance_ore=980_000)
    faelles = Account(name="Fælleskonto", kind="shared", opening_balance_ore=2_150_000)
    opsparing = Account(name="Opsparing", kind="savings", opening_balance_ore=8_400_000)
    buffer = Account(name="Buffer", kind="buffer", opening_balance_ore=3_000_000)
    session.add(lon_anna)
    session.add(lon_bo)
    session.add(faelles)
    session.add(opsparing)
    session.add(buffer)
    session.commit()
    for account in (lon_anna, lon_bo, faelles, opsparing, buffer):
        session.refresh(account)

    today = date.today()
    start = date(today.year, 1, 1)

    def add(**kwargs):
        session.add(RecurringItem(**kwargs))

    add(
        kind="income",
        name="Løn Anna",
        amount_ore=3_800_000,
        cadence="monthly",
        charge_rule="last",
        charge_day=None,
        anchor_month=1,
        starts_on=start,
        person_id=anna.id,
        to_account_id=lon_anna.id,
        category="løn",
    )
    add(
        kind="income",
        name="Løn Bo",
        amount_ore=3_200_000,
        cadence="monthly",
        charge_rule="last",
        charge_day=None,
        anchor_month=1,
        starts_on=start,
        person_id=bo.id,
        to_account_id=lon_bo.id,
        category="løn",
    )
    add(
        kind="internal_transfer",
        name="Anna til fælles",
        amount_ore=1_600_000,
        cadence="monthly",
        charge_rule="first",
        charge_day=None,
        anchor_month=1,
        starts_on=start,
        person_id=anna.id,
        from_account_id=lon_anna.id,
        to_account_id=faelles.id,
        category="fælles",
    )
    add(
        kind="internal_transfer",
        name="Bo til fælles",
        amount_ore=1_400_000,
        cadence="monthly",
        charge_rule="first",
        charge_day=None,
        anchor_month=1,
        starts_on=start,
        person_id=bo.id,
        from_account_id=lon_bo.id,
        to_account_id=faelles.id,
        category="fælles",
    )
    add(
        kind="internal_transfer",
        name="Til opsparing",
        amount_ore=500_000,
        cadence="monthly",
        charge_rule="day_of_month",
        charge_day=2,
        anchor_month=1,
        starts_on=start,
        from_account_id=faelles.id,
        to_account_id=opsparing.id,
        category="opsparing",
    )
    add(
        kind="internal_transfer",
        name="Til buffer",
        amount_ore=150_000,
        cadence="monthly",
        charge_rule="day_of_month",
        charge_day=2,
        anchor_month=1,
        starts_on=start,
        from_account_id=faelles.id,
        to_account_id=buffer.id,
        category="buffer",
    )
    add(
        kind="expense",
        name="Realkredit ydelseskonto",
        amount_ore=1_185_000,
        cadence="monthly",
        charge_rule="first",
        charge_day=None,
        anchor_month=1,
        starts_on=start,
        from_account_id=faelles.id,
        category="bolig",
    )
    add(
        kind="expense",
        name="Husforsikring",
        amount_ore=240_000,
        cadence="quarterly",
        charge_rule="first",
        charge_day=None,
        anchor_month=1,
        starts_on=start,
        from_account_id=faelles.id,
        category="bolig",
    )
    add(
        kind="expense",
        name="Ejendomsforsikring tillæg",
        amount_ore=180_000,
        cadence="semiannual",
        charge_rule="day_of_month",
        charge_day=15,
        anchor_month=1,
        starts_on=start,
        from_account_id=faelles.id,
        category="bolig",
    )
    add(
        kind="expense",
        name="Licens og streaming",
        amount_ore=149_00,
        cadence="monthly",
        charge_rule="day_of_month",
        charge_day=17,
        anchor_month=1,
        starts_on=start,
        from_account_id=faelles.id,
        category="abonnement",
    )
    add(
        kind="expense",
        name="Mobil Anna",
        amount_ore=199_00,
        cadence="monthly",
        charge_rule="day_of_month",
        charge_day=8,
        anchor_month=1,
        starts_on=start,
        person_id=anna.id,
        from_account_id=lon_anna.id,
        category="abonnement",
    )
    add(
        kind="expense",
        name="Mobil Bo",
        amount_ore=149_00,
        cadence="monthly",
        charge_rule="last",
        charge_day=None,
        anchor_month=1,
        starts_on=start,
        person_id=bo.id,
        from_account_id=lon_bo.id,
        category="abonnement",
    )
    add(
        kind="expense",
        name="Bilforsikring",
        amount_ore=1_680_00,
        cadence="yearly",
        charge_rule="day_of_month",
        charge_day=12,
        anchor_month=3,
        starts_on=date(today.year, 3, 12),
        from_account_id=faelles.id,
        category="transport",
    )
    add(
        kind="external_transfer",
        name="Børneopsparing bank",
        amount_ore=300_00,
        cadence="monthly",
        charge_rule="day_of_month",
        charge_day=5,
        anchor_month=1,
        starts_on=start,
        from_account_id=faelles.id,
        category="børn",
    )
    session.add(
        Mortgage(
            name="Realkredit bolig",
            remaining_principal_ore=248_000_000,
            interest_rate_pct=3.85,
            contribution_rate_pct=0.55,
            forskud_interest_ore=0,
            property_value_ore=310_000_000,
        )
    )
    settings.name = "Familien"
    settings.is_couple = True
    settings.seeded = True
    session.add(settings)
    session.commit()

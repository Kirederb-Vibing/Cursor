from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class HouseholdSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=1, primary_key=True)
    name: str = "Min husstand"
    is_couple: bool = True
    municipal_tax_pct: float = 25.05
    church_tax_pct: float = 0.0
    n8n_webhook_url: str = ""
    api_key: str = ""
    seeded: bool = False
    onboarded: bool = False
    updated_at: datetime = Field(default_factory=_now)


class Person(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    color: str = "#0f5c4c"
    notes: str = ""
    yearly_gross_ore: int = 0
    role: str = "member"
    can_login: bool = False
    password_hash: str = ""
    created_at: datetime = Field(default_factory=_now)


class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    kind: str = "checking"  # checking, shared, savings, buffer, other
    opening_balance_ore: int = 0
    opening_on: Optional[date] = None
    created_at: datetime = Field(default_factory=_now)


class RecurringItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str  # income, expense, internal_transfer, external_transfer
    name: str
    amount_ore: int
    cadence: str = "monthly"
    charge_rule: str = "day_of_month"
    charge_day: Optional[int] = 1
    anchor_month: int = 1
    starts_on: date
    ends_on: Optional[date] = None
    person_id: Optional[int] = Field(default=None, foreign_key="person.id")
    from_account_id: Optional[int] = Field(default=None, foreign_key="account.id")
    to_account_id: Optional[int] = Field(default=None, foreign_key="account.id")
    category: str = ""
    notes: str = ""
    active: bool = True
    external_id: str = ""
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Mortgage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = "Huslån"
    remaining_principal_ore: int = 0
    interest_rate_pct: float = 0.0
    contribution_rate_pct: float = 0.0
    annual_interest_override_ore: Optional[int] = None
    forskud_interest_ore: int = 0
    property_value_ore: Optional[int] = None
    person_id: Optional[int] = Field(default=None, foreign_key="person.id")
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PersonIn(BaseModel):
    name: str
    color: str = "#0f5c4c"
    notes: str = ""
    yearly_gross_dkk: Optional[float] = None
    yearly_gross_ore: Optional[int] = None
    external_id: str = ""


class AccountIn(BaseModel):
    name: str
    kind: str = "checking"
    opening_balance_dkk: Optional[float] = None
    opening_balance_ore: Optional[int] = None
    opening_on: Optional[date] = None


class ItemIn(BaseModel):
    kind: str = Field(default="expense", description="income | expense | internal_transfer | external_transfer")
    name: str
    amount_dkk: Optional[float] = None
    amount_ore: Optional[int] = None
    cadence: str = Field(default="monthly", description="monthly | quarterly | semiannual | yearly")
    charge_rule: str = Field(default="day_of_month", description="first | last | day_of_month")
    charge_day: Optional[int] = 1
    anchor_month: Optional[int] = None
    starts_on: date
    ends_on: Optional[date] = None
    person_id: Optional[int] = None
    from_account_id: Optional[int] = None
    to_account_id: Optional[int] = None
    category: str = ""
    notes: str = ""
    active: bool = True
    external_id: str = ""


class MortgageIn(BaseModel):
    name: str = "Huslån"
    remaining_principal_dkk: Optional[float] = None
    remaining_principal_ore: Optional[int] = None
    interest_rate_pct: float = 0.0
    contribution_rate_pct: float = 0.0
    annual_interest_override_dkk: Optional[float] = None
    annual_interest_override_ore: Optional[int] = None
    forskud_interest_dkk: Optional[float] = None
    forskud_interest_ore: Optional[int] = None
    property_value_dkk: Optional[float] = None
    property_value_ore: Optional[int] = None
    person_id: Optional[int] = None


class SettingsIn(BaseModel):
    name: Optional[str] = None
    is_couple: Optional[bool] = None
    municipal_tax_pct: Optional[float] = None
    church_tax_pct: Optional[float] = None
    n8n_webhook_url: Optional[str] = None
    rotate_api_key: bool = False

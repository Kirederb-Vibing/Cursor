from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.models import Account, HouseholdSettings, Mortgage, Person, RecurringItem
from app.schemas import AccountIn, ItemIn, MortgageIn, PersonIn, SettingsIn
from app.seed import rotate_api_key
from app.webhooks import emit_event, item_payload


def _ore(*candidates) -> Optional[int]:
    for value in candidates:
        if value is None:
            continue
        if isinstance(value, float):
            return int(round(value * 100))
        return int(value)
    return None


def create_person(session: Session, data: PersonIn) -> Person:
    person = Person(
        name=data.name.strip(),
        color=data.color or "#0f5c4c",
        notes=data.notes or "",
        yearly_gross_ore=_ore(data.yearly_gross_ore, data.yearly_gross_dkk) or 0,
    )
    session.add(person)
    session.commit()
    session.refresh(person)
    emit_event(session, "person.created", {"id": person.id, "name": person.name})
    return person


def create_account(session: Session, data: AccountIn) -> Account:
    account = Account(
        name=data.name.strip(),
        kind=data.kind or "checking",
        opening_balance_ore=_ore(data.opening_balance_ore, data.opening_balance_dkk) or 0,
        opening_on=data.opening_on,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    emit_event(session, "account.created", {"id": account.id, "name": account.name})
    return account


def _item_from_schema(data: ItemIn, existing: RecurringItem | None = None) -> RecurringItem:
    amount = _ore(data.amount_ore, data.amount_dkk)
    if amount is None:
        raise ValueError("Beløb mangler (amount_dkk eller amount_ore)")
    if data.kind not in {"income", "expense", "internal_transfer", "external_transfer"}:
        raise ValueError("Ugyldig type")
    if data.cadence not in {"monthly", "quarterly", "semiannual", "yearly"}:
        raise ValueError("Ugyldig kadence")
    if data.charge_rule not in {"first", "last", "day_of_month"}:
        raise ValueError("Ugyldig hævereegel")
    item = existing or RecurringItem(
        kind=data.kind,
        name=data.name,
        amount_ore=amount,
        cadence=data.cadence,
        charge_rule=data.charge_rule,
        charge_day=data.charge_day,
        anchor_month=data.anchor_month or data.starts_on.month,
        starts_on=data.starts_on,
        ends_on=data.ends_on,
        person_id=data.person_id,
        from_account_id=data.from_account_id,
        to_account_id=data.to_account_id,
        category=data.category or "",
        notes=data.notes or "",
        active=data.active,
        external_id=data.external_id or "",
    )
    if existing:
        item.kind = data.kind
        item.name = data.name.strip()
        item.amount_ore = amount
        item.cadence = data.cadence
        item.charge_rule = data.charge_rule
        item.charge_day = data.charge_day
        item.anchor_month = data.anchor_month or data.starts_on.month
        item.starts_on = data.starts_on
        item.ends_on = data.ends_on
        item.person_id = data.person_id
        item.from_account_id = data.from_account_id
        item.to_account_id = data.to_account_id
        item.category = data.category or ""
        item.notes = data.notes or ""
        item.active = data.active
        if data.external_id:
            item.external_id = data.external_id
        item.updated_at = datetime.now(timezone.utc)
    return item


def upsert_item(session: Session, data: ItemIn) -> tuple[RecurringItem, bool]:
    existing = None
    if data.external_id:
        existing = session.exec(
            select(RecurringItem).where(RecurringItem.external_id == data.external_id)
        ).first()
    created = existing is None
    item = _item_from_schema(data, existing)
    session.add(item)
    session.commit()
    session.refresh(item)
    emit_event(session, "item.created" if created else "item.updated", item_payload(item))
    return item, created


def update_item(session: Session, item: RecurringItem, data: ItemIn) -> RecurringItem:
    updated = _item_from_schema(data, item)
    session.add(updated)
    session.commit()
    session.refresh(updated)
    emit_event(session, "item.updated", item_payload(updated))
    return updated


def delete_item(session: Session, item: RecurringItem) -> None:
    payload = item_payload(item)
    session.delete(item)
    session.commit()
    emit_event(session, "item.deleted", payload)


def upsert_mortgage(session: Session, data: MortgageIn, mortgage: Mortgage | None = None) -> Mortgage:
    row = mortgage or Mortgage(name=data.name)
    row.name = data.name
    row.remaining_principal_ore = (
        _ore(data.remaining_principal_ore, data.remaining_principal_dkk) or 0
    )
    row.interest_rate_pct = data.interest_rate_pct
    row.contribution_rate_pct = data.contribution_rate_pct
    override = _ore(data.annual_interest_override_ore, data.annual_interest_override_dkk)
    row.annual_interest_override_ore = override
    row.forskud_interest_ore = _ore(data.forskud_interest_ore, data.forskud_interest_dkk) or 0
    row.property_value_ore = _ore(data.property_value_ore, data.property_value_dkk)
    row.person_id = data.person_id
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    emit_event(session, "mortgage.updated", {"id": row.id, "name": row.name})
    return row


def update_settings(session: Session, data: SettingsIn) -> HouseholdSettings:
    settings = session.get(HouseholdSettings, 1)
    if data.name is not None:
        settings.name = data.name.strip() or settings.name
    if data.is_couple is not None:
        settings.is_couple = data.is_couple
    if data.municipal_tax_pct is not None:
        settings.municipal_tax_pct = data.municipal_tax_pct
    if data.church_tax_pct is not None:
        settings.church_tax_pct = data.church_tax_pct
    if data.n8n_webhook_url is not None:
        settings.n8n_webhook_url = data.n8n_webhook_url.strip()
    if data.rotate_api_key:
        rotate_api_key(session)
        session.refresh(settings)
    else:
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


def public_item(item: RecurringItem) -> dict:
    return {
        "id": item.id,
        "kind": item.kind,
        "name": item.name,
        "amount_ore": item.amount_ore,
        "amount_dkk": item.amount_ore / 100,
        "cadence": item.cadence,
        "charge_rule": item.charge_rule,
        "charge_day": item.charge_day,
        "anchor_month": item.anchor_month,
        "starts_on": item.starts_on.isoformat(),
        "ends_on": item.ends_on.isoformat() if item.ends_on else None,
        "person_id": item.person_id,
        "from_account_id": item.from_account_id,
        "to_account_id": item.to_account_id,
        "category": item.category,
        "notes": item.notes,
        "active": item.active,
        "external_id": item.external_id,
        "continues_until_removed": item.ends_on is None,
    }

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select

from app.auth import require_api_key
from app.crud import (
    create_account,
    create_person,
    delete_item,
    public_item,
    update_item,
    update_settings,
    upsert_item,
    upsert_mortgage,
)
from app.database import get_engine
from app.formatting import format_dkk
from app.icsfeed import to_ics
from app.models import Account, Mortgage, Person, RecurringItem
from app.planning import build_plan, household_tax, occurrence_public
from app.schemas import AccountIn, ItemIn, MortgageIn, PersonIn, SettingsIn
from app.seed import ensure_settings
from app.tax import rough_income_tax

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])


def get_session():
    with Session(get_engine()) as session:
        yield session


@router.get("/people")
def list_people(session: Session = Depends(get_session)):
    people = session.exec(select(Person).order_by(Person.name)).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "color": p.color,
            "notes": p.notes,
            "yearly_gross_ore": p.yearly_gross_ore,
            "yearly_gross_dkk": p.yearly_gross_ore / 100,
        }
        for p in people
    ]


@router.post("/people", status_code=201)
def add_person(data: PersonIn, session: Session = Depends(get_session)):
    person = create_person(session, data)
    return {"id": person.id, "name": person.name}


@router.get("/accounts")
def list_accounts(session: Session = Depends(get_session)):
    accounts = session.exec(select(Account).order_by(Account.name)).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "kind": a.kind,
            "opening_balance_ore": a.opening_balance_ore,
            "opening_balance_dkk": a.opening_balance_ore / 100,
            "opening_on": a.opening_on,
        }
        for a in accounts
    ]


@router.post("/accounts", status_code=201)
def add_account(data: AccountIn, session: Session = Depends(get_session)):
    account = create_account(session, data)
    return {"id": account.id, "name": account.name}


@router.get("/items")
def list_items(
    kind: str | None = None,
    active: bool | None = None,
    session: Session = Depends(get_session),
):
    items = session.exec(select(RecurringItem).order_by(RecurringItem.name)).all()
    if kind:
        items = [i for i in items if i.kind == kind]
    if active is not None:
        items = [i for i in items if i.active is active]
    return [public_item(i) for i in items]


@router.post("/items", status_code=201)
def add_item(data: ItemIn, session: Session = Depends(get_session)):
    try:
        item, created = upsert_item(session, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"created": created, "item": public_item(item)}


@router.post("/subscriptions", status_code=201)
def add_subscription(data: ItemIn, session: Session = Depends(get_session)):
    payload = data.model_copy(update={"kind": data.kind or "expense"})
    if payload.kind not in {"expense", "external_transfer"}:
        payload = payload.model_copy(update={"kind": "expense"})
    try:
        item, created = upsert_item(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"created": created, "item": public_item(item)}


@router.get("/items/{item_id}")
def get_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(RecurringItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ikke fundet")
    return public_item(item)


@router.put("/items/{item_id}")
def put_item(item_id: int, data: ItemIn, session: Session = Depends(get_session)):
    item = session.get(RecurringItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ikke fundet")
    try:
        updated = update_item(session, item, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return public_item(updated)


@router.delete("/items/{item_id}")
def remove_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(RecurringItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ikke fundet")
    delete_item(session, item)
    return {"ok": True}


@router.get("/overview")
def overview(
    months: int = Query(default=12, ge=1, le=36),
    person_id: int | None = None,
    session: Session = Depends(get_session),
):
    plan = build_plan(session, months=months, person_id=person_id)
    return {
        "household": plan["settings"].name if plan["settings"] else "",
        "today": plan["today"].isoformat(),
        "this_month_net_ore": plan["this_month"].net_ore if plan["this_month"] else 0,
        "next_month_net_ore": plan["next_month"].net_ore if plan["next_month"] else 0,
        "this_month_net_dkk": (plan["this_month"].net_ore if plan["this_month"] else 0) / 100,
        "next_month_net_dkk": (plan["next_month"].net_ore if plan["next_month"] else 0) / 100,
        "estimated_march_payout_ore": plan["tax"]["total_payout_ore"],
        "estimated_march_payout_dkk": plan["tax"]["total_payout_ore"] / 100,
        "payout_label": plan["tax"]["payout_label"],
        "months": [
            {
                "year": m.year,
                "month": m.month,
                "label": m.label,
                "income_ore": m.income_ore,
                "expense_ore": m.expense_ore,
                "external_ore": m.external_ore,
                "internal_ore": m.internal_ore,
                "net_ore": m.net_ore,
                "income_dkk": m.income_ore / 100,
                "expense_dkk": m.expense_ore / 100,
                "net_dkk": m.net_ore / 100,
            }
            for m in plan["months"]
        ],
        "upcoming": [
            occurrence_public(o, plan["person_map"], plan["account_map"])
            for o in plan["upcoming_charges"]
        ],
        "upcoming_transfers": [
            occurrence_public(o, plan["person_map"], plan["account_map"])
            for o in plan["upcoming_transfers"]
        ],
        "accounts": [
            {
                "id": row["account"].id,
                "name": row["account"].name,
                "kind": row["account"].kind,
                "opening_dkk": row["opening_ore"] / 100,
                "projected_dkk": row["projected_ore"] / 100,
            }
            for row in plan["balances"]
        ],
    }


@router.get("/overview/upcoming")
def upcoming(session: Session = Depends(get_session)):
    plan = build_plan(session)
    return [
        occurrence_public(o, plan["person_map"], plan["account_map"])
        for o in plan["upcoming_charges"]
    ]


def _ha_sensors(session: Session) -> dict:
    plan = build_plan(session)
    nxt = plan["upcoming_transfers"][0] if plan["upcoming_transfers"] else None
    charge = next((o for o in plan["upcoming_charges"] if o.kind == "expense"), None)
    this_net = plan["this_month"].net_ore if plan["this_month"] else 0
    next_net = plan["next_month"].net_ore if plan["next_month"] else 0
    march = plan["tax"]["total_payout_ore"]
    sensors = [
        {
            "unique_id": "faelleskassen_this_month_net",
            "name": "Økonomi denne måned netto",
            "state": round(this_net / 100, 2),
            "unit_of_measurement": "DKK",
            "icon": "mdi:calendar-month",
            "device_class": "monetary",
        },
        {
            "unique_id": "faelleskassen_next_month_net",
            "name": "Økonomi næste måned netto",
            "state": round(next_net / 100, 2),
            "unit_of_measurement": "DKK",
            "icon": "mdi:calendar-arrow-right",
            "device_class": "monetary",
        },
        {
            "unique_id": "faelleskassen_march_payout",
            "name": f"Estimeret skatteudbetaling {plan['tax']['payout_label']}",
            "state": round(march / 100, 2),
            "unit_of_measurement": "DKK",
            "icon": "mdi:home-city",
            "device_class": "monetary",
        },
        {
            "unique_id": "faelleskassen_next_transfer_amount",
            "name": "Næste overførsel beløb",
            "state": round((nxt.amount_ore if nxt else 0) / 100, 2),
            "unit_of_measurement": "DKK",
            "icon": "mdi:bank-transfer",
            "device_class": "monetary",
        },
        {
            "unique_id": "faelleskassen_next_transfer_name",
            "name": "Næste overførsel",
            "state": nxt.name if nxt else "Ingen",
            "icon": "mdi:swap-horizontal",
        },
        {
            "unique_id": "faelleskassen_next_transfer_date",
            "name": "Næste overførsel dato",
            "state": nxt.date.isoformat() if nxt else "",
            "icon": "mdi:calendar",
            "device_class": "date",
        },
        {
            "unique_id": "faelleskassen_next_subscription",
            "name": "Næste abonnement",
            "state": charge.name if charge else "Ingen",
            "icon": "mdi:receipt-text",
        },
        {
            "unique_id": "faelleskassen_next_subscription_amount",
            "name": "Næste abonnement beløb",
            "state": round((charge.amount_ore if charge else 0) / 100, 2),
            "unit_of_measurement": "DKK",
            "icon": "mdi:cash",
            "device_class": "monetary",
        },
    ]
    markdown_lines = ["### Forventede poster", ""]
    for occ in plan["upcoming_charges"][:8]:
        markdown_lines.append(
            f"- **{occ.date.isoformat()}** {occ.name}: {format_dkk(occ.amount_ore)}"
        )
    return {
        "denne_maaned_netto": round(this_net / 100, 2),
        "naeste_maaned_netto": round(next_net / 100, 2),
        "forventet_marts_udbetaling": round(march / 100, 2),
        "marts_label": plan["tax"]["payout_label"],
        "naeste_overfoersel_navn": nxt.name if nxt else None,
        "naeste_overfoersel_beloeb": round((nxt.amount_ore if nxt else 0) / 100, 2),
        "naeste_overfoersel_dato": nxt.date.isoformat() if nxt else None,
        "naeste_abonnement_navn": charge.name if charge else None,
        "naeste_abonnement_beloeb": round((charge.amount_ore if charge else 0) / 100, 2),
        "markdown": "\n".join(markdown_lines),
        "sensors": sensors,
    }


@router.get("/ha/sensors")
def ha_sensors(session: Session = Depends(get_session)):
    return _ha_sensors(session)


@router.get("/ha/states")
def ha_states(session: Session = Depends(get_session)):
    return _ha_sensors(session)["sensors"]


@router.get("/ha/calendar.ics")
def ha_calendar(session: Session = Depends(get_session)):
    plan = build_plan(session, months=18)
    settings = plan["settings"]
    body = to_ics(plan["occurrences"], settings.name if settings else "Fælleskassen")
    return PlainTextResponse(body, media_type="text/calendar; charset=utf-8")


@router.get("/tax")
def tax_overview(session: Session = Depends(get_session)):
    settings = ensure_settings(session)
    year = date.today().year
    result = household_tax(session, year)
    people = session.exec(select(Person)).all()
    incomes = [
        {
            "person": p.name,
            "tax": rough_income_tax(
                p.yearly_gross_ore,
                municipal_tax_pct=settings.municipal_tax_pct,
                church_tax_pct=settings.church_tax_pct,
            ).__dict__,
        }
        for p in people
        if p.yearly_gross_ore
    ]
    return {
        "tax_year": year,
        "payout_label": result["payout_label"],
        "is_couple": settings.is_couple,
        "municipal_tax_pct": settings.municipal_tax_pct,
        "church_tax_pct": settings.church_tax_pct,
        "mortgages": [
            {
                "id": row["mortgage"].id,
                "name": row["mortgage"].name,
                "annual_interest_dkk": row["estimate"].annual_interest_ore / 100,
                "rentefradrag_dkk": row["estimate"].rentefradrag_value_ore / 100,
                "march_payout_dkk": row["estimate"].estimated_march_payout_ore / 100,
                "disclaimer": row["estimate"].disclaimer,
            }
            for row in result["estimates"]
        ],
        "total_march_payout_dkk": result["total_payout_ore"] / 100,
        "incomes": incomes,
    }


@router.get("/mortgages")
def list_mortgages(session: Session = Depends(get_session)):
    rows = session.exec(select(Mortgage)).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "remaining_principal_dkk": m.remaining_principal_ore / 100,
            "interest_rate_pct": m.interest_rate_pct,
            "contribution_rate_pct": m.contribution_rate_pct,
            "annual_interest_override_dkk": (
                None
                if m.annual_interest_override_ore is None
                else m.annual_interest_override_ore / 100
            ),
            "forskud_interest_dkk": m.forskud_interest_ore / 100,
            "property_value_dkk": None if m.property_value_ore is None else m.property_value_ore / 100,
            "person_id": m.person_id,
        }
        for m in rows
    ]


@router.post("/mortgages", status_code=201)
def add_mortgage(data: MortgageIn, session: Session = Depends(get_session)):
    return {"id": upsert_mortgage(session, data).id}


@router.get("/settings")
def get_settings_api(session: Session = Depends(get_session)):
    settings = ensure_settings(session)
    return {
        "name": settings.name,
        "is_couple": settings.is_couple,
        "municipal_tax_pct": settings.municipal_tax_pct,
        "church_tax_pct": settings.church_tax_pct,
        "n8n_webhook_url": settings.n8n_webhook_url,
        "api_key": settings.api_key,
    }


@router.patch("/settings")
def patch_settings(data: SettingsIn, session: Session = Depends(get_session)):
    settings = update_settings(session, data)
    return {
        "name": settings.name,
        "is_couple": settings.is_couple,
        "municipal_tax_pct": settings.municipal_tax_pct,
        "church_tax_pct": settings.church_tax_pct,
        "n8n_webhook_url": settings.n8n_webhook_url,
        "api_key": settings.api_key,
    }

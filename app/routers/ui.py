from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.auth import current_api_key, require_ui
from app.config import settings as env_settings
from app.crud import create_account, create_person, delete_item, update_item, upsert_item, upsert_mortgage
from app.database import get_engine
from app.formatting import (
    CADENCE_DA,
    CHARGE_RULE_DA,
    KIND_DA,
    MONTHS_DA,
    format_date,
    format_dkk,
    format_short_date,
    parse_dkk,
)
from app.models import Account, Mortgage, Person, RecurringItem
from app.planning import build_plan
from app.schemas import AccountIn, ItemIn, MortgageIn, PersonIn
from app.seed import ensure_settings, rotate_api_key, seed_demo
from app.tax import rough_income_tax

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
templates.env.filters["dkk"] = format_dkk
templates.env.filters["dato"] = format_date
templates.env.filters["shortdate"] = format_short_date

router = APIRouter(dependencies=[Depends(require_ui)])


def get_session():
    with Session(get_engine()) as session:
        yield session


def ctx(request: Request, session: Session, **extra):
    settings = ensure_settings(session)
    people = session.exec(select(Person).order_by(Person.name)).all()
    payload = {
        "request": request,
        "settings": settings,
        "nav_people": people,
        "kind_labels": KIND_DA,
        "cadence_labels": CADENCE_DA,
        "charge_labels": CHARGE_RULE_DA,
        "months": MONTHS_DA,
        "effective_api_key": current_api_key(),
        "api_key_from_env": bool(env_settings.api_key),
    }
    payload.update(extra)
    return payload


def render(request: Request, session: Session, template: str, **extra):
    return templates.TemplateResponse(request, template, ctx(request, session, **extra))


@router.get("/")
def overblik(request: Request, person_id: Optional[int] = None, session: Session = Depends(get_session)):
    plan = build_plan(session, person_id=person_id)
    selected = session.get(Person, person_id) if person_id else None
    return render(request, session, "overblik.html", plan=plan, selected_person=selected)


@router.get("/poster")
def poster(request: Request, kind: Optional[str] = None, session: Session = Depends(get_session)):
    items = session.exec(select(RecurringItem).order_by(RecurringItem.kind, RecurringItem.name)).all()
    if kind:
        items = [i for i in items if i.kind == kind]
    people = session.exec(select(Person)).all()
    accounts = session.exec(select(Account)).all()
    return render(
        request,
        session,
        "poster.html",
        items=items,
        filter_kind=kind,
        people={p.id: p for p in people},
        accounts={a.id: a for a in accounts},
    )


@router.get("/poster/ny")
def ny_post(request: Request, kind: str = "expense", session: Session = Depends(get_session)):
    people = session.exec(select(Person).order_by(Person.name)).all()
    accounts = session.exec(select(Account).order_by(Account.name)).all()
    return render(
        request,
        session,
        "post_form.html",
        item=None,
        default_kind=kind,
        people=people,
        accounts=accounts,
        today=date.today().isoformat(),
    )


@router.get("/poster/{item_id}")
def rediger_post(request: Request, item_id: int, session: Session = Depends(get_session)):
    item = session.get(RecurringItem, item_id)
    if not item:
        raise HTTPException(404)
    people = session.exec(select(Person).order_by(Person.name)).all()
    accounts = session.exec(select(Account).order_by(Account.name)).all()
    return render(
        request,
        session,
        "post_form.html",
        item=item,
        default_kind=item.kind,
        people=people,
        accounts=accounts,
        today=None,
    )


def _item_from_form(
    *,
    kind: str,
    name: str,
    amount: str,
    cadence: str,
    charge_rule: str,
    charge_day: Optional[str],
    anchor_month: Optional[str],
    starts_on: str,
    ends_on: str,
    person_id: str,
    from_account_id: str,
    to_account_id: str,
    category: str,
    notes: str,
    active: Optional[str],
    external_id: str,
) -> ItemIn:
    return ItemIn(
        kind=kind,
        name=name,
        amount_ore=parse_dkk(amount),
        cadence=cadence,
        charge_rule=charge_rule,
        charge_day=int(charge_day) if charge_day else None,
        anchor_month=int(anchor_month) if anchor_month else None,
        starts_on=date.fromisoformat(starts_on),
        ends_on=date.fromisoformat(ends_on) if ends_on else None,
        person_id=int(person_id) if person_id else None,
        from_account_id=int(from_account_id) if from_account_id else None,
        to_account_id=int(to_account_id) if to_account_id else None,
        category=category,
        notes=notes,
        active=bool(active),
        external_id=external_id,
    )


@router.post("/poster")
def gem_ny_post(
    kind: str = Form(),
    name: str = Form(),
    amount: str = Form(),
    cadence: str = Form(),
    charge_rule: str = Form(),
    charge_day: Optional[str] = Form(default=""),
    anchor_month: Optional[str] = Form(default=""),
    starts_on: str = Form(),
    ends_on: str = Form(default=""),
    person_id: str = Form(default=""),
    from_account_id: str = Form(default=""),
    to_account_id: str = Form(default=""),
    category: str = Form(default=""),
    notes: str = Form(default=""),
    active: Optional[str] = Form(default=None),
    external_id: str = Form(default=""),
    session: Session = Depends(get_session),
):
    data = _item_from_form(
        kind=kind,
        name=name,
        amount=amount,
        cadence=cadence,
        charge_rule=charge_rule,
        charge_day=charge_day,
        anchor_month=anchor_month,
        starts_on=starts_on,
        ends_on=ends_on,
        person_id=person_id,
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        category=category,
        notes=notes,
        active=active,
        external_id=external_id,
    )
    upsert_item(session, data)
    return RedirectResponse("/poster", status_code=303)


@router.post("/poster/{item_id}")
def gem_post(
    item_id: int,
    kind: str = Form(),
    name: str = Form(),
    amount: str = Form(),
    cadence: str = Form(),
    charge_rule: str = Form(),
    charge_day: Optional[str] = Form(default=""),
    anchor_month: Optional[str] = Form(default=""),
    starts_on: str = Form(),
    ends_on: str = Form(default=""),
    person_id: str = Form(default=""),
    from_account_id: str = Form(default=""),
    to_account_id: str = Form(default=""),
    category: str = Form(default=""),
    notes: str = Form(default=""),
    active: Optional[str] = Form(default=None),
    external_id: str = Form(default=""),
    session: Session = Depends(get_session),
):
    item = session.get(RecurringItem, item_id)
    if not item:
        raise HTTPException(404)
    data = _item_from_form(
        kind=kind,
        name=name,
        amount=amount,
        cadence=cadence,
        charge_rule=charge_rule,
        charge_day=charge_day,
        anchor_month=anchor_month,
        starts_on=starts_on,
        ends_on=ends_on,
        person_id=person_id,
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        category=category,
        notes=notes,
        active=active,
        external_id=external_id or item.external_id,
    )
    update_item(session, item, data)
    return RedirectResponse("/poster", status_code=303)


@router.post("/poster/{item_id}/slet")
def slet_post(item_id: int, session: Session = Depends(get_session)):
    item = session.get(RecurringItem, item_id)
    if item:
        delete_item(session, item)
    return RedirectResponse("/poster", status_code=303)


@router.get("/personer")
def personer(request: Request, session: Session = Depends(get_session)):
    people = session.exec(select(Person).order_by(Person.name)).all()
    return render(request, session, "personer.html", people=people)


@router.post("/personer")
def gem_person(
    name: str = Form(),
    color: str = Form(default="#0f5c4c"),
    yearly_gross: str = Form(default=""),
    notes: str = Form(default=""),
    session: Session = Depends(get_session),
):
    create_person(
        session,
        PersonIn(name=name, color=color, notes=notes, yearly_gross_ore=parse_dkk(yearly_gross)),
    )
    return RedirectResponse("/personer", status_code=303)


@router.post("/personer/{person_id}/slet")
def slet_person(person_id: int, session: Session = Depends(get_session)):
    person = session.get(Person, person_id)
    if person:
        session.delete(person)
        session.commit()
    return RedirectResponse("/personer", status_code=303)


@router.get("/konti")
def konti(request: Request, session: Session = Depends(get_session)):
    accounts = session.exec(select(Account).order_by(Account.name)).all()
    return render(request, session, "konti.html", accounts=accounts)


@router.post("/konti")
def gem_konto(
    name: str = Form(),
    kind: str = Form(default="checking"),
    opening_balance: str = Form(default="0"),
    session: Session = Depends(get_session),
):
    create_account(
        session,
        AccountIn(name=name, kind=kind, opening_balance_ore=parse_dkk(opening_balance)),
    )
    return RedirectResponse("/konti", status_code=303)


@router.post("/konti/{account_id}/slet")
def slet_konto(account_id: int, session: Session = Depends(get_session)):
    account = session.get(Account, account_id)
    if account:
        session.delete(account)
        session.commit()
    return RedirectResponse("/konti", status_code=303)


@router.get("/skat")
def skat(request: Request, session: Session = Depends(get_session)):
    plan = build_plan(session)
    settings = ensure_settings(session)
    people = session.exec(select(Person).order_by(Person.name)).all()
    incomes = [
        (
            person,
            rough_income_tax(
                person.yearly_gross_ore,
                municipal_tax_pct=settings.municipal_tax_pct,
                church_tax_pct=settings.church_tax_pct,
            ),
        )
        for person in people
        if person.yearly_gross_ore
    ]
    mortgages = session.exec(select(Mortgage)).all()
    return render(request, session, "skat.html", plan=plan, incomes=incomes, mortgages=mortgages)


@router.post("/skat/laan")
def gem_laan(
    name: str = Form(),
    remaining_principal: str = Form(),
    interest_rate_pct: str = Form(),
    contribution_rate_pct: str = Form(default="0"),
    annual_interest_override: str = Form(default=""),
    forskud_interest: str = Form(default="0"),
    property_value: str = Form(default=""),
    mortgage_id: str = Form(default=""),
    session: Session = Depends(get_session),
):
    existing = session.get(Mortgage, int(mortgage_id)) if mortgage_id else None
    upsert_mortgage(
        session,
        MortgageIn(
            name=name,
            remaining_principal_ore=parse_dkk(remaining_principal),
            interest_rate_pct=float(interest_rate_pct.replace(",", ".")),
            contribution_rate_pct=float(contribution_rate_pct.replace(",", ".") or 0),
            annual_interest_override_ore=parse_dkk(annual_interest_override) if annual_interest_override else None,
            forskud_interest_ore=parse_dkk(forskud_interest),
            property_value_ore=parse_dkk(property_value) if property_value else None,
        ),
        existing,
    )
    return RedirectResponse("/skat", status_code=303)


@router.post("/skat/laan/{mortgage_id}/slet")
def slet_laan(mortgage_id: int, session: Session = Depends(get_session)):
    row = session.get(Mortgage, mortgage_id)
    if row:
        session.delete(row)
        session.commit()
    return RedirectResponse("/skat", status_code=303)


@router.get("/indstillinger")
def indstillinger(request: Request, session: Session = Depends(get_session)):
    return render(request, session, "indstillinger.html")


@router.post("/indstillinger")
def gem_indstillinger(
    name: str = Form(),
    municipal_tax_pct: str = Form(),
    church_tax_pct: str = Form(default="0"),
    n8n_webhook_url: str = Form(default=""),
    is_couple: Optional[str] = Form(default=None),
    session: Session = Depends(get_session),
):
    settings = ensure_settings(session)
    settings.name = name.strip() or settings.name
    settings.municipal_tax_pct = float(municipal_tax_pct.replace(",", "."))
    settings.church_tax_pct = float(church_tax_pct.replace(",", ".") or 0)
    settings.n8n_webhook_url = n8n_webhook_url.strip()
    settings.is_couple = bool(is_couple)
    session.add(settings)
    session.commit()
    return RedirectResponse("/indstillinger", status_code=303)


@router.post("/indstillinger/nogle")
def ny_nogle(session: Session = Depends(get_session)):
    rotate_api_key(session)
    return RedirectResponse("/indstillinger", status_code=303)


@router.post("/indstillinger/demo")
def indlaes_demo(session: Session = Depends(get_session)):
    seed_demo(session, force=True)
    return RedirectResponse("/", status_code=303)

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlmodel import Session, select

from app.crud import create_person
from app.database import get_engine
from app.models import Person
from app.schemas import PersonIn
from app.seed import ensure_settings
from app.security import verify_password

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
COLORS = ["#0f5c4c", "#7a3e12", "#1d4e89", "#6b2d5c", "#3f4d2a"]


def get_session():
    with Session(get_engine()) as session:
        yield session


@router.get("/opsaetning")
def opsætning(request: Request, session: Session = Depends(get_session)):
    household = ensure_settings(session)
    if household.onboarded:
        return RedirectResponse("/", status_code=303)
    error = request.session.pop("setup_error", "")
    return templates.TemplateResponse(
        request,
        "opsætning.html",
        {
            "request": request,
            "settings": household,
            "error": error,
        },
    )


@router.post("/opsaetning")
def gem_opsætning(
    request: Request,
    household_name: str = Form(),
    municipal_tax_pct: str = Form(default="25.05"),
    church_tax_pct: str = Form(default="0"),
    is_couple: str | None = Form(default=None),
    admin_name: str = Form(),
    admin_password: str = Form(),
    admin_password2: str = Form(),
    other_name_1: str = Form(default=""),
    other_login_1: str | None = Form(default=None),
    other_password_1: str = Form(default=""),
    other_name_2: str = Form(default=""),
    other_login_2: str | None = Form(default=None),
    other_password_2: str = Form(default=""),
    other_name_3: str = Form(default=""),
    other_login_3: str | None = Form(default=None),
    other_password_3: str = Form(default=""),
    session: Session = Depends(get_session),
):
    household = ensure_settings(session)
    if household.onboarded:
        return RedirectResponse("/", status_code=303)

    def fail(message: str):
        request.session["setup_error"] = message
        return RedirectResponse("/opsaetning", status_code=303)

    admin_name = admin_name.strip()
    if not household_name.strip():
        return fail("Husstanden skal have et navn.")
    if not admin_name:
        return fail("Administratoren skal have et navn.")
    if len(admin_password) < 8:
        return fail("Administratorens kode skal være mindst 8 tegn.")
    if admin_password != admin_password2:
        return fail("De to kodeord til administratoren er ikke ens.")

    extras = [
        (other_name_1, other_login_1, other_password_1),
        (other_name_2, other_login_2, other_password_2),
        (other_name_3, other_login_3, other_password_3),
    ]
    for name, can_login, password in extras:
        name = name.strip()
        if not name:
            continue
        if can_login:
            if len(password) < 8:
                return fail(f"{name} skal have en kode på mindst 8 tegn, fordi personen skal kunne logge ind.")
        elif password:
            return fail(f"{name} har en kode, men er ikke sat til at kunne logge ind. Sæt fluebenet, eller fjern koden.")

    household.name = household_name.strip()
    household.is_couple = bool(is_couple)
    household.municipal_tax_pct = float(municipal_tax_pct.replace(",", ".") or 25.05)
    household.church_tax_pct = float(church_tax_pct.replace(",", ".") or 0)
    household.onboarded = True
    session.add(household)
    session.commit()

    admin = create_person(
        session,
        PersonIn(
            name=admin_name,
            color=COLORS[0],
            role="admin",
            can_login=True,
            password=admin_password,
        ),
    )
    for index, (name, can_login, password) in enumerate(extras, start=1):
        name = name.strip()
        if not name:
            continue
        create_person(
            session,
            PersonIn(
                name=name,
                color=COLORS[index % len(COLORS)],
                role="member",
                can_login=bool(can_login),
                password=password if can_login else None,
            ),
        )
    request.session.clear()
    request.session["person_id"] = admin.id
    return RedirectResponse("/", status_code=303)


@router.get("/login")
def login_page(request: Request, session: Session = Depends(get_session)):
    household = ensure_settings(session)
    if not household.onboarded:
        return RedirectResponse("/opsaetning", status_code=303)
    error = request.session.pop("login_error", "")
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "settings": household, "error": error},
    )


@router.post("/login")
def login(
    request: Request,
    name: str = Form(),
    password: str = Form(),
    session: Session = Depends(get_session),
):
    people = session.exec(select(Person)).all()
    match = next((p for p in people if p.name.lower() == name.strip().lower()), None)
    if (
        not match
        or not match.can_login
        or not verify_password(password, match.password_hash)
    ):
        request.session["login_error"] = "Ukendt navn, eller personen kan ikke logge ind."
        return RedirectResponse("/login", status_code=303)
    request.session.clear()
    request.session["person_id"] = match.id
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

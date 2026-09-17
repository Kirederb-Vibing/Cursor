from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials
from sqlmodel import Session, select
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import get_engine, session_scope
from app.models import Person
from app.seed import ensure_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
basic = HTTPBasic(auto_error=False)

OPEN_PREFIXES = ("/static", "/api/", "/docs", "/redoc", "/openapi.json")
OPEN_PATHS = {"/health", "/login", "/logout", "/opsaetning"}


def current_api_key() -> str:
    if settings.api_key:
        return settings.api_key
    with session_scope() as session:
        row = ensure_settings(session)
        return row.api_key


def require_api_key(
    request: Request,
    key: Optional[str] = Depends(api_key_header),
) -> str:
    provided = key or ""
    auth = request.headers.get("Authorization", "")
    if not provided and auth.lower().startswith("bearer "):
        provided = auth[7:].strip()
    provided = provided or request.query_params.get("api_key", "")
    expected = current_api_key()
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ugyldig API-nøgle")
    return provided


def require_ui(credentials: Optional[HTTPBasicCredentials] = Depends(basic)) -> None:
    password = settings.app_password
    if not password:
        return
    if credentials is None or not secrets.compare_digest(credentials.password, password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login kræves",
            headers={"WWW-Authenticate": "Basic"},
        )


def current_user(request: Request, db: Session) -> Person | None:
    person_id = request.session.get("person_id")
    if not person_id:
        return None
    person = db.get(Person, person_id)
    if not person or not person.can_login:
        request.session.clear()
        return None
    return person


def login_is_required(db: Session) -> bool:
    people = db.exec(select(Person).where(Person.can_login == True)).all()  # noqa: E712
    return any(people)


def is_admin(person: Person | None) -> bool:
    return bool(person and person.role == "admin")


def require_admin(request: Request, db: Session) -> Person | None:
    if not login_is_required(db):
        return current_user(request, db)
    user = current_user(request, db)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Kun administrator")
    return user


class UIGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in OPEN_PATHS or any(path.startswith(prefix) for prefix in OPEN_PREFIXES):
            return await call_next(request)
        try:
            engine = get_engine()
        except RuntimeError:
            return await call_next(request)
        with Session(engine) as db:
            household = ensure_settings(db)
            if not household.onboarded:
                return RedirectResponse("/opsaetning", status_code=303)
            user = current_user(request, db)
            if login_is_required(db) and user is None:
                return RedirectResponse("/login", status_code=303)
        return await call_next(request)

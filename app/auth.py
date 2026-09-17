from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials

from app.config import settings
from app.database import session_scope
from app.seed import ensure_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
basic = HTTPBasic(auto_error=False)


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

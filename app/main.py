from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import select
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.auth import UIGateMiddleware
from app.config import settings
from app.database import init_db, session_scope
from app.models import Person
from app.routers import api, setup, ui
from app.seed import ensure_settings, seed_demo
from app.security import session_secret


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db(settings.data_dir)
    with session_scope() as session:
        household = ensure_settings(session)
        if settings.seed_demo:
            seed_demo(session, force=False)
        elif not household.onboarded and session.exec(select(Person)).first():
            household.onboarded = True
            session.add(household)
            session.commit()
    yield


app = FastAPI(
    title="Fælleskassen",
    description=(
        "Husstandsøkonomi til planlægning, Home Assistant og n8n. "
        "Autentificér med headeren X-API-Key eller Authorization: Bearer."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(UIGateMiddleware)
app.add_middleware(SessionMiddleware, secret_key=session_secret(), same_site="lax")


@app.get("/health")
@app.get("/api/v1/health")
def health():
    return JSONResponse({"ok": True, "service": "faelleskassen", "version": __version__})


app.include_router(setup.router)
app.include_router(api.router)
app.include_router(ui.router)
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")

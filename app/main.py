from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import settings
from app.database import init_db, session_scope
from app.routers import api, ui
from app.seed import ensure_settings, seed_demo


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db(settings.data_dir)
    with session_scope() as session:
        ensure_settings(session)
        if settings.seed_demo:
            seed_demo(session, force=False)
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


@app.get("/health")
@app.get("/api/v1/health")
def health():
    return JSONResponse({"ok": True, "service": "faelleskassen", "version": __version__})


app.include_router(api.router)
app.include_router(ui.router)
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")

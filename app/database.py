from __future__ import annotations

from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = None


def _sqlite_path(data_dir: Path | None = None) -> Path:
    directory = Path(data_dir or settings.data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "faelleskassen.db"


def get_engine():
    global engine
    if engine is None:
        raise RuntimeError("Databasen er ikke initialiseret")
    return engine


def init_db(data_dir: Path | None = None):
    global engine
    path = _sqlite_path(data_dir)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    return engine


def reset_engine():
    global engine
    if engine is not None:
        engine.dispose()
    engine = None


def session_scope() -> Session:
    return Session(get_engine())

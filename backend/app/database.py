"""Configuracion de SQLAlchemy 2.x: engine, sesion y base declarativa."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

connect_args = {}
if settings.db_url.startswith("sqlite"):
    # Necesario para SQLite + FastAPI (multiples hilos comparten la conexion)
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.db_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos ORM."""


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: entrega una sesion de BD y la cierra al finalizar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

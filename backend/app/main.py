"""Punto de entrada de la aplicacion FastAPI: SIREFO Web (backend)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import hash_password
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import User
from app.routers import auth, config, consultas, remisiones, solicitudes, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea las tablas (si no existen) y siembra el usuario admin al arrancar."""
    Base.metadata.create_all(bind=engine)
    _seed_admin()
    yield


app = FastAPI(
    title="SIREFO Web - API",
    description="Backend REST para el consumo del servicio SOAP SIREFO de ASFI "
    "(Alcaldia de Warnes).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(config.router)
app.include_router(solicitudes.router)
app.include_router(remisiones.router)
app.include_router(consultas.router)


def _seed_admin() -> None:
    """Crea el usuario administrador semilla si no existe todavia."""
    settings = get_settings()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == "admin").first() is None:
            db.add(
                User(
                    username="admin",
                    full_name="Administrador",
                    hashed_password=hash_password(settings.admin_password),
                    role="admin",
                    is_active=True,
                )
            )
            db.commit()
    finally:
        db.close()


@app.get("/api/health", tags=["health"])
def health() -> dict:
    """Endpoint simple de salud del servicio."""
    return {"status": "ok"}

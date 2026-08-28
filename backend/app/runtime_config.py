"""Configuracion efectiva del gateway SIREFO: entorno (`.env`) + overrides en BD.

`AppConfig` (fila unica, id=1) permite gestionar desde el panel de administracion
los mismos parametros que hoy solo viven en `backend/.env`. Cualquier columna no
nula/no vacia de esa fila tiene prioridad sobre el valor de entorno equivalente.
Sin fila `AppConfig`, el comportamiento es identico al de hoy (solo entorno).
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AppConfig

CAMPOS = ("modo", "wsdl_url", "asfi_usuario", "asfi_clave", "entidad", "hash_encoding", "tls_verify")


@dataclass(frozen=True)
class EffectiveConfig:
    """Configuracion resultante de fusionar `Settings` (entorno) y `AppConfig` (BD)."""

    mode: str
    wsdl_url: str
    asfi_usuario: str
    asfi_clave: str
    entidad: str
    hash_encoding: str
    tls_verify: bool


def _get_row(db: Session) -> AppConfig | None:
    return db.get(AppConfig, 1)


def _override(env_value, db_value):
    """El valor de BD gana solo si esta definido (no None, no cadena vacia)."""
    if db_value is None or db_value == "":
        return env_value
    return db_value


def get_effective_config(db: Session) -> EffectiveConfig:
    """Fusiona `Settings` (entorno) con la fila `AppConfig` (BD), si existe."""
    settings = get_settings()
    row = _get_row(db)

    return EffectiveConfig(
        mode=_override(settings.mode, row.modo if row else None),
        wsdl_url=_override(settings.wsdl_url, row.wsdl_url if row else None),
        asfi_usuario=_override(settings.asfi_usuario, row.asfi_usuario if row else None),
        asfi_clave=_override(settings.asfi_clave, row.asfi_clave if row else None),
        entidad=_override(settings.entidad, row.entidad if row else None),
        hash_encoding=_override(settings.hash_encoding, row.hash_encoding if row else None),
        tls_verify=settings.tls_verify if (row is None or row.tls_verify is None) else row.tls_verify,
    )


def get_config_sources(db: Session) -> dict[str, str]:
    """Indica, por campo, si el valor efectivo proviene de `env` o de `db`."""
    row = _get_row(db)
    if row is None:
        return {campo: "env" for campo in CAMPOS}

    def _fuente_texto(valor):
        return "env" if (valor is None or valor == "") else "db"

    return {
        "modo": _fuente_texto(row.modo),
        "wsdl_url": _fuente_texto(row.wsdl_url),
        "asfi_usuario": _fuente_texto(row.asfi_usuario),
        "asfi_clave": _fuente_texto(row.asfi_clave),
        "entidad": _fuente_texto(row.entidad),
        "hash_encoding": _fuente_texto(row.hash_encoding),
        "tls_verify": "env" if row.tls_verify is None else "db",
    }

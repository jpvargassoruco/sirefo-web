"""Configuracion de la conexion SIREFO editable desde el panel (solo admin).

Permite gestionar desde la UI los mismos parametros que hoy solo viven en
`backend/.env`: se guardan en la fila unica (`id=1`) de `AppConfig` y
sobreescriben el valor de entorno correspondiente cuando estan definidos (ver
`app/runtime_config.py`). La clave ASFI nunca se devuelve al cliente; solo se
informa si esta definida (`asfi_clave_definida`).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import AppConfig
from app.runtime_config import get_config_sources, get_effective_config
from app.schemas import ConfigOut, ConfigSourcesOut, ConfigUpdate
from app.sirefo.gateway import get_gateway

router = APIRouter(prefix="/api/config", tags=["config"], dependencies=[Depends(require_admin)])

MODOS_VALIDOS = ("mock", "soap")
HASH_ENCODINGS_VALIDOS = ("hex", "HEX", "base64")


def _obtener_fila(db: Session) -> AppConfig | None:
    return db.get(AppConfig, 1)


def _armar_salida(db: Session) -> ConfigOut:
    efectiva = get_effective_config(db)
    fuentes = get_config_sources(db)
    return ConfigOut(
        modo=efectiva.mode,
        wsdl_url=efectiva.wsdl_url,
        asfi_usuario=efectiva.asfi_usuario,
        entidad=efectiva.entidad,
        hash_encoding=efectiva.hash_encoding,
        tls_verify=efectiva.tls_verify,
        asfi_clave_definida=bool(efectiva.asfi_clave),
        fuente=ConfigSourcesOut(**fuentes),
    )


@router.get("", response_model=ConfigOut)
def obtener_config(db: Session = Depends(get_db)) -> ConfigOut:
    """Configuracion efectiva actual (entorno + overrides de BD); nunca expone la clave."""
    return _armar_salida(db)


@router.put("", response_model=ConfigOut)
def actualizar_config(datos: ConfigUpdate, db: Session = Depends(get_db)) -> ConfigOut:
    """Actualiza los overrides de configuracion en BD (fila unica `id=1`).

    Reglas (ver SPEC seccion 10):
    - Campo ausente del body: no se toca (se mantiene el valor actual, sea de BD o de entorno).
    - Campo enviado como `null` explicito: limpia el override (vuelve a usar el valor de entorno).
    - `asfi_clave` ausente o cadena vacia: se mantiene la clave actual (nunca se borra por
      accidente al reenviar el formulario sin tocar el campo de contrasena).
    """
    campos_enviados = datos.model_fields_set
    fila = _obtener_fila(db)
    if fila is None:
        fila = AppConfig(id=1)
        db.add(fila)

    if "modo" in campos_enviados:
        if datos.modo is not None and datos.modo not in MODOS_VALIDOS:
            raise HTTPException(status_code=400, detail="modo debe ser 'mock' o 'soap'")
        fila.modo = datos.modo

    if "wsdl_url" in campos_enviados:
        fila.wsdl_url = datos.wsdl_url

    if "asfi_usuario" in campos_enviados:
        fila.asfi_usuario = datos.asfi_usuario

    if "asfi_clave" in campos_enviados:
        if datos.asfi_clave is None:
            fila.asfi_clave = None  # limpia el override -> vuelve a usar el de entorno
        elif datos.asfi_clave != "":
            fila.asfi_clave = datos.asfi_clave
        # cadena vacia: se deja fila.asfi_clave sin tocar (se mantiene la actual)

    if "entidad" in campos_enviados:
        fila.entidad = datos.entidad

    if "hash_encoding" in campos_enviados:
        if datos.hash_encoding is not None and datos.hash_encoding not in HASH_ENCODINGS_VALIDOS:
            raise HTTPException(
                status_code=400, detail="hash_encoding debe ser 'hex', 'HEX' o 'base64'"
            )
        fila.hash_encoding = datos.hash_encoding

    if "tls_verify" in campos_enviados:
        fila.tls_verify = datos.tls_verify

    db.commit()

    # La configuracion efectiva pudo haber cambiado: se limpia la cache de gateways
    # para no seguir sirviendo una instancia construida con valores viejos.
    get_gateway.cache_clear()

    return _armar_salida(db)

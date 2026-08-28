"""Endpoints de consulta al gateway SIREFO y de auditoria."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.audit import registrar_log
from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import EnvioLog, User
from app.runtime_config import get_effective_config
from app.schemas import (
    EnvioLogListOut,
    EnvioLogOut,
    EntidadVigenteOut,
    EstadoEnvioOut,
    MaxIdSolicitudOut,
    PingOut,
)
from app.sirefo.gateway import SirefoFault, get_gateway

router = APIRouter(tags=["consultas"])


@router.get("/api/sirefo/ping", response_model=PingOut)
def ping(
    texto: str = "hola", db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> PingOut:
    """Prueba de vida contra el servicio SIREFO (proxy a Ping)."""
    gateway = get_gateway(get_effective_config(db))
    try:
        respuesta = gateway.ping(texto)
    except SirefoFault as exc:
        raise HTTPException(
            status_code=502, detail=f"SIREFO: {exc.mensaje} ({exc.tipo_excepcion})"
        ) from exc
    return PingOut(respuesta=respuesta)


@router.get("/api/sirefo/entidades", response_model=list[EntidadVigenteOut])
def entidades_vigentes(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[EntidadVigenteOut]:
    """Lista de entidades financieras vigentes (para combos del frontend)."""
    gateway = get_gateway(get_effective_config(db))
    try:
        entidades = gateway.consulta_entidad_vigente()
    except SirefoFault as exc:
        raise HTTPException(
            status_code=502, detail=f"SIREFO: {exc.mensaje} ({exc.tipo_excepcion})"
        ) from exc
    return [
        EntidadVigenteOut(
            codigo_envio=e.get("CodigoEnvio", ""),
            descripcion=e.get("Descripcion", ""),
            codigo_tipo_entidad=e.get("CodigoTipoEntidad", ""),
            descripcion_tipo_entidad=e.get("DescripcionTipoEntidad", ""),
            estado=e.get("Estado", ""),
        )
        for e in entidades
    ]


@router.get("/api/sirefo/max-id-solicitud", response_model=MaxIdSolicitudOut)
def max_id_solicitud(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MaxIdSolicitudOut:
    """Maximo IdSolicitud registrado en ASFI para la entidad (ConsultaCabecera)."""
    gateway = get_gateway(get_effective_config(db))
    try:
        ultimo = gateway.consulta_cabecera()
    except SirefoFault as exc:
        raise HTTPException(
            status_code=502, detail=f"SIREFO: {exc.mensaje} ({exc.tipo_excepcion})"
        ) from exc
    return MaxIdSolicitudOut(ultimo_id=ultimo)


@router.get("/api/consultas/lista-estado", response_model=list[EstadoEnvioOut])
def lista_estado(
    fecha: str = Query(..., description="Fecha en formato YYYYMMDDHHMISS"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EstadoEnvioOut]:
    """Lista de estados de envio para una fecha dada (ConsultarListaEstadoEnvio)."""
    gateway = get_gateway(get_effective_config(db))
    try:
        estados = gateway.consultar_lista_estado_envio(fecha)
    except SirefoFault as exc:
        registrar_log(db, user.username, "ConsultarListaEstadoEnvio", {"fecha": fecha}, str(exc), False)
        raise HTTPException(
            status_code=502, detail=f"SIREFO: {exc.mensaje} ({exc.tipo_excepcion})"
        ) from exc
    registrar_log(db, user.username, "ConsultarListaEstadoEnvio", {"fecha": fecha}, estados, True)
    return [
        EstadoEnvioOut(
            circular=e.get("Circular"),
            error_envio=e.get("ErrorEnvio"),
            estado=e.get("Estado"),
            fecha_circular=e.get("FechaCircular"),
            c_tipo=e.get("cTipo"),
            tipo=e.get("Tipo"),
            c_id_solicitud=e.get("cIDSolicitud"),
        )
        for e in estados
    ]


@router.get("/api/logs", response_model=EnvioLogListOut, dependencies=[Depends(require_admin)])
def listar_logs(page: int = 1, db: Session = Depends(get_db)) -> EnvioLogListOut:
    """Auditoria de operaciones contra ASFI, paginada (solo admin)."""
    page = max(page, 1)
    tam_pagina = 20
    total = db.query(func.count(EnvioLog.id)).scalar() or 0
    items = (
        db.query(EnvioLog)
        .order_by(EnvioLog.ts.desc())
        .offset((page - 1) * tam_pagina)
        .limit(tam_pagina)
        .all()
    )
    return EnvioLogListOut(
        total=total,
        page=page,
        page_size=tam_pagina,
        items=[EnvioLogOut.model_validate(i) for i in items],
    )

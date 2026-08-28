"""Endpoints de solicitudes de retencion (R) y suspension (S) de fondos."""
import base64
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.audit import registrar_log
from app.auth import get_current_user, require_operador
from app.database import get_db
from app.models import Solicitud, SolicitudDetalle, User
from app.runtime_config import EffectiveConfig, get_effective_config
from app.schemas import SolicitudCreate, SolicitudListItem, SolicitudListOut, SolicitudOut
from app.sirefo import hashes
from app.sirefo.gateway import SirefoFault, get_gateway
from app.sirefo.validation import validar_solicitud

router = APIRouter(prefix="/api/solicitudes", tags=["solicitudes"])

TAM_PAGINA = 20


def _fecha_actual() -> str:
    """Fecha/hora actual en formato SIREFO: YYYYMMDDHHMISS."""
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _construir_cabecera(solicitud_datos: SolicitudCreate, id_solicitud: int, adjunto_nombre: str,
                         adjunto_pdf: bytes, fecha_envio: str, usuario_registro: str,
                         config: EffectiveConfig) -> dict:
    """Arma el dict CabeceraSolicitud (PascalCase, SOAP) con sus hashes calculados."""
    cabecera = {
        "AdjuntoNombre": adjunto_nombre,
        "AutoridadCargo": solicitud_datos.autoridad_cargo,
        "AutoridadSolicitante": solicitud_datos.autoridad_solicitante,
        "CodigoSolicitud": solicitud_datos.codigo_solicitud,
        "DetalleCantidad": len(solicitud_datos.detalles),
        "Entidad": config.entidad,
        "FechaEnvio": fecha_envio,
        "Gerencia": solicitud_datos.gerencia,
        "IdSolicitud": id_solicitud,
        "TipoProceso": solicitud_datos.tipo_proceso,
        "Usuario": usuario_registro,
    }
    cabecera["HashDatos"] = hashes.hash_cabecera_solicitud(cabecera, config.hash_encoding)
    cabecera["HashImagen"] = hashes.hash_imagen(adjunto_pdf, config.hash_encoding)
    cabecera["Adjunto"] = base64.b64encode(adjunto_pdf).decode("ascii")
    return cabecera


def _construir_detalles(solicitud_datos: SolicitudCreate, config: EffectiveConfig) -> list[dict]:
    """Arma la lista ItemSolicitud (PascalCase, SOAP) con sus hashes calculados."""
    items = []
    for idx, d in enumerate(solicitud_datos.detalles, start=1):
        item = {
            "ApellidoMaterno": d.apellido_materno,
            "ApellidoPaterno": d.apellido_paterno,
            "AutoConclusion": d.auto_conclusion,
            "DocumentoIdentidadComplemento": d.documento_complemento,
            "DocumentoIdentidadExtension": d.documento_extension,
            "DocumentoIdentidadNumero": d.documento_numero,
            "DocumentoIdentidadTipo": d.documento_tipo,
            "DocumentoRespaldo": d.documento_respaldo,
            "Item": idx,
            "MontoRetencionBs": d.monto_bs,
            "MontoRetencionUFV": d.monto_ufv,
            "Nombres": d.nombres,
            "RazonSocial": d.razon_social,
            "TipoRespaldo": d.tipo_respaldo,
        }
        item["HashDetalle"] = hashes.hash_detalle_solicitud(item, config.hash_encoding)
        items.append(item)
    return items


def _parsear_datos(data: str) -> SolicitudCreate:
    """Parsea y valida el campo `data` (JSON) del multipart."""
    try:
        bruto = json.loads(data)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="El campo 'data' no es un JSON valido") from exc
    try:
        return SolicitudCreate.model_validate(bruto)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _guardar_detalles(db: Session, solicitud: Solicitud, detalles_in) -> None:
    for idx, d in enumerate(detalles_in, start=1):
        db.add(
            SolicitudDetalle(
                solicitud_id=solicitud.id,
                item=idx,
                tipo_persona=d.tipo_persona,
                nombres=d.nombres,
                apellido_paterno=d.apellido_paterno,
                apellido_materno=d.apellido_materno,
                razon_social=d.razon_social,
                documento_tipo=d.documento_tipo,
                documento_numero=d.documento_numero,
                documento_complemento=d.documento_complemento,
                documento_extension=d.documento_extension,
                documento_respaldo=d.documento_respaldo,
                tipo_respaldo=d.tipo_respaldo,
                monto_bs=d.monto_bs,
                monto_ufv=d.monto_ufv,
                auto_conclusion=d.auto_conclusion,
            )
        )


@router.post("", response_model=SolicitudOut, status_code=201)
async def crear_solicitud(
    data: str = Form(...),
    adjunto: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_operador),
) -> SolicitudOut:
    """Crea y envia a ASFI una solicitud de retencion (R) o suspension (S)."""
    solicitud_datos = _parsear_datos(data)
    pdf_bytes = await adjunto.read()

    # Reglas de negocio (SPEC seccion 3) antes de tocar el gateway.
    detalles_dict = [d.model_dump() for d in solicitud_datos.detalles]
    try:
        validar_solicitud(solicitud_datos.tipo_proceso, detalles_dict, pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # No se permite reutilizar codigo_solicitud (salvo reenvio, que usa otro endpoint).
    existente = (
        db.query(Solicitud).filter(Solicitud.codigo_solicitud == solicitud_datos.codigo_solicitud).first()
    )
    if existente is not None:
        raise HTTPException(
            status_code=400,
            detail="El codigo_solicitud (cite) ya fue utilizado; use reenviar si el envio anterior fallo",
        )

    config = get_effective_config(db)
    gateway = get_gateway(config)
    try:
        ultimo_asfi = gateway.consulta_cabecera()
    except SirefoFault as exc:
        raise HTTPException(
            status_code=502, detail=f"SIREFO: {exc.mensaje} ({exc.tipo_excepcion})"
        ) from exc
    ultimo_local = db.query(func.max(Solicitud.id_solicitud)).scalar() or 0
    id_solicitud = max(ultimo_local, ultimo_asfi) + 1

    fecha_envio = _fecha_actual()
    usuario_registro = user.full_name or user.username
    cabecera = _construir_cabecera(
        solicitud_datos, id_solicitud, adjunto.filename or "adjunto.pdf", pdf_bytes, fecha_envio,
        usuario_registro, config,
    )
    detalles_soap = _construir_detalles(solicitud_datos, config)

    try:
        respuesta = gateway.remitir_solicitud(cabecera, detalles_soap)
    except SirefoFault as exc:
        registrar_log(db, user.username, "RemitirSolicitud", cabecera, str(exc), False)
        raise HTTPException(
            status_code=502, detail=f"SIREFO: {exc.mensaje} ({exc.tipo_excepcion})"
        ) from exc

    solicitud = Solicitud(
        id_solicitud=id_solicitud,
        codigo_solicitud=solicitud_datos.codigo_solicitud,
        tipo_proceso=solicitud_datos.tipo_proceso,
        autoridad_solicitante=solicitud_datos.autoridad_solicitante,
        autoridad_cargo=solicitud_datos.autoridad_cargo,
        gerencia=solicitud_datos.gerencia,
        usuario_registro=usuario_registro,
        adjunto_nombre=adjunto.filename or "adjunto.pdf",
        adjunto_pdf=pdf_bytes,
        fecha_envio=fecha_envio,
        estado_local="enviada" if respuesta.get("Respuesta") == 0 else "error_envio",
        respuesta_codigo=respuesta.get("Respuesta"),
        respuesta_detalle=respuesta.get("Detalle"),
        confirmacion=respuesta.get("Confirmacion"),
        numero_sirefo=respuesta.get("NumeroSIREFO"),
        created_by=user.id,
    )
    db.add(solicitud)
    db.flush()
    _guardar_detalles(db, solicitud, solicitud_datos.detalles)
    db.commit()
    db.refresh(solicitud)

    registrar_log(db, user.username, "RemitirSolicitud", cabecera, respuesta, respuesta.get("Respuesta") == 0)
    return SolicitudOut.model_validate(solicitud)


@router.get("", response_model=SolicitudListOut)
def listar_solicitudes(
    estado: str | None = None,
    tipo: str | None = None,
    q: str | None = None,
    page: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SolicitudListOut:
    """Lista paginada de solicitudes, sin el binario del PDF."""
    query = db.query(Solicitud)
    if estado:
        query = query.filter(Solicitud.estado_local == estado)
    if tipo:
        query = query.filter(Solicitud.tipo_proceso == tipo)
    if q:
        patron = f"%{q}%"
        query = query.filter(
            (Solicitud.codigo_solicitud.ilike(patron))
            | (Solicitud.autoridad_solicitante.ilike(patron))
        )
    page = max(page, 1)
    total = query.count()
    items = (
        query.order_by(Solicitud.id.desc()).offset((page - 1) * TAM_PAGINA).limit(TAM_PAGINA).all()
    )
    return SolicitudListOut(
        total=total,
        page=page,
        page_size=TAM_PAGINA,
        items=[SolicitudListItem.model_validate(i) for i in items],
    )


def _obtener_solicitud(db: Session, solicitud_id: int) -> Solicitud:
    solicitud = db.get(Solicitud, solicitud_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return solicitud


@router.get("/{solicitud_id}", response_model=SolicitudOut)
def obtener_solicitud(
    solicitud_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SolicitudOut:
    """Detalle completo de una solicitud (con sus items, sin el binario)."""
    return SolicitudOut.model_validate(_obtener_solicitud(db, solicitud_id))


@router.get("/{solicitud_id}/adjunto")
def descargar_adjunto(
    solicitud_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    """Descarga el PDF adjunto de la solicitud."""
    solicitud = _obtener_solicitud(db, solicitud_id)
    return Response(
        content=solicitud.adjunto_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{solicitud.adjunto_nombre}"'},
    )


@router.post("/{solicitud_id}/reenviar", response_model=SolicitudOut)
def reenviar_solicitud(
    solicitud_id: int, db: Session = Depends(get_db), user: User = Depends(require_operador)
) -> SolicitudOut:
    """Reintenta el envio a ASFI de una solicitud que quedo en error_envio."""
    solicitud = _obtener_solicitud(db, solicitud_id)
    if solicitud.estado_local != "error_envio":
        raise HTTPException(
            status_code=400, detail="Solo se puede reenviar una solicitud en estado error_envio"
        )

    fecha_envio = _fecha_actual()
    usuario_registro = solicitud.usuario_registro
    config = get_effective_config(db)
    detalles_soap = []
    for d in solicitud.detalles:
        item = {
            "ApellidoMaterno": d.apellido_materno,
            "ApellidoPaterno": d.apellido_paterno,
            "AutoConclusion": d.auto_conclusion,
            "DocumentoIdentidadComplemento": d.documento_complemento,
            "DocumentoIdentidadExtension": d.documento_extension,
            "DocumentoIdentidadNumero": d.documento_numero,
            "DocumentoIdentidadTipo": d.documento_tipo,
            "DocumentoRespaldo": d.documento_respaldo,
            "Item": d.item,
            "MontoRetencionBs": d.monto_bs,
            "MontoRetencionUFV": d.monto_ufv,
            "Nombres": d.nombres,
            "RazonSocial": d.razon_social,
            "TipoRespaldo": d.tipo_respaldo,
        }
        item["HashDetalle"] = hashes.hash_detalle_solicitud(item, config.hash_encoding)
        detalles_soap.append(item)

    cabecera = {
        "AdjuntoNombre": solicitud.adjunto_nombre,
        "AutoridadCargo": solicitud.autoridad_cargo,
        "AutoridadSolicitante": solicitud.autoridad_solicitante,
        "CodigoSolicitud": solicitud.codigo_solicitud,
        "DetalleCantidad": len(detalles_soap),
        "Entidad": config.entidad,
        "FechaEnvio": fecha_envio,
        "Gerencia": solicitud.gerencia,
        "IdSolicitud": solicitud.id_solicitud,
        "TipoProceso": solicitud.tipo_proceso,
        "Usuario": usuario_registro,
    }
    cabecera["HashDatos"] = hashes.hash_cabecera_solicitud(cabecera, config.hash_encoding)
    cabecera["HashImagen"] = hashes.hash_imagen(solicitud.adjunto_pdf, config.hash_encoding)
    cabecera["Adjunto"] = base64.b64encode(solicitud.adjunto_pdf).decode("ascii")

    gateway = get_gateway(config)
    try:
        respuesta = gateway.remitir_solicitud(cabecera, detalles_soap)
    except SirefoFault as exc:
        registrar_log(db, user.username, "RemitirSolicitud(reenvio)", cabecera, str(exc), False)
        raise HTTPException(
            status_code=502, detail=f"SIREFO: {exc.mensaje} ({exc.tipo_excepcion})"
        ) from exc

    solicitud.fecha_envio = fecha_envio
    solicitud.estado_local = "enviada" if respuesta.get("Respuesta") == 0 else "error_envio"
    solicitud.respuesta_codigo = respuesta.get("Respuesta")
    solicitud.respuesta_detalle = respuesta.get("Detalle")
    solicitud.confirmacion = respuesta.get("Confirmacion")
    if respuesta.get("NumeroSIREFO"):
        solicitud.numero_sirefo = respuesta.get("NumeroSIREFO")
    db.commit()
    db.refresh(solicitud)

    registrar_log(
        db, user.username, "RemitirSolicitud(reenvio)", cabecera, respuesta, respuesta.get("Respuesta") == 0
    )
    return SolicitudOut.model_validate(solicitud)


@router.post("/{solicitud_id}/consultar-estado", response_model=SolicitudOut)
def consultar_estado(
    solicitud_id: int, db: Session = Depends(get_db), user: User = Depends(require_operador)
) -> SolicitudOut:
    """Consulta en ASFI el estado de una solicitud ya enviada (ConsultarEstadoEnvio)."""
    solicitud = _obtener_solicitud(db, solicitud_id)
    if solicitud.estado_local != "enviada":
        raise HTTPException(
            status_code=400, detail="Solo se puede consultar el estado de una solicitud enviada"
        )
    tipo = 1 if solicitud.tipo_proceso == "R" else 2
    gateway = get_gateway(get_effective_config(db))
    try:
        estado = gateway.consultar_estado_envio(solicitud.id_solicitud, tipo)
    except SirefoFault as exc:
        registrar_log(db, user.username, "ConsultarEstadoEnvio", {"id_solicitud": solicitud.id_solicitud}, str(exc), False)
        raise HTTPException(
            status_code=502, detail=f"SIREFO: {exc.mensaje} ({exc.tipo_excepcion})"
        ) from exc

    solicitud.estado_asfi = estado.get("Estado")
    solicitud.circular = estado.get("Circular")
    solicitud.fecha_circular = estado.get("FechaCircular")
    solicitud.error_envio_asfi = estado.get("ErrorEnvio")
    db.commit()
    db.refresh(solicitud)

    registrar_log(db, user.username, "ConsultarEstadoEnvio", {"id_solicitud": solicitud.id_solicitud}, estado, True)
    return SolicitudOut.model_validate(solicitud)

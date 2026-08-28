"""Endpoints de remision de fondos previamente retenidos."""
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
from app.models import Remision, RemisionDetalle, User
from app.runtime_config import EffectiveConfig, get_effective_config
from app.schemas import RemisionCreate, RemisionListItem, RemisionListOut, RemisionOut
from app.sirefo import hashes
from app.sirefo.gateway import SirefoFault, get_gateway
from app.sirefo.validation import validar_remision

router = APIRouter(prefix="/api/remisiones", tags=["remisiones"])

TAM_PAGINA = 20


def _fecha_actual() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _construir_cabecera(datos: RemisionCreate, id_remision: int, adjunto_nombre: str,
                         adjunto_pdf: bytes, fecha_emision: str, usuario_registro: str,
                         config: EffectiveConfig) -> dict:
    cabecera = {
        "NumeroSIREFO": datos.numero_sirefo,
        "IdRemision": id_remision,
        "IdentificadorRemision": datos.identificador_remision,
        "AutoridadSolicitante": datos.autoridad_solicitante,
        "GerenciaSolicitante": datos.gerencia_solicitante,
        "CargoSolicitante": datos.cargo_solicitante,
        "FechaHoraEmision": fecha_emision,
        "DetalleCantidad": len(datos.detalles),
        "Entidad": config.entidad,
        "AdjuntoNombre": adjunto_nombre,
        "Usuario": usuario_registro,
    }
    cabecera["HashDatos"] = hashes.hash_cabecera_remision(cabecera, config.hash_encoding)
    cabecera["HashImagen"] = hashes.hash_imagen(adjunto_pdf, config.hash_encoding)
    cabecera["Adjunto"] = base64.b64encode(adjunto_pdf).decode("ascii")
    return cabecera


def _construir_detalles(datos: RemisionCreate, usuario_registro: str, config: EffectiveConfig) -> list[dict]:
    items = []
    for idx, d in enumerate(datos.detalles, start=1):
        item = {
            "Item": idx,
            "ApellidoPaterno": d.apellido_paterno,
            "ApellidoMaterno": d.apellido_materno,
            "Nombres": d.nombres,
            "RazonSocial": d.razon_social,
            "NumeroDocumento": d.numero_documento,
            "DocumentoComplemento": d.documento_complemento,
            "ExtensionDocumento": d.extension_documento,
            "TipoDocumento": d.tipo_documento,
            "DocumentoRespaldo": d.documento_respaldo,
            "TipoRespaldo": d.tipo_respaldo,
            "MontoRemision": d.monto_remision,
            "NumeroCuenta": d.numero_cuenta,
            "CuentaMoneda": d.cuenta_moneda,
            "CodigoEnvio": d.codigo_envio,
            # Entidad y Usuario participan en el hash del item aunque conceptualmente
            # son datos de cabecera (asi lo exige el documento ASFI).
            "Entidad": config.entidad,
            "Usuario": usuario_registro,
        }
        item["HashDetalle"] = hashes.hash_detalle_remision(item, config.hash_encoding)
        items.append(item)
    return items


def _parsear_datos(data: str) -> RemisionCreate:
    try:
        bruto = json.loads(data)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="El campo 'data' no es un JSON valido") from exc
    try:
        return RemisionCreate.model_validate(bruto)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _guardar_detalles(db: Session, remision: Remision, detalles_in) -> None:
    for idx, d in enumerate(detalles_in, start=1):
        db.add(
            RemisionDetalle(
                remision_id=remision.id,
                item=idx,
                tipo_persona=d.tipo_persona,
                nombres=d.nombres,
                apellido_paterno=d.apellido_paterno,
                apellido_materno=d.apellido_materno,
                razon_social=d.razon_social,
                numero_documento=d.numero_documento,
                documento_complemento=d.documento_complemento,
                extension_documento=d.extension_documento,
                tipo_documento=d.tipo_documento,
                documento_respaldo=d.documento_respaldo,
                tipo_respaldo=d.tipo_respaldo,
                monto_remision=d.monto_remision,
                numero_cuenta=d.numero_cuenta,
                cuenta_moneda=d.cuenta_moneda,
                codigo_envio=d.codigo_envio,
            )
        )


@router.post("", response_model=RemisionOut, status_code=201)
async def crear_remision(
    data: str = Form(...),
    adjunto: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_operador),
) -> RemisionOut:
    """Crea y envia a ASFI una remision de fondos retenidos previamente."""
    datos = _parsear_datos(data)
    pdf_bytes = await adjunto.read()

    detalles_dict = [d.model_dump() for d in datos.detalles]
    try:
        validar_remision(detalles_dict, pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ultimo_local = db.query(func.max(Remision.id_remision)).scalar() or 0
    id_remision = ultimo_local + 1

    fecha_emision = _fecha_actual()
    usuario_registro = user.full_name or user.username
    config = get_effective_config(db)
    cabecera = _construir_cabecera(
        datos, id_remision, adjunto.filename or "adjunto.pdf", pdf_bytes, fecha_emision, usuario_registro,
        config,
    )
    detalles_soap = _construir_detalles(datos, usuario_registro, config)

    gateway = get_gateway(config)
    try:
        respuesta = gateway.remitir_remision(cabecera, detalles_soap)
    except SirefoFault as exc:
        registrar_log(db, user.username, "RemitirRemisionFondos", cabecera, str(exc), False)
        raise HTTPException(
            status_code=502, detail=f"SIREFO: {exc.mensaje} ({exc.tipo_excepcion})"
        ) from exc

    remision = Remision(
        id_remision=id_remision,
        numero_sirefo=datos.numero_sirefo,
        identificador_remision=datos.identificador_remision,
        autoridad_solicitante=datos.autoridad_solicitante,
        gerencia_solicitante=datos.gerencia_solicitante,
        cargo_solicitante=datos.cargo_solicitante,
        fecha_hora_emision=fecha_emision,
        adjunto_nombre=adjunto.filename or "adjunto.pdf",
        adjunto_pdf=pdf_bytes,
        usuario_registro=usuario_registro,
        estado_local="enviada" if respuesta.get("Respuesta") == 0 else "error_envio",
        respuesta_codigo=respuesta.get("Respuesta"),
        respuesta_detalle=respuesta.get("Detalle"),
        confirmacion=respuesta.get("Confirmacion"),
        created_by=user.id,
    )
    db.add(remision)
    db.flush()
    _guardar_detalles(db, remision, datos.detalles)
    db.commit()
    db.refresh(remision)

    registrar_log(db, user.username, "RemitirRemisionFondos", cabecera, respuesta, respuesta.get("Respuesta") == 0)
    return RemisionOut.model_validate(remision)


@router.get("", response_model=RemisionListOut)
def listar_remisiones(
    estado: str | None = None,
    q: str | None = None,
    page: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RemisionListOut:
    """Lista paginada de remisiones, sin el binario del PDF."""
    query = db.query(Remision)
    if estado:
        query = query.filter(Remision.estado_local == estado)
    if q:
        patron = f"%{q}%"
        query = query.filter(
            (Remision.identificador_remision.ilike(patron))
            | (Remision.numero_sirefo.ilike(patron))
        )
    page = max(page, 1)
    total = query.count()
    items = (
        query.order_by(Remision.id.desc()).offset((page - 1) * TAM_PAGINA).limit(TAM_PAGINA).all()
    )
    return RemisionListOut(
        total=total,
        page=page,
        page_size=TAM_PAGINA,
        items=[RemisionListItem.model_validate(i) for i in items],
    )


def _obtener_remision(db: Session, remision_id: int) -> Remision:
    remision = db.get(Remision, remision_id)
    if remision is None:
        raise HTTPException(status_code=404, detail="Remision no encontrada")
    return remision


@router.get("/{remision_id}", response_model=RemisionOut)
def obtener_remision(
    remision_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> RemisionOut:
    """Detalle completo de una remision (con sus items, sin el binario)."""
    return RemisionOut.model_validate(_obtener_remision(db, remision_id))


@router.get("/{remision_id}/adjunto")
def descargar_adjunto(
    remision_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    """Descarga el PDF adjunto de la remision."""
    remision = _obtener_remision(db, remision_id)
    return Response(
        content=remision.adjunto_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{remision.adjunto_nombre}"'},
    )


@router.post("/{remision_id}/reenviar", response_model=RemisionOut)
def reenviar_remision(
    remision_id: int, db: Session = Depends(get_db), user: User = Depends(require_operador)
) -> RemisionOut:
    """Reintenta el envio a ASFI de una remision que quedo en error_envio."""
    remision = _obtener_remision(db, remision_id)
    if remision.estado_local != "error_envio":
        raise HTTPException(
            status_code=400, detail="Solo se puede reenviar una remision en estado error_envio"
        )

    fecha_emision = _fecha_actual()
    usuario_registro = remision.usuario_registro
    config = get_effective_config(db)
    detalles_soap = []
    for d in remision.detalles:
        item = {
            "Item": d.item,
            "ApellidoPaterno": d.apellido_paterno,
            "ApellidoMaterno": d.apellido_materno,
            "Nombres": d.nombres,
            "RazonSocial": d.razon_social,
            "NumeroDocumento": d.numero_documento,
            "DocumentoComplemento": d.documento_complemento,
            "ExtensionDocumento": d.extension_documento,
            "TipoDocumento": d.tipo_documento,
            "DocumentoRespaldo": d.documento_respaldo,
            "TipoRespaldo": d.tipo_respaldo,
            "MontoRemision": d.monto_remision,
            "NumeroCuenta": d.numero_cuenta,
            "CuentaMoneda": d.cuenta_moneda,
            "CodigoEnvio": d.codigo_envio,
            "Entidad": config.entidad,
            "Usuario": usuario_registro,
        }
        item["HashDetalle"] = hashes.hash_detalle_remision(item, config.hash_encoding)
        detalles_soap.append(item)

    cabecera = {
        "NumeroSIREFO": remision.numero_sirefo,
        "IdRemision": remision.id_remision,
        "IdentificadorRemision": remision.identificador_remision,
        "AutoridadSolicitante": remision.autoridad_solicitante,
        "GerenciaSolicitante": remision.gerencia_solicitante,
        "CargoSolicitante": remision.cargo_solicitante,
        "FechaHoraEmision": fecha_emision,
        "DetalleCantidad": len(detalles_soap),
        "Entidad": config.entidad,
        "AdjuntoNombre": remision.adjunto_nombre,
        "Usuario": usuario_registro,
    }
    cabecera["HashDatos"] = hashes.hash_cabecera_remision(cabecera, config.hash_encoding)
    cabecera["HashImagen"] = hashes.hash_imagen(remision.adjunto_pdf, config.hash_encoding)
    cabecera["Adjunto"] = base64.b64encode(remision.adjunto_pdf).decode("ascii")

    gateway = get_gateway(config)
    try:
        respuesta = gateway.remitir_remision(cabecera, detalles_soap)
    except SirefoFault as exc:
        registrar_log(db, user.username, "RemitirRemisionFondos(reenvio)", cabecera, str(exc), False)
        raise HTTPException(
            status_code=502, detail=f"SIREFO: {exc.mensaje} ({exc.tipo_excepcion})"
        ) from exc

    remision.fecha_hora_emision = fecha_emision
    remision.estado_local = "enviada" if respuesta.get("Respuesta") == 0 else "error_envio"
    remision.respuesta_codigo = respuesta.get("Respuesta")
    remision.respuesta_detalle = respuesta.get("Detalle")
    remision.confirmacion = respuesta.get("Confirmacion")
    db.commit()
    db.refresh(remision)

    registrar_log(
        db, user.username, "RemitirRemisionFondos(reenvio)", cabecera, respuesta, respuesta.get("Respuesta") == 0
    )
    return RemisionOut.model_validate(remision)


@router.post("/{remision_id}/consultar-estado", response_model=RemisionOut)
def consultar_estado(
    remision_id: int, db: Session = Depends(get_db), user: User = Depends(require_operador)
) -> RemisionOut:
    """Consulta en ASFI el estado de una remision ya enviada (ConsultarEstadoEnvio, tipo 4)."""
    remision = _obtener_remision(db, remision_id)
    if remision.estado_local != "enviada":
        raise HTTPException(
            status_code=400, detail="Solo se puede consultar el estado de una remision enviada"
        )
    gateway = get_gateway(get_effective_config(db))
    try:
        estado = gateway.consultar_estado_envio(remision.id_remision, 4)
    except SirefoFault as exc:
        registrar_log(db, user.username, "ConsultarEstadoEnvio", {"id_remision": remision.id_remision}, str(exc), False)
        raise HTTPException(
            status_code=502, detail=f"SIREFO: {exc.mensaje} ({exc.tipo_excepcion})"
        ) from exc

    remision.estado_asfi = estado.get("Estado")
    remision.circular = estado.get("Circular")
    remision.fecha_circular = estado.get("FechaCircular")
    remision.error_envio_asfi = estado.get("ErrorEnvio")
    db.commit()
    db.refresh(remision)

    registrar_log(db, user.username, "ConsultarEstadoEnvio", {"id_remision": remision.id_remision}, estado, True)
    return RemisionOut.model_validate(remision)

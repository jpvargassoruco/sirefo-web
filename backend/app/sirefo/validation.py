"""Reglas de validacion de negocio del documento SIREFO/ASFI (SPEC seccion 3).

Se aplican tanto en el backend (antes de llamar al gateway, para responder 400
con un mensaje claro) como en el mock gateway (para simular el comportamiento
real de ASFI ante datos invalidos). Todas las funciones lanzan `ValueError`
con un mensaje en espanol cuando la regla no se cumple.
"""
import re

EXTENSIONES_VALIDAS = {"CH", "LP", "CB", "OR", "PO", "TJ", "SC", "BE", "PA", "PE"}
TIPOS_DOC_NATURAL = {2, 4, 5}
TIPOS_DOC_JURIDICA = {1, 3}
FECHA_RE = re.compile(r"^\d{14}$")


def validar_persona(detalle: dict) -> None:
    """Regla 1: consistencia entre tipo_persona, documento_tipo, nombres/apellidos/razon_social."""
    tipo_persona = detalle.get("tipo_persona")
    documento_tipo = detalle.get("documento_tipo", detalle.get("tipo_documento"))
    nombres = (detalle.get("nombres") or "").strip()
    apellido_paterno = (detalle.get("apellido_paterno") or "").strip()
    apellido_materno = (detalle.get("apellido_materno") or "").strip()
    razon_social = (detalle.get("razon_social") or "").strip()

    if tipo_persona == "natural":
        if documento_tipo not in TIPOS_DOC_NATURAL:
            raise ValueError(
                "Persona natural: el tipo de documento debe ser 2 (CI), 4 (Pasaporte) o 5 "
                "(CI extranjero)"
            )
        if not nombres or not (apellido_paterno or apellido_materno):
            raise ValueError(
                "Persona natural: se requieren nombres y al menos un apellido"
            )
        if razon_social:
            raise ValueError("Persona natural: la razon social debe ir vacia")
    elif tipo_persona == "juridica":
        if documento_tipo not in TIPOS_DOC_JURIDICA:
            raise ValueError(
                "Persona juridica: el tipo de documento debe ser 1 (NIT) o 3 (RUC)"
            )
        if not razon_social:
            raise ValueError("Persona juridica: se requiere la razon social")
        if nombres or apellido_paterno or apellido_materno:
            raise ValueError("Persona juridica: nombres y apellidos deben ir vacios")
    else:
        raise ValueError("tipo_persona debe ser 'natural' o 'juridica'")


def validar_extension(detalle: dict, contexto: str = "solicitud") -> None:
    """Regla 2: PE solo aplica a documento_tipo 2 y 5; puede ir vacia segun el tipo y el
    contexto (solicitud: tipos 1,2,3,4 pueden ir vacios; remision: tipos 1,3,4)."""
    extension = (
        detalle.get("documento_extension") or detalle.get("extension_documento") or ""
    ).strip()
    documento_tipo = detalle.get("documento_tipo") or detalle.get("tipo_documento")
    tipos_permiten_vacio = {1, 2, 3, 4} if contexto == "solicitud" else {1, 3, 4}

    if not extension:
        if documento_tipo not in tipos_permiten_vacio:
            raise ValueError(
                f"El tipo de documento {documento_tipo} requiere indicar la extension"
            )
        return
    if extension not in EXTENSIONES_VALIDAS:
        raise ValueError(f"Extension de documento invalida: {extension}")
    if extension == "PE" and documento_tipo not in (2, 5):
        raise ValueError("La extension PE solo es valida para los tipos de documento 2 y 5")


def validar_monto(detalle: dict) -> None:
    """Regla 3: monto en Bs o UFV, nunca ambos, nunca ninguno."""
    monto_bs = detalle.get("monto_bs")
    monto_ufv = detalle.get("monto_ufv")
    if monto_bs is not None and monto_ufv is not None:
        raise ValueError("No se puede indicar monto en Bs y en UFV a la vez")
    if monto_bs is None and monto_ufv is None:
        raise ValueError("Se debe indicar el monto en Bs o en UFV")


def validar_fecha(fecha: str, campo: str = "FechaEnvio") -> None:
    """Regla 4: formato YYYYMMDDHHMISS (14 digitos)."""
    if not fecha or not FECHA_RE.match(fecha):
        raise ValueError(f"{campo} debe tener el formato YYYYMMDDHHMISS (14 digitos)")


def validar_pdf(pdf_bytes: bytes) -> None:
    """Regla 5: el adjunto debe ser un PDF valido (magic bytes %PDF)."""
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("El adjunto debe ser un archivo PDF valido")


def validar_detalle_cantidad(detalle_cantidad: int, cantidad_real: int) -> None:
    """Regla 6: DetalleCantidad debe coincidir con el numero real de detalles."""
    if detalle_cantidad != cantidad_real:
        raise ValueError(
            f"DetalleCantidad ({detalle_cantidad}) no coincide con el numero de detalles "
            f"enviados ({cantidad_real})"
        )


def validar_auto_conclusion(tipo_proceso: str, auto_conclusion: str) -> None:
    """Regla 8: AutoConclusion solo aplica a suspensiones (TipoProceso=S)."""
    if tipo_proceso != "S" and (auto_conclusion or "").strip():
        raise ValueError("AutoConclusion solo aplica a solicitudes de suspension (S)")


def validar_solicitud(tipo_proceso: str, detalles: list[dict], pdf_bytes: bytes) -> None:
    """Valida una solicitud de retencion/suspension completa (cabecera + detalles)."""
    if tipo_proceso not in ("R", "S"):
        raise ValueError("tipo_proceso debe ser 'R' (retencion) o 'S' (suspension)")
    if not detalles:
        raise ValueError("La solicitud debe tener al menos un detalle")
    validar_pdf(pdf_bytes)
    for detalle in detalles:
        validar_persona(detalle)
        validar_extension(detalle, contexto="solicitud")
        validar_monto(detalle)
        validar_auto_conclusion(tipo_proceso, detalle.get("auto_conclusion", ""))


def validar_remision(detalles: list[dict], pdf_bytes: bytes) -> None:
    """Valida una remision de fondos completa (cabecera + detalles)."""
    if not detalles:
        raise ValueError("La remision debe tener al menos un detalle")
    validar_pdf(pdf_bytes)
    for detalle in detalles:
        validar_persona(detalle)
        validar_extension(detalle, contexto="remision")
        if detalle.get("monto_remision") is None:
            raise ValueError("Se debe indicar el monto de la remision")
        if detalle.get("cuenta_moneda") not in (1, 2, 3, 4):
            raise ValueError("cuenta_moneda debe ser 1 (BOB), 2 (USD), 3 (BOB c/MV) o 4 (MN a UFV)")

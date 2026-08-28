"""Algoritmos de hash SHA-1 exigidos por el documento SIREFO/ASFI (22/11/2022).

El orden exacto de concatenacion de campos es el que define ASFI para validar la
integridad de los datos enviados; no debe alterarse. Ver docs/SPEC.md seccion 4.
"""
import base64
import hashlib
from typing import Any

from app.config import get_settings


def _s(valor: Any) -> str:
    """Normaliza un valor a texto para la concatenacion del hash.

    None -> cadena vacia. Enteros -> str(n). El resto se usa tal cual (ya se
    espera texto).
    """
    if valor is None:
        return ""
    if isinstance(valor, bool):
        # No deberia ocurrir en los campos de hash, pero se evita True/False literal
        return str(valor)
    return str(valor)


def _monto(valor: Any) -> str:
    """Formatea un monto con 2 decimales, o cadena vacia si es None."""
    if valor is None or valor == "":
        return ""
    return f"{float(valor):.2f}"


def _resolver_encoding(encoding: str | None) -> str:
    """Si no se indica encoding explicito, cae al de `Settings` (entorno)."""
    return encoding if encoding is not None else get_settings().hash_encoding


def _h(texto: str, encoding: str | None = None) -> str:
    """SHA-1 de `texto` codificado en utf-8, en la codificacion indicada.

    `encoding`: "hex" (minusculas, default), "HEX" (mayusculas) o "base64". Si
    no se pasa, se usa `SIREFO_HASH_ENCODING` (entorno) -- asi las llamadas
    existentes (y las pruebas de `test_hashes.py`) siguen funcionando igual.
    En produccion, los routers y el gateway deben pasar el encoding de la
    configuracion efectiva (`app/runtime_config.py`), que puede venir de la BD.
    """
    digest = hashlib.sha1(texto.encode("utf-8")).digest()
    encoding = _resolver_encoding(encoding)
    if encoding == "HEX":
        return digest.hex().upper()
    if encoding == "base64":
        return base64.b64encode(digest).decode("ascii")
    # default: hex minusculas
    return digest.hex()


def hash_cabecera_solicitud(c: dict, encoding: str | None = None) -> str:
    """Hash de la cabecera de una solicitud de retencion/suspension (CabeceraSolicitud)."""
    partes = [
        _s(c.get("AdjuntoNombre")),
        _s(c.get("AutoridadCargo")),
        _s(c.get("AutoridadSolicitante")),
        _s(c.get("CodigoSolicitud")),
        _s(c.get("DetalleCantidad")),
        _s(c.get("Entidad")),
        _s(c.get("FechaEnvio")),
        _s(c.get("Gerencia")),
        _s(c.get("IdSolicitud")),
        _s(c.get("TipoProceso")),
    ]
    return _h("".join(partes), encoding)


def hash_detalle_solicitud(d: dict, encoding: str | None = None) -> str:
    """Hash de un item (ItemSolicitud) de una solicitud de retencion/suspension.

    Nota: el documento ASFI NO incluye MontoRetencionUFV en este hash; solo
    MontoRetencionBs (o vacio si el item usa UFV).
    """
    partes = [
        _s(d.get("ApellidoMaterno")),
        _s(d.get("ApellidoPaterno")),
        _s(d.get("AutoConclusion")),
        _s(d.get("DocumentoIdentidadComplemento")),
        _s(d.get("DocumentoIdentidadExtension")),
        _s(d.get("DocumentoIdentidadNumero")),
        _s(d.get("DocumentoIdentidadTipo")),
        _s(d.get("DocumentoRespaldo")),
        _s(d.get("Item")),
        _monto(d.get("MontoRetencionBs")),
        _s(d.get("Nombres")),
        _s(d.get("RazonSocial")),
        _s(d.get("TipoRespaldo")),
    ]
    return _h("".join(partes), encoding)


def hash_imagen(pdf_bytes: bytes, encoding: str | None = None) -> str:
    """Hash SHA-1 de los bytes crudos del PDF adjunto."""
    digest = hashlib.sha1(pdf_bytes).digest()
    encoding = _resolver_encoding(encoding)
    if encoding == "HEX":
        return digest.hex().upper()
    if encoding == "base64":
        return base64.b64encode(digest).decode("ascii")
    return digest.hex()


def hash_cabecera_remision(r: dict, encoding: str | None = None) -> str:
    """Hash de la cabecera de una remision de fondos (CabeceraRemision)."""
    partes = [
        _s(r.get("NumeroSIREFO")),
        _s(r.get("IdRemision")),
        _s(r.get("IdentificadorRemision")),
        _s(r.get("AutoridadSolicitante")),
        _s(r.get("GerenciaSolicitante")),
        _s(r.get("CargoSolicitante")),
        _s(r.get("FechaHoraEmision")),
        _s(r.get("DetalleCantidad")),
        _s(r.get("Entidad")),
    ]
    return _h("".join(partes), encoding)


def hash_detalle_remision(d: dict, encoding: str | None = None) -> str:
    """Hash de un item (ItemRemision) de una remision de fondos."""
    partes = [
        _s(d.get("Item")),
        _s(d.get("ApellidoPaterno")),
        _s(d.get("ApellidoMaterno")),
        _s(d.get("Nombres")),
        _s(d.get("RazonSocial")),
        _s(d.get("NumeroDocumento")),
        _s(d.get("DocumentoComplemento")),
        _s(d.get("TipoDocumento")),
        _s(d.get("DocumentoRespaldo")),
        _s(d.get("TipoRespaldo")),
        _monto(d.get("MontoRemision")),
        _s(d.get("NumeroCuenta")),
        _s(d.get("CuentaMoneda")),
        _s(d.get("CodigoEnvio")),
        _s(d.get("Entidad")),
        _s(d.get("Usuario")),
    ]
    return _h("".join(partes), encoding)

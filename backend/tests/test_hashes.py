"""Pruebas de los algoritmos de hash SHA-1 exigidos por ASFI (SPEC seccion 4).

Cada hash se recalcula aqui con hashlib directamente (misma concatenacion que
describe el documento) y se compara contra el resultado de `app.sirefo.hashes`.
"""
import hashlib
import os

# Aseguramos SIREFO_HASH_ENCODING=hex (default) para que los vectores sean deterministas.
os.environ.setdefault("SIREFO_HASH_ENCODING", "hex")

from app.sirefo import hashes  # noqa: E402


def test_hash_vacio_hex():
    """Vector fijo del SPEC: SHA-1 de la cadena vacia en hex."""
    assert hashes._h("") == "da39a3ee5e6b4b0d3255bfef95601890afd80709"


def test_hash_cabecera_solicitud():
    cabecera = {
        "AdjuntoNombre": "nota.pdf",
        "AutoridadCargo": "Alcalde",
        "AutoridadSolicitante": "Juan Perez",
        "CodigoSolicitud": "CITE-001/2026",
        "DetalleCantidad": 2,
        "Entidad": "GAMW",
        "FechaEnvio": "20260827120000",
        "Gerencia": "Gerencia Juridica",
        "IdSolicitud": 15,
        "TipoProceso": "R",
    }
    esperado_texto = (
        cabecera["AdjuntoNombre"]
        + cabecera["AutoridadCargo"]
        + cabecera["AutoridadSolicitante"]
        + cabecera["CodigoSolicitud"]
        + str(cabecera["DetalleCantidad"])
        + cabecera["Entidad"]
        + cabecera["FechaEnvio"]
        + cabecera["Gerencia"]
        + str(cabecera["IdSolicitud"])
        + cabecera["TipoProceso"]
    )
    esperado = hashlib.sha1(esperado_texto.encode("utf-8")).hexdigest()
    assert hashes.hash_cabecera_solicitud(cabecera) == esperado


def test_hash_detalle_solicitud_con_monto_bs():
    """La nota del SPEC indica que MontoRetencionUFV NO participa en este hash."""
    detalle = {
        "ApellidoMaterno": "Lopez",
        "ApellidoPaterno": "Garcia",
        "AutoConclusion": "",
        "DocumentoIdentidadComplemento": "1A",
        "DocumentoIdentidadExtension": "SC",
        "DocumentoIdentidadNumero": "1234567",
        "DocumentoIdentidadTipo": 2,
        "DocumentoRespaldo": "Nota 123",
        "Item": 1,
        "MontoRetencionBs": 1500.5,
        "MontoRetencionUFV": None,  # no debe influir en el hash
        "Nombres": "Maria",
        "RazonSocial": "",
        "TipoRespaldo": 1,
    }
    esperado_texto = (
        detalle["ApellidoMaterno"]
        + detalle["ApellidoPaterno"]
        + detalle["AutoConclusion"]
        + detalle["DocumentoIdentidadComplemento"]
        + detalle["DocumentoIdentidadExtension"]
        + detalle["DocumentoIdentidadNumero"]
        + str(detalle["DocumentoIdentidadTipo"])
        + detalle["DocumentoRespaldo"]
        + str(detalle["Item"])
        + f"{detalle['MontoRetencionBs']:.2f}"
        + detalle["Nombres"]
        + detalle["RazonSocial"]
        + str(detalle["TipoRespaldo"])
    )
    esperado = hashlib.sha1(esperado_texto.encode("utf-8")).hexdigest()
    assert hashes.hash_detalle_solicitud(detalle) == esperado

    # Si en su lugar se usa MontoRetencionUFV, el campo de monto en el hash queda vacio.
    detalle_ufv = dict(detalle, MontoRetencionBs=None, MontoRetencionUFV=200.25)
    esperado_texto_ufv = esperado_texto.replace(f"{detalle['MontoRetencionBs']:.2f}", "")
    esperado_ufv = hashlib.sha1(esperado_texto_ufv.encode("utf-8")).hexdigest()
    assert hashes.hash_detalle_solicitud(detalle_ufv) == esperado_ufv


def test_hash_imagen():
    pdf_bytes = b"%PDF-1.4\n%mock-pdf-content\n"
    esperado = hashlib.sha1(pdf_bytes).hexdigest()
    assert hashes.hash_imagen(pdf_bytes) == esperado


def test_hash_cabecera_remision():
    cabecera = {
        "NumeroSIREFO": "SIREFO-000015",
        "IdRemision": 3,
        "IdentificadorRemision": "REM-001",
        "AutoridadSolicitante": "Juan Perez",
        "GerenciaSolicitante": "Gerencia Juridica",
        "CargoSolicitante": "Alcalde",
        "FechaHoraEmision": "20260827120500",
        "DetalleCantidad": 1,
        "Entidad": "GAMW",
    }
    esperado_texto = (
        cabecera["NumeroSIREFO"]
        + str(cabecera["IdRemision"])
        + cabecera["IdentificadorRemision"]
        + cabecera["AutoridadSolicitante"]
        + cabecera["GerenciaSolicitante"]
        + cabecera["CargoSolicitante"]
        + cabecera["FechaHoraEmision"]
        + str(cabecera["DetalleCantidad"])
        + cabecera["Entidad"]
    )
    esperado = hashlib.sha1(esperado_texto.encode("utf-8")).hexdigest()
    assert hashes.hash_cabecera_remision(cabecera) == esperado


def test_hash_detalle_remision():
    detalle = {
        "Item": 1,
        "ApellidoPaterno": "Garcia",
        "ApellidoMaterno": "Lopez",
        "Nombres": "Maria",
        "RazonSocial": "",
        "NumeroDocumento": "1234567",
        "DocumentoComplemento": "1A",
        "TipoDocumento": 2,
        "DocumentoRespaldo": "Nota 123",
        "TipoRespaldo": 1,
        "MontoRemision": 999.9,
        "NumeroCuenta": "1002003",
        "CuentaMoneda": 1,
        "CodigoEnvio": "IBBUN",
        "Entidad": "GAMW",
        "Usuario": "Juan Perez",
    }
    esperado_texto = (
        str(detalle["Item"])
        + detalle["ApellidoPaterno"]
        + detalle["ApellidoMaterno"]
        + detalle["Nombres"]
        + detalle["RazonSocial"]
        + detalle["NumeroDocumento"]
        + detalle["DocumentoComplemento"]
        + str(detalle["TipoDocumento"])
        + detalle["DocumentoRespaldo"]
        + str(detalle["TipoRespaldo"])
        + f"{detalle['MontoRemision']:.2f}"
        + detalle["NumeroCuenta"]
        + str(detalle["CuentaMoneda"])
        + detalle["CodigoEnvio"]
        + detalle["Entidad"]
        + detalle["Usuario"]
    )
    esperado = hashlib.sha1(esperado_texto.encode("utf-8")).hexdigest()
    assert hashes.hash_detalle_remision(detalle) == esperado


def test_hash_encoding_hex_mayuscula():
    """SIREFO_HASH_ENCODING='HEX' produce la salida en mayusculas."""
    from app.config import get_settings

    get_settings.cache_clear()
    os.environ["SIREFO_HASH_ENCODING"] = "HEX"
    try:
        get_settings.cache_clear()
        assert hashes._h("") == "DA39A3EE5E6B4B0D3255BFEF95601890AFD80709"
    finally:
        os.environ["SIREFO_HASH_ENCODING"] = "hex"
        get_settings.cache_clear()


def test_hash_encoding_base64():
    """SIREFO_HASH_ENCODING='base64' codifica el digest en base64."""
    import base64

    from app.config import get_settings

    os.environ["SIREFO_HASH_ENCODING"] = "base64"
    try:
        get_settings.cache_clear()
        digest = hashlib.sha1(b"").digest()
        assert hashes._h("") == base64.b64encode(digest).decode("ascii")
    finally:
        os.environ["SIREFO_HASH_ENCODING"] = "hex"
        get_settings.cache_clear()

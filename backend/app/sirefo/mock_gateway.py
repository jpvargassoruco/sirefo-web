"""Gateway simulado de SIREFO (SIREFO_MODE=mock).

Emula, dentro del mismo proceso, el comportamiento del servicio SOAP real de
ASFI: valida credenciales, reglas de negocio y hashes (recalculandolos, para
ejercer nuestra propia implementacion de `hashes.py`), y mantiene un estado
en memoria (dicts) para responder a las consultas de estado. No usa timers:
un envio exitoso queda "Procesada" de inmediato.
"""
import base64
from datetime import datetime, timezone

from app.runtime_config import EffectiveConfig
from app.sirefo import hashes
from app.sirefo.gateway import SirefoFault, SirefoGateway
from app.sirefo.validation import (
    validar_auto_conclusion,
    validar_detalle_cantidad,
    validar_extension,
    validar_fecha,
    validar_monto,
    validar_persona,
    validar_pdf,
)

ENTIDADES_VIGENTES = [
    {
        "CodigoEnvio": "IBBUN",
        "Descripcion": "Banco Unión S.A.",
        "CodigoTipoEntidad": "IBB",
        "DescripcionTipoEntidad": "Banco Múltiple",
        "Estado": "VIGENTE",
    },
    {
        "CodigoEnvio": "IBBME",
        "Descripcion": "Banco Mercantil Santa Cruz S.A.",
        "CodigoTipoEntidad": "IBB",
        "DescripcionTipoEntidad": "Banco Múltiple",
        "Estado": "VIGENTE",
    },
    {
        "CodigoEnvio": "IBBBI",
        "Descripcion": "Banco BISA S.A.",
        "CodigoTipoEntidad": "IBB",
        "DescripcionTipoEntidad": "Banco Múltiple",
        "Estado": "VIGENTE",
    },
    {
        "CodigoEnvio": "IBPEF",
        "Descripcion": "Banco PYME Ecofuturo S.A.",
        "CodigoTipoEntidad": "IBP",
        "DescripcionTipoEntidad": "Banco PYME",
        "Estado": "VIGENTE",
    },
    {
        "CodigoEnvio": "IIIPM",
        "Descripcion": "Fundación Pro Mujer IFD",
        "CodigoTipoEntidad": "IFD",
        "DescripcionTipoEntidad": "Institución Financiera de Desarrollo",
        "Estado": "VIGENTE",
    },
    {
        "CodigoEnvio": "ICACS",
        "Descripcion": "Cooperativa San Martín de Porres R.L.",
        "CodigoTipoEntidad": "ICA",
        "DescripcionTipoEntidad": "Cooperativa de Ahorro y Crédito",
        "Estado": "VIGENTE",
    },
]


def _detalle_solicitud_a_snake(d: dict) -> dict:
    """Traduce un ItemSolicitud (PascalCase, formato SOAP) a claves snake_case
    para reutilizar las funciones de `validation.py`. El tipo de persona no
    viaja por SOAP: se infiere de si trae RazonSocial o Nombres/Apellidos."""
    razon_social = d.get("RazonSocial") or ""
    return {
        "tipo_persona": "juridica" if razon_social else "natural",
        "nombres": d.get("Nombres") or "",
        "apellido_paterno": d.get("ApellidoPaterno") or "",
        "apellido_materno": d.get("ApellidoMaterno") or "",
        "razon_social": razon_social,
        "documento_tipo": d.get("DocumentoIdentidadTipo"),
        "documento_extension": d.get("DocumentoIdentidadExtension") or "",
        "monto_bs": d.get("MontoRetencionBs"),
        "monto_ufv": d.get("MontoRetencionUFV"),
        "auto_conclusion": d.get("AutoConclusion") or "",
    }


def _detalle_remision_a_snake(d: dict) -> dict:
    """Traduce un ItemRemision (PascalCase) a claves snake_case."""
    razon_social = d.get("RazonSocial") or ""
    return {
        "tipo_persona": "juridica" if razon_social else "natural",
        "nombres": d.get("Nombres") or "",
        "apellido_paterno": d.get("ApellidoPaterno") or "",
        "apellido_materno": d.get("ApellidoMaterno") or "",
        "razon_social": razon_social,
        "documento_tipo": d.get("TipoDocumento"),
        "documento_extension": d.get("ExtensionDocumento") or "",
    }


class MockSirefoGateway(SirefoGateway):
    """Simulacion en memoria del servicio SOAP SIREFO."""

    def __init__(self, config: EffectiveConfig) -> None:
        self._config = config
        self._solicitudes: dict[int, dict] = {}
        self._codigos_solicitud: set[str] = set()
        self._numero_sirefo_procesados: set[str] = set()
        self._remisiones: dict[int, dict] = {}

    # -- utilidades internas -------------------------------------------------
    def _validar_credenciales(self) -> None:
        if not self._config.asfi_usuario or not self._config.asfi_clave:
            raise SirefoFault(
                "Usuario o clave ASFI no configurados", "AutenticacionException"
            )

    def ping(self, texto: str) -> str:
        return f"ServicioRetencionFondos-v1.0-MOCK - Eco: {texto}"

    # -- solicitudes (retencion / suspension) --------------------------------
    def remitir_solicitud(self, cabecera: dict, detalles: list[dict]) -> dict:
        self._validar_credenciales()

        tipo_proceso = cabecera.get("TipoProceso")
        id_solicitud = cabecera.get("IdSolicitud")
        codigo_solicitud = cabecera.get("CodigoSolicitud")

        # Reglas de negocio (SPEC seccion 3), replicadas aqui como lo haria ASFI.
        # Cualquier violacion se traduce a SirefoFault: si llego hasta aqui es que
        # el backend ya debio rechazarla antes (400); si no fue asi, es una falla
        # de servicio, no un error de validacion del cliente.
        try:
            validar_fecha(cabecera.get("FechaEnvio"), "FechaEnvio")
            validar_detalle_cantidad(cabecera.get("DetalleCantidad"), len(detalles))
            adjunto = base64.b64decode(cabecera.get("Adjunto") or "")
            validar_pdf(adjunto)
            for d in detalles:
                snake = _detalle_solicitud_a_snake(d)
                validar_persona(snake)
                validar_extension(snake, contexto="solicitud")
                validar_monto(snake)
                validar_auto_conclusion(tipo_proceso, snake["auto_conclusion"])
        except ValueError as exc:
            raise SirefoFault(str(exc), "ValidacionException") from exc

        # Verificacion de integridad: recalculamos los hashes (con la codificacion
        # de la configuracion efectiva) y comparamos.
        encoding = self._config.hash_encoding
        if hashes.hash_cabecera_solicitud(cabecera, encoding) != cabecera.get("HashDatos"):
            raise SirefoFault("HashDatos de la cabecera no coincide", "IntegridadException")
        if hashes.hash_imagen(adjunto, encoding) != cabecera.get("HashImagen"):
            raise SirefoFault("HashImagen del adjunto no coincide", "IntegridadException")
        for d in detalles:
            if hashes.hash_detalle_solicitud(d, encoding) != d.get("HashDetalle"):
                raise SirefoFault(
                    f"HashDetalle del item {d.get('Item')} no coincide", "IntegridadException"
                )

        # Duplicados: no se procesan, se responde con Respuesta=1 (no es una falla de servicio).
        if id_solicitud in self._solicitudes or codigo_solicitud in self._codigos_solicitud:
            return {"Respuesta": 1, "Detalle": "IdSolicitud/CodigoSolicitud duplicado", "Confirmacion": False}

        circular = f"ASFI/DEP/CC-{id_solicitud:05d}/2026"
        fecha_circular = datetime.now(timezone.utc).strftime("%Y%m%d")
        numero_sirefo = f"SIREFO-{id_solicitud:06d}"

        self._solicitudes[id_solicitud] = {
            "tipo_proceso": tipo_proceso,
            "codigo_solicitud": codigo_solicitud,
            "fecha_envio": cabecera.get("FechaEnvio"),
            "estado": "Procesada",
            "circular": circular,
            "fecha_circular": fecha_circular,
            "numero_sirefo": numero_sirefo,
            "error_envio": "",
        }
        self._codigos_solicitud.add(codigo_solicitud)
        if tipo_proceso == "R":
            self._numero_sirefo_procesados.add(numero_sirefo)

        return {"Respuesta": 0, "Detalle": "OK", "Confirmacion": True, "NumeroSIREFO": numero_sirefo}

    # -- remisiones de fondos -------------------------------------------------
    def remitir_remision(self, cabecera: dict, detalles: list[dict]) -> dict:
        self._validar_credenciales()

        numero_sirefo = cabecera.get("NumeroSIREFO") or ""
        if numero_sirefo not in self._numero_sirefo_procesados and not numero_sirefo.startswith(
            "SIREFO-"
        ):
            raise SirefoFault(
                "NumeroSIREFO no corresponde a una retencion procesada", "ReferenciaException"
            )

        id_remision = cabecera.get("IdRemision")
        try:
            validar_fecha(cabecera.get("FechaHoraEmision"), "FechaHoraEmision")
            validar_detalle_cantidad(cabecera.get("DetalleCantidad"), len(detalles))
            adjunto = base64.b64decode(cabecera.get("Adjunto") or "")
            validar_pdf(adjunto)
            for d in detalles:
                snake = _detalle_remision_a_snake(d)
                validar_persona(snake)
                validar_extension(snake, contexto="remision")
                if d.get("MontoRemision") is None:
                    raise ValueError("Se debe indicar el monto de la remision")
                if d.get("CuentaMoneda") not in (1, 2, 3, 4):
                    raise ValueError("CuentaMoneda debe ser 1, 2, 3 o 4")
        except ValueError as exc:
            raise SirefoFault(str(exc), "ValidacionException") from exc

        encoding = self._config.hash_encoding
        if hashes.hash_cabecera_remision(cabecera, encoding) != cabecera.get("HashDatos"):
            raise SirefoFault("HashDatos de la cabecera no coincide", "IntegridadException")
        if hashes.hash_imagen(adjunto, encoding) != cabecera.get("HashImagen"):
            raise SirefoFault("HashImagen del adjunto no coincide", "IntegridadException")
        for d in detalles:
            if hashes.hash_detalle_remision(d, encoding) != d.get("HashDetalle"):
                raise SirefoFault(
                    f"HashDetalle del item {d.get('Item')} no coincide", "IntegridadException"
                )

        if id_remision in self._remisiones:
            return {"Respuesta": 1, "Detalle": "IdRemision duplicado", "Confirmacion": False}

        circular = f"ASFI/DEP/CC-{id_remision:05d}/2026"
        fecha_circular = datetime.now(timezone.utc).strftime("%Y%m%d")
        self._remisiones[id_remision] = {
            "estado": "Procesada",
            "circular": circular,
            "fecha_circular": fecha_circular,
            "error_envio": "",
        }
        return {"Respuesta": 0, "Detalle": "OK", "Confirmacion": True}

    # -- consultas --------------------------------------------------------
    def consulta_cabecera(self) -> int:
        if not self._solicitudes:
            return 0
        return max(self._solicitudes.keys())

    def consultar_estado_envio(self, id_solicitud: int, tipo: int) -> dict:
        if tipo in (1, 2):
            rec = self._solicitudes.get(id_solicitud)
            if rec is None:
                raise SirefoFault("No existe una solicitud con ese IdSolicitud", "NotFoundException")
        elif tipo == 4:
            rec = self._remisiones.get(id_solicitud)
            if rec is None:
                raise SirefoFault("No existe una remision con ese IdRemision", "NotFoundException")
        else:
            raise SirefoFault("Tipo de consulta invalido", "ValidacionException")

        return {
            "Circular": rec["circular"],
            "ErrorEnvio": rec.get("error_envio") or "",
            "Estado": rec["estado"],
            "FechaCircular": rec["fecha_circular"],
            "cTipo": str(tipo),
            "Tipo": tipo,
            "cIDSolicitud": str(id_solicitud),
        }

    def consultar_lista_estado_envio(self, fecha_envio: str) -> list[dict]:
        resultado = []
        for id_solicitud, rec in self._solicitudes.items():
            if rec.get("fecha_envio") == fecha_envio:
                resultado.append(
                    {
                        "Circular": rec["circular"],
                        "ErrorEnvio": rec.get("error_envio") or "",
                        "Estado": rec["estado"],
                        "FechaCircular": rec["fecha_circular"],
                        "cTipo": "1" if rec["tipo_proceso"] == "R" else "2",
                        "Tipo": 1 if rec["tipo_proceso"] == "R" else 2,
                        "cIDSolicitud": str(id_solicitud),
                    }
                )
        return resultado

    def consulta_entidad_vigente(self) -> list[dict]:
        return ENTIDADES_VIGENTES

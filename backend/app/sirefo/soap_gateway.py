"""Gateway SOAP real contra el servicio SIREFO de ASFI (SIREFO_MODE=soap).

Usa `zeep` contra el WSDL publicado por ASFI. El cliente SOAP se construye de
forma perezosa (solo en el primer uso) para que la aplicacion pueda arrancar
sin acceso de red ni WSDL disponible (por ejemplo en pruebas con modo mock).

Nota: los nombres exactos de los tipos complejos del WSDL (p.ej. el nombre de
la operacion o el namespace de `RemitirSolicitudBsoUFVRequest`) deben
ajustarse cuando se tenga acceso al WSDL real via SIGMA; aqui se usan los
nombres documentados en el oficio ASFI del 22/11/2022 (ver SPEC seccion 3).
"""
import zeep
from requests import Session
from zeep.exceptions import Fault as ZeepFault
from zeep.transports import Transport

from app.runtime_config import EffectiveConfig
from app.sirefo.gateway import SirefoFault, SirefoGateway


class SoapSirefoGateway(SirefoGateway):
    """Adaptador SirefoGateway -> SOAP real via zeep."""

    def __init__(self, config: EffectiveConfig) -> None:
        self._config = config
        self._client: zeep.Client | None = None
        self._client_key: tuple[str, bool] | None = None

    def _get_client(self) -> zeep.Client:
        """Construye el cliente zeep en el primer uso (perezoso), para no requerir
        red ni WSDL disponible al arrancar la aplicacion.

        Se cachea junto con la clave (wsdl_url, tls_verify) con la que se
        construyo: si esos valores cambian (p. ej. porque la configuracion
        efectiva vino de la BD y fue editada), se reconstruye en la siguiente
        llamada en vez de seguir usando un cliente obsoleto.
        """
        clave_actual = (self._config.wsdl_url, self._config.tls_verify)
        if self._client is None or self._client_key != clave_actual:
            session = Session()
            session.verify = self._config.tls_verify
            transport = Transport(session=session, timeout=60, operation_timeout=60)
            self._client = zeep.Client(wsdl=self._config.wsdl_url, transport=transport)
            self._client_key = clave_actual
        return self._client

    def _login(self) -> dict:
        return {"Usuario": self._config.asfi_usuario, "Clave": self._config.asfi_clave}

    def _call(self, operacion: str, **kwargs):
        """Invoca una operacion SOAP y traduce zeep.exceptions.Fault a SirefoFault."""
        client = self._get_client()
        try:
            servicio = getattr(client.service, operacion)
            return servicio(**kwargs)
        except ZeepFault as exc:
            detalle = getattr(exc, "detail", None)
            mensaje = str(exc)
            tipo_excepcion = "SoapFault"
            if detalle is not None:
                # Se intenta extraer FallaServicio{Mensaje, TipoExcepcion} del detalle SOAP.
                falla = getattr(detalle, "FallaServicio", None) or detalle
                mensaje = getattr(falla, "Mensaje", mensaje)
                tipo_excepcion = getattr(falla, "TipoExcepcion", tipo_excepcion)
            raise SirefoFault(mensaje, tipo_excepcion) from exc

    def ping(self, texto: str) -> str:
        return self._call("Ping", texto=texto)

    def remitir_solicitud(self, cabecera: dict, detalles: list[dict]) -> dict:
        request = {"Login": self._login(), "Cabecera": cabecera, "Detalle": detalles}
        respuesta = self._call("RemitirSolicitud", request=request)
        return dict(respuesta) if respuesta is not None else {}

    def remitir_remision(self, cabecera: dict, detalles: list[dict]) -> dict:
        request = {"Login": self._login(), "Cabecera": cabecera, "Detalle": detalles}
        respuesta = self._call("RemitirRemisionFondos", request=request)
        return dict(respuesta) if respuesta is not None else {}

    def consulta_cabecera(self) -> int:
        respuesta = self._call("ConsultaCabecera", login=self._login())
        return int(respuesta) if respuesta is not None else 0

    def consultar_estado_envio(self, id_solicitud: int, tipo: int) -> dict:
        respuesta = self._call(
            "ConsultarEstadoEnvio", login=self._login(), idSolicitud=id_solicitud, tipo=tipo
        )
        return dict(respuesta) if respuesta is not None else {}

    def consultar_lista_estado_envio(self, fecha_envio: str) -> list[dict]:
        respuesta = self._call(
            "ConsultarListaEstadoEnvio", login=self._login(), fechaEnvio=fecha_envio
        )
        return [dict(item) for item in (respuesta or [])]

    def consulta_entidad_vigente(self) -> list[dict]:
        respuesta = self._call("ConsultaEntidadVigente", login=self._login())
        return [dict(item) for item in (respuesta or [])]

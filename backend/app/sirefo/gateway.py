"""Interfaz abstracta del gateway SIREFO y fabrica segun configuracion.

El gateway encapsula la comunicacion con el servicio SOAP de ASFI (o su
simulacion en modo mock). Los routers de la API solo conocen esta interfaz,
nunca los detalles de SOAP ni del mock.
"""
from abc import ABC, abstractmethod
from functools import lru_cache

from app.runtime_config import EffectiveConfig


class SirefoFault(Exception):
    """Error de negocio devuelto por ASFI (FaultException / FallaServicio)."""

    def __init__(self, mensaje: str, tipo_excepcion: str = "Exception"):
        self.mensaje = mensaje
        self.tipo_excepcion = tipo_excepcion
        super().__init__(f"{mensaje} ({tipo_excepcion})")


class SirefoGateway(ABC):
    """Operaciones SOAP de SIREFO que consume el backend (ver SPEC seccion 3)."""

    @abstractmethod
    def ping(self, texto: str) -> str:
        """Prueba de vida: retorna 'Servicio-Version-eco'."""

    @abstractmethod
    def remitir_solicitud(self, cabecera: dict, detalles: list[dict]) -> dict:
        """Envia una solicitud de retencion (R) o suspension (S). Retorna EstadoEnvio."""

    @abstractmethod
    def remitir_remision(self, cabecera: dict, detalles: list[dict]) -> dict:
        """Envia una remision de fondos. Retorna EstadoEnvio."""

    @abstractmethod
    def consulta_cabecera(self) -> int:
        """Maximo IdSolicitud registrado por la entidad."""

    @abstractmethod
    def consultar_estado_envio(self, id_solicitud: int, tipo: int) -> dict:
        """Estado de un envio (tipo: 1=Retencion, 2=Suspension/Levantamiento, 4=Remision)."""

    @abstractmethod
    def consultar_lista_estado_envio(self, fecha_envio: str) -> list[dict]:
        """Lista de estados de envio para una fecha dada."""

    @abstractmethod
    def consulta_entidad_vigente(self) -> list[dict]:
        """Lista de entidades financieras vigentes."""


@lru_cache
def get_gateway(config: EffectiveConfig) -> SirefoGateway:
    """Fabrica: devuelve la implementacion del gateway segun `config.mode`.

    `config` es la configuracion efectiva (entorno + overrides de BD, ver
    `app/runtime_config.py`). Se cachea por valor: mientras la configuracion
    efectiva no cambie, se reutiliza la misma instancia (y por tanto el estado
    en memoria del mock, o el cliente zeep ya construido); si cambia (p. ej.
    tras editarla desde el panel de administracion), se crea una instancia
    nueva con la configuracion nueva.
    """
    # Import diferido para evitar dependencias circulares entre modulos del gateway.
    if config.mode == "soap":
        from app.sirefo.soap_gateway import SoapSirefoGateway

        return SoapSirefoGateway(config)

    from app.sirefo.mock_gateway import MockSirefoGateway

    return MockSirefoGateway(config)

"""Configuracion de la aplicacion via variables de entorno (prefijo SIREFO_)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes de la aplicacion, cargados desde el entorno o un archivo .env."""

    model_config = SettingsConfigDict(
        env_prefix="SIREFO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gateway SIREFO: "mock" (simulado en proceso) o "soap" (ASFI real)
    mode: str = "mock"

    # WSDL real de ASFI (solo modo soap)
    wsdl_url: str = (
        "https://srvservicios.asfi.gov.bo/retencionesDev/ServicioRetencionFondos.svc?wsdl"
    )

    # Credenciales asignadas por ASFI
    asfi_usuario: str = ""
    asfi_clave: str = ""

    # Codigo de entidad asignado por ASFI
    entidad: str = "GAMW"

    # Codificacion de los hashes SHA-1: hex, HEX o base64
    hash_encoding: str = "hex"

    # Verificacion TLS del cliente SOAP
    tls_verify: bool = True

    # Seguridad JWT
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 8

    # Base de datos
    db_url: str = "sqlite:///./sirefo.db"

    # Usuario semilla admin
    admin_password: str = "admin123"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia de configuracion (cacheada)."""
    return Settings()

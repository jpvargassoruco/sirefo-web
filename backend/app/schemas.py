"""Esquemas Pydantic v2 para la API REST."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Auth / usuarios
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str = ""
    role: str = "consulta"


class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None
    full_name: str | None = None


# ---------------------------------------------------------------------------
# Solicitudes (retencion R / suspension S)
# ---------------------------------------------------------------------------
class SolicitudDetalleIn(BaseModel):
    tipo_persona: str  # natural|juridica
    nombres: str = ""
    apellido_paterno: str = ""
    apellido_materno: str = ""
    razon_social: str = ""
    documento_tipo: int
    documento_numero: str
    documento_complemento: str = ""
    documento_extension: str = ""
    documento_respaldo: str = ""
    tipo_respaldo: int
    monto_bs: Decimal | None = None
    monto_ufv: Decimal | None = None
    auto_conclusion: str = ""

    # El frontend puede enviar null en los campos no aplicables (p. ej. razon_social
    # para persona natural); se normaliza a cadena vacia / None segun el tipo.
    @field_validator(
        "nombres",
        "apellido_paterno",
        "apellido_materno",
        "razon_social",
        "documento_complemento",
        "documento_extension",
        "documento_respaldo",
        "auto_conclusion",
        mode="before",
    )
    @classmethod
    def _none_a_vacio(cls, v):
        return "" if v is None else v

    @field_validator("monto_bs", "monto_ufv", mode="before")
    @classmethod
    def _vacio_a_none(cls, v):
        return None if v in ("", None) else v


class SolicitudCreate(BaseModel):
    codigo_solicitud: str
    tipo_proceso: str  # R|S
    autoridad_solicitante: str
    autoridad_cargo: str
    gerencia: str
    detalles: list[SolicitudDetalleIn] = Field(default_factory=list)


class SolicitudDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item: int
    tipo_persona: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str
    razon_social: str
    documento_tipo: int
    documento_numero: str
    documento_complemento: str
    documento_extension: str
    documento_respaldo: str
    tipo_respaldo: int
    monto_bs: Decimal | None
    monto_ufv: Decimal | None
    auto_conclusion: str


class SolicitudOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_solicitud: int
    codigo_solicitud: str
    tipo_proceso: str
    autoridad_solicitante: str
    autoridad_cargo: str
    gerencia: str
    usuario_registro: str
    adjunto_nombre: str
    fecha_envio: str
    estado_local: str
    respuesta_codigo: int | None
    respuesta_detalle: str | None
    confirmacion: bool | None
    numero_sirefo: str | None
    estado_asfi: str | None
    circular: str | None
    fecha_circular: str | None
    error_envio_asfi: str | None
    created_at: datetime
    detalles: list[SolicitudDetalleOut] = []


class SolicitudListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_solicitud: int
    codigo_solicitud: str
    tipo_proceso: str
    autoridad_solicitante: str
    estado_local: str
    estado_asfi: str | None
    circular: str | None
    created_at: datetime


class SolicitudListOut(BaseModel):
    total: int
    page: int
    page_size: int = 20
    items: list[SolicitudListItem]


# ---------------------------------------------------------------------------
# Remisiones de fondos
# ---------------------------------------------------------------------------
class RemisionDetalleIn(BaseModel):
    tipo_persona: str
    nombres: str = ""
    apellido_paterno: str = ""
    apellido_materno: str = ""
    razon_social: str = ""
    numero_documento: str
    documento_complemento: str = ""
    extension_documento: str = ""
    tipo_documento: int
    documento_respaldo: str = ""
    tipo_respaldo: int
    monto_remision: Decimal
    numero_cuenta: str = ""
    cuenta_moneda: int
    codigo_envio: str = ""

    @field_validator(
        "nombres",
        "apellido_paterno",
        "apellido_materno",
        "razon_social",
        "documento_complemento",
        "extension_documento",
        "documento_respaldo",
        "numero_cuenta",
        "codigo_envio",
        mode="before",
    )
    @classmethod
    def _none_a_vacio(cls, v):
        return "" if v is None else v


class RemisionCreate(BaseModel):
    numero_sirefo: str
    identificador_remision: str
    autoridad_solicitante: str
    gerencia_solicitante: str
    cargo_solicitante: str
    detalles: list[RemisionDetalleIn] = Field(default_factory=list)


class RemisionDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item: int
    tipo_persona: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str
    razon_social: str
    numero_documento: str
    documento_complemento: str
    extension_documento: str
    tipo_documento: int
    documento_respaldo: str
    tipo_respaldo: int
    monto_remision: Decimal
    numero_cuenta: str
    cuenta_moneda: int
    codigo_envio: str


class RemisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_remision: int
    numero_sirefo: str
    identificador_remision: str
    autoridad_solicitante: str
    gerencia_solicitante: str
    cargo_solicitante: str
    fecha_hora_emision: str
    adjunto_nombre: str
    usuario_registro: str
    estado_local: str
    respuesta_codigo: int | None
    respuesta_detalle: str | None
    confirmacion: bool | None
    estado_asfi: str | None
    circular: str | None
    fecha_circular: str | None
    error_envio_asfi: str | None
    created_at: datetime
    detalles: list[RemisionDetalleOut] = []


class RemisionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_remision: int
    numero_sirefo: str
    identificador_remision: str
    estado_local: str
    estado_asfi: str | None
    created_at: datetime


class RemisionListOut(BaseModel):
    total: int
    page: int
    page_size: int = 20
    items: list[RemisionListItem]


# ---------------------------------------------------------------------------
# Configuracion de la conexion SIREFO (entorno + overrides en BD)
# ---------------------------------------------------------------------------
class ConfigSourcesOut(BaseModel):
    modo: str
    wsdl_url: str
    asfi_usuario: str
    entidad: str
    hash_encoding: str
    tls_verify: str


class ConfigOut(BaseModel):
    modo: str
    wsdl_url: str
    asfi_usuario: str
    entidad: str
    hash_encoding: str
    tls_verify: bool
    asfi_clave_definida: bool
    fuente: ConfigSourcesOut


class ConfigUpdate(BaseModel):
    modo: str | None = None
    wsdl_url: str | None = None
    asfi_usuario: str | None = None
    asfi_clave: str | None = None
    entidad: str | None = None
    hash_encoding: str | None = None
    tls_verify: bool | None = None


# ---------------------------------------------------------------------------
# Consultas / varios
# ---------------------------------------------------------------------------
class PingOut(BaseModel):
    respuesta: str


class EntidadVigenteOut(BaseModel):
    codigo_envio: str
    descripcion: str
    codigo_tipo_entidad: str
    descripcion_tipo_entidad: str
    estado: str


class MaxIdSolicitudOut(BaseModel):
    ultimo_id: int


class EstadoEnvioOut(BaseModel):
    circular: str | None = None
    error_envio: str | None = None
    estado: str | None = None
    fecha_circular: str | None = None
    c_tipo: str | None = None
    tipo: int | None = None
    c_id_solicitud: str | None = None


class EnvioLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ts: datetime
    usuario: str
    operacion: str
    request_resumen: str | None
    respuesta: str | None
    exito: bool


class EnvioLogListOut(BaseModel):
    total: int
    page: int
    page_size: int = 20
    items: list[EnvioLogOut]

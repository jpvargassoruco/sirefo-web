"""Modelos ORM (SQLAlchemy 2.x) segun el modelo de datos del SPEC (seccion 2)."""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Usuario del sistema web (no confundir con el usuario/clave de ASFI)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="consulta")  # admin|operador|consulta
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Solicitud(Base):
    """Solicitud de retencion (R) o suspension (S) de fondos enviada a ASFI."""

    __tablename__ = "solicitudes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_solicitud: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    codigo_solicitud: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    tipo_proceso: Mapped[str] = mapped_column(String(1))  # R|S
    autoridad_solicitante: Mapped[str] = mapped_column(String(200))
    autoridad_cargo: Mapped[str] = mapped_column(String(200))
    gerencia: Mapped[str] = mapped_column(String(200))
    usuario_registro: Mapped[str] = mapped_column(String(200))
    adjunto_nombre: Mapped[str] = mapped_column(String(255))
    adjunto_pdf: Mapped[bytes] = mapped_column(LargeBinary)
    fecha_envio: Mapped[str] = mapped_column(String(14))  # YYYYMMDDHHMISS

    estado_local: Mapped[str] = mapped_column(String(20), default="borrador")
    # borrador|enviada|error_envio

    respuesta_codigo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    respuesta_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmacion: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    numero_sirefo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estado_asfi: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Procesada|No Procesada|Con error
    circular: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_circular: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error_envio_asfi: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    detalles: Mapped[list["SolicitudDetalle"]] = relationship(
        back_populates="solicitud", cascade="all, delete-orphan", order_by="SolicitudDetalle.item"
    )


class SolicitudDetalle(Base):
    """Item (persona) de una solicitud de retencion/suspension."""

    __tablename__ = "solicitud_detalles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"))
    item: Mapped[int] = mapped_column(Integer)  # 1..n

    tipo_persona: Mapped[str] = mapped_column(String(10))  # natural|juridica
    nombres: Mapped[str] = mapped_column(String(200), default="")
    apellido_paterno: Mapped[str] = mapped_column(String(100), default="")
    apellido_materno: Mapped[str] = mapped_column(String(100), default="")
    razon_social: Mapped[str] = mapped_column(String(200), default="")

    documento_tipo: Mapped[int] = mapped_column(Integer)  # 1..5
    documento_numero: Mapped[str] = mapped_column(String(50))
    documento_complemento: Mapped[str] = mapped_column(String(20), default="")
    documento_extension: Mapped[str] = mapped_column(String(5), default="")

    documento_respaldo: Mapped[str] = mapped_column(String(100), default="")
    tipo_respaldo: Mapped[int] = mapped_column(Integer)  # 1..4

    monto_bs: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    monto_ufv: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    auto_conclusion: Mapped[str] = mapped_column(String(200), default="")  # solo suspensiones

    solicitud: Mapped["Solicitud"] = relationship(back_populates="detalles")


class Remision(Base):
    """Remision de fondos retenidos previamente (requiere NumeroSIREFO de una retencion)."""

    __tablename__ = "remisiones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_remision: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    numero_sirefo: Mapped[str] = mapped_column(String(50))
    identificador_remision: Mapped[str] = mapped_column(String(100))
    autoridad_solicitante: Mapped[str] = mapped_column(String(200))
    gerencia_solicitante: Mapped[str] = mapped_column(String(200))
    cargo_solicitante: Mapped[str] = mapped_column(String(200))
    fecha_hora_emision: Mapped[str] = mapped_column(String(14))  # YYYYMMDDHHMISS

    adjunto_nombre: Mapped[str] = mapped_column(String(255))
    adjunto_pdf: Mapped[bytes] = mapped_column(LargeBinary)
    usuario_registro: Mapped[str] = mapped_column(String(200))

    estado_local: Mapped[str] = mapped_column(String(20), default="borrador")
    respuesta_codigo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    respuesta_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmacion: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    estado_asfi: Mapped[str | None] = mapped_column(String(50), nullable=True)
    circular: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_circular: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error_envio_asfi: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    detalles: Mapped[list["RemisionDetalle"]] = relationship(
        back_populates="remision", cascade="all, delete-orphan", order_by="RemisionDetalle.item"
    )


class RemisionDetalle(Base):
    """Item (persona/cuenta) de una remision de fondos."""

    __tablename__ = "remision_detalles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    remision_id: Mapped[int] = mapped_column(ForeignKey("remisiones.id"))
    item: Mapped[int] = mapped_column(Integer)

    tipo_persona: Mapped[str] = mapped_column(String(10))  # natural|juridica
    nombres: Mapped[str] = mapped_column(String(200), default="")
    apellido_paterno: Mapped[str] = mapped_column(String(100), default="")
    apellido_materno: Mapped[str] = mapped_column(String(100), default="")
    razon_social: Mapped[str] = mapped_column(String(200), default="")

    numero_documento: Mapped[str] = mapped_column(String(50))
    documento_complemento: Mapped[str] = mapped_column(String(20), default="")
    extension_documento: Mapped[str] = mapped_column(String(5), default="")
    tipo_documento: Mapped[int] = mapped_column(Integer)  # 1..5

    documento_respaldo: Mapped[str] = mapped_column(String(100), default="")
    tipo_respaldo: Mapped[int] = mapped_column(Integer)  # 1..4

    monto_remision: Mapped[float] = mapped_column(Numeric(18, 2))
    numero_cuenta: Mapped[str] = mapped_column(String(50), default="")
    cuenta_moneda: Mapped[int] = mapped_column(Integer)  # 1..4
    codigo_envio: Mapped[str] = mapped_column(String(50), default="")

    remision: Mapped["Remision"] = relationship(back_populates="detalles")


class AppConfig(Base):
    """Configuracion de la conexion SIREFO editable desde el panel de administracion.

    Fila unica (id=1): cualquier columna no nula/no vacia sobreescribe el valor
    correspondiente de `Settings` (entorno / `.env`). Ver `app/runtime_config.py`.
    """

    __tablename__ = "app_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    modo: Mapped[str | None] = mapped_column(String(10), nullable=True)  # mock|soap
    wsdl_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    asfi_usuario: Mapped[str | None] = mapped_column(String(200), nullable=True)
    asfi_clave: Mapped[str | None] = mapped_column(String(200), nullable=True)
    entidad: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hash_encoding: Mapped[str | None] = mapped_column(String(10), nullable=True)  # hex|HEX|base64
    tls_verify: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class EnvioLog(Base):
    """Auditoria de todas las operaciones realizadas contra el gateway SIREFO."""

    __tablename__ = "envio_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    usuario: Mapped[str] = mapped_column(String(64), default="")
    operacion: Mapped[str] = mapped_column(String(100))
    request_resumen: Mapped[str | None] = mapped_column(Text, nullable=True)
    respuesta: Mapped[str | None] = mapped_column(Text, nullable=True)
    exito: Mapped[bool] = mapped_column(Boolean, default=True)

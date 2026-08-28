"""Autenticacion JWT y control de acceso por rol (admin|operador|consulta)."""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contrasena."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verifica una contrasena en texto plano contra su hash bcrypt."""
    return pwd_context.verify(password, hashed)


def create_access_token(user: User) -> str:
    """Genera un JWT firmado con los datos basicos del usuario."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependencia: extrae y valida el JWT del header Authorization, devuelve el User."""
    settings = get_settings()
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales invalidas o sesion expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise error
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        raise error from None

    user_id = payload.get("sub")
    user = db.get(User, int(user_id)) if user_id is not None else None
    if user is None or not user.is_active:
        raise error
    return user


def require_role(*roles: str):
    """Fabrica de dependencias que exige que el usuario actual tenga uno de los roles dados."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para realizar esta accion",
            )
        return user

    return _checker


# Atajos de uso comun: operador y admin pueden operar sobre solicitudes/remisiones,
# consulta solo puede leer (cualquier usuario autenticado).
require_operador = require_role("admin", "operador")
require_admin = require_role("admin")

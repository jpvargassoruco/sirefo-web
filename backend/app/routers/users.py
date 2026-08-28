"""CRUD basico de usuarios del sistema web (solo administradores)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import hash_password, require_admin
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut], dependencies=[Depends(require_admin)])
def listar_usuarios(db: Session = Depends(get_db)) -> list[UserOut]:
    """Lista todos los usuarios del sistema."""
    usuarios = db.query(User).order_by(User.username).all()
    return [UserOut.model_validate(u) for u in usuarios]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def crear_usuario(datos: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    """Crea un nuevo usuario."""
    if db.query(User).filter(User.username == datos.username).first() is not None:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    if datos.role not in ("admin", "operador", "consulta"):
        raise HTTPException(status_code=400, detail="Rol invalido")
    usuario = User(
        username=datos.username,
        full_name=datos.full_name,
        hashed_password=hash_password(datos.password),
        role=datos.role,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return UserOut.model_validate(usuario)


@router.patch("/{user_id}", response_model=UserOut, dependencies=[Depends(require_admin)])
def actualizar_usuario(user_id: int, datos: UserUpdate, db: Session = Depends(get_db)) -> UserOut:
    """Actualiza rol, estado activo, nombre o contrasena de un usuario."""
    usuario = db.get(User, user_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if datos.role is not None:
        if datos.role not in ("admin", "operador", "consulta"):
            raise HTTPException(status_code=400, detail="Rol invalido")
        usuario.role = datos.role
    if datos.is_active is not None:
        usuario.is_active = datos.is_active
    if datos.full_name is not None:
        usuario.full_name = datos.full_name
    if datos.password:
        usuario.hashed_password = hash_password(datos.password)
    db.commit()
    db.refresh(usuario)
    return UserOut.model_validate(usuario)

"""Utilidad de auditoria: registra cada operacion contra el gateway SIREFO."""
import json

from sqlalchemy.orm import Session

from app.models import EnvioLog


def registrar_log(
    db: Session,
    usuario: str,
    operacion: str,
    request_resumen: dict | None,
    respuesta: object,
    exito: bool,
) -> None:
    """Inserta una fila de auditoria (EnvioLog). No lanza excepciones si falla
    la serializacion; se guarda un resumen textual en su lugar."""
    try:
        resumen = json.dumps(request_resumen, default=str, ensure_ascii=False) if request_resumen else None
    except TypeError:
        resumen = str(request_resumen)
    try:
        texto_respuesta = json.dumps(respuesta, default=str, ensure_ascii=False)
    except TypeError:
        texto_respuesta = str(respuesta)

    db.add(
        EnvioLog(
            usuario=usuario,
            operacion=operacion,
            request_resumen=resumen,
            respuesta=texto_respuesta,
            exito=exito,
        )
    )
    db.commit()

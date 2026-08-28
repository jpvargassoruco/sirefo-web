"""Prueba de flujo completo de la API contra el gateway mock (SPEC seccion 9).

Usa una base SQLite temporal y SIREFO_MODE=mock. El entorno se configura ANTES
de importar cualquier modulo de la aplicacion, porque `Settings` se cachea
(`lru_cache`) durante toda la sesion de pruebas.
"""
import json
import os
import tempfile

import pytest

_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP_DB.close()

os.environ["SIREFO_MODE"] = "mock"
os.environ["SIREFO_DB_URL"] = f"sqlite:///{_TMP_DB.name}"
os.environ["SIREFO_JWT_SECRET"] = "test-secret"
os.environ["SIREFO_ADMIN_PASSWORD"] = "admin123"
os.environ["SIREFO_ASFI_USUARIO"] = "usuario_test"
os.environ["SIREFO_ASFI_CLAVE"] = "clave_test"
os.environ["SIREFO_ENTIDAD"] = "GAMW"
os.environ["SIREFO_HASH_ENCODING"] = "hex"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.sirefo.gateway import get_gateway  # noqa: E402

get_gateway.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PDF_MINIMO = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\ntrailer\n<< >>\n%%EOF"

# Estado compartido entre pruebas dentro del mismo modulo (flujo secuencial).
_estado: dict = {}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _detalle_natural(**overrides):
    detalle = {
        "tipo_persona": "natural",
        "nombres": "Maria",
        "apellido_paterno": "Garcia",
        "apellido_materno": "Lopez",
        "razon_social": "",
        "documento_tipo": 2,
        "documento_numero": "1234567",
        "documento_complemento": "",
        "documento_extension": "SC",
        "documento_respaldo": "Nota de prensa",
        "tipo_respaldo": 1,
        "monto_bs": 1500.50,
        "monto_ufv": None,
        "auto_conclusion": "",
    }
    detalle.update(overrides)
    return detalle


def _solicitud_valida(codigo="CITE-0001/2026", **overrides):
    data = {
        "codigo_solicitud": codigo,
        "tipo_proceso": "R",
        "autoridad_solicitante": "Juan Perez",
        "autoridad_cargo": "Alcalde",
        "gerencia": "Gerencia Juridica",
        "detalles": [_detalle_natural()],
    }
    data.update(overrides)
    return data


def _post_solicitud(client, headers, data, pdf_bytes=PDF_MINIMO, filename="nota.pdf"):
    return client.post(
        "/api/solicitudes",
        data={"data": json.dumps(data)},
        files={"adjunto": (filename, pdf_bytes, "application/pdf")},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Autenticacion y ping
# ---------------------------------------------------------------------------
def test_login_correcto(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["username"] == "admin"
    assert body["user"]["role"] == "admin"
    assert body["access_token"]


def test_login_incorrecto(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "incorrecta"})
    assert resp.status_code == 401


def test_ping(client, auth_headers):
    resp = client.get("/api/sirefo/ping", params={"texto": "hola"}, headers=auth_headers)
    assert resp.status_code == 200
    assert "MOCK" in resp.json()["respuesta"]
    assert "hola" in resp.json()["respuesta"]


def test_entidades_vigentes(client, auth_headers):
    resp = client.get("/api/sirefo/entidades", headers=auth_headers)
    assert resp.status_code == 200
    entidades = resp.json()
    assert len(entidades) >= 5
    assert all("codigo_envio" in e for e in entidades)


# ---------------------------------------------------------------------------
# Flujo completo: crear solicitud R valida -> consultar estado -> Procesada
# ---------------------------------------------------------------------------
def test_crear_solicitud_r_valida(client, auth_headers):
    resp = _post_solicitud(client, auth_headers, _solicitud_valida())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["estado_local"] == "enviada"
    assert body["confirmacion"] is True
    assert body["respuesta_codigo"] == 0
    assert body["numero_sirefo"].startswith("SIREFO-")
    assert len(body["detalles"]) == 1
    _estado["solicitud_id"] = body["id"]
    _estado["numero_sirefo"] = body["numero_sirefo"]


def test_consultar_estado_queda_procesada(client, auth_headers):
    solicitud_id = _estado["solicitud_id"]
    resp = client.post(f"/api/solicitudes/{solicitud_id}/consultar-estado", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["estado_asfi"] == "Procesada"
    assert body["circular"]
    assert body["circular"].startswith("ASFI/DEP/CC-")


def test_obtener_solicitud_y_adjunto(client, auth_headers):
    solicitud_id = _estado["solicitud_id"]
    resp = client.get(f"/api/solicitudes/{solicitud_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["codigo_solicitud"] == "CITE-0001/2026"

    resp_pdf = client.get(f"/api/solicitudes/{solicitud_id}/adjunto", headers=auth_headers)
    assert resp_pdf.status_code == 200
    assert resp_pdf.content == PDF_MINIMO
    assert resp_pdf.headers["content-type"] == "application/pdf"


def test_listar_solicitudes(client, auth_headers):
    resp = client.get("/api/solicitudes", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


# ---------------------------------------------------------------------------
# Casos invalidos -> 400
# ---------------------------------------------------------------------------
def test_juridica_con_documento_tipo_invalido(client, auth_headers):
    """Persona juridica requiere documento_tipo 1 o 3; tipo 2 debe rechazarse."""
    detalle = _detalle_natural(
        tipo_persona="juridica",
        nombres="",
        apellido_paterno="",
        apellido_materno="",
        razon_social="Empresa SRL",
        documento_tipo=2,
    )
    data = _solicitud_valida(codigo="CITE-0002/2026", detalles=[detalle])
    resp = _post_solicitud(client, auth_headers, data)
    assert resp.status_code == 400
    assert "juridica" in resp.json()["detail"].lower() or "documento" in resp.json()["detail"].lower()


def test_monto_bs_y_ufv_a_la_vez(client, auth_headers):
    detalle = _detalle_natural(monto_bs=100.0, monto_ufv=50.0)
    data = _solicitud_valida(codigo="CITE-0003/2026", detalles=[detalle])
    resp = _post_solicitud(client, auth_headers, data)
    assert resp.status_code == 400
    assert "monto" in resp.json()["detail"].lower()


def test_adjunto_no_es_pdf(client, auth_headers):
    data = _solicitud_valida(codigo="CITE-0004/2026")
    resp = _post_solicitud(client, auth_headers, data, pdf_bytes=b"esto no es un pdf")
    assert resp.status_code == 400
    assert "pdf" in resp.json()["detail"].lower()


def test_codigo_solicitud_duplicado(client, auth_headers):
    """CITE-0001/2026 ya fue usado en test_crear_solicitud_r_valida."""
    data = _solicitud_valida(codigo="CITE-0001/2026")
    resp = _post_solicitud(client, auth_headers, data)
    assert resp.status_code == 400
    assert "duplicado" in resp.json()["detail"].lower() or "ya fue" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Remision de fondos, referenciando el NumeroSIREFO obtenido arriba
# ---------------------------------------------------------------------------
def test_crear_remision_valida(client, auth_headers):
    numero_sirefo = _estado["numero_sirefo"]
    data = {
        "numero_sirefo": numero_sirefo,
        "identificador_remision": "REM-0001",
        "autoridad_solicitante": "Juan Perez",
        "gerencia_solicitante": "Gerencia Juridica",
        "cargo_solicitante": "Alcalde",
        "detalles": [
            {
                "tipo_persona": "natural",
                "nombres": "Maria",
                "apellido_paterno": "Garcia",
                "apellido_materno": "Lopez",
                "razon_social": "",
                "numero_documento": "1234567",
                "documento_complemento": "",
                "extension_documento": "SC",
                "tipo_documento": 2,
                "documento_respaldo": "Nota de remision",
                "tipo_respaldo": 1,
                "monto_remision": 1500.50,
                "numero_cuenta": "1002003",
                "cuenta_moneda": 1,
                "codigo_envio": "IBBUN",
            }
        ],
    }
    resp = client.post(
        "/api/remisiones",
        data={"data": json.dumps(data)},
        files={"adjunto": ("remision.pdf", PDF_MINIMO, "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["estado_local"] == "enviada"
    assert body["confirmacion"] is True
    _estado["remision_id"] = body["id"]


def test_consultar_estado_remision(client, auth_headers):
    remision_id = _estado["remision_id"]
    resp = client.post(f"/api/remisiones/{remision_id}/consultar-estado", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["estado_asfi"] == "Procesada"
    assert body["circular"]


def test_listar_remisiones(client, auth_headers):
    resp = client.get("/api/remisiones", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# Permisos y logs
# ---------------------------------------------------------------------------
def test_logs_solo_admin(client, auth_headers):
    resp = client.get("/api/logs", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_endpoint_sin_token_rechazado(client):
    resp = client.get("/api/solicitudes")
    assert resp.status_code == 401

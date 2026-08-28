"""Pruebas del endpoint de configuracion (`/api/config`, solo administradores)
y de que el gateway SIREFO usa la configuracion EFECTIVA (entorno + overrides
en BD), no solo el entorno (ver `app/runtime_config.py` y SPEC seccion 10).

Reutiliza la app/DB ya montada por `tests/test_api.py` (mismo proceso) y sus
helpers de construccion de solicitudes, importandolo explicitamente para
garantizar que su configuracion de entorno (modo mock, DB temporal, etc.) ya
esta lista antes de que corran estas pruebas, sin importar el orden de
recoleccion de pytest.
"""
import os

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models import AppConfig
from app.sirefo.gateway import get_gateway
from tests.test_api import _post_solicitud, _solicitud_valida


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def admin_headers(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def operador_headers(client, admin_headers):
    """Crea un usuario operador (no-admin) y devuelve sus headers de auth."""
    resp = client.post(
        "/api/users",
        json={
            "username": "operador_config_test",
            "password": "clave12345",
            "full_name": "Operador Config Test",
            "role": "operador",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    resp_login = client.post(
        "/api/auth/login", json={"username": "operador_config_test", "password": "clave12345"}
    )
    assert resp_login.status_code == 200, resp_login.text
    token = resp_login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _borrar_app_config() -> None:
    db = SessionLocal()
    try:
        fila = db.get(AppConfig, 1)
        if fila is not None:
            db.delete(fila)
            db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _config_limpia():
    """Cada prueba de este modulo arranca sin override de BD y con las caches
    de `Settings`/gateway limpias, para no depender de lo que dejo otra prueba."""
    _borrar_app_config()
    get_settings.cache_clear()
    get_gateway.cache_clear()
    yield
    _borrar_app_config()
    get_settings.cache_clear()
    get_gateway.cache_clear()


# ---------------------------------------------------------------------------
# Permisos
# ---------------------------------------------------------------------------
def test_get_config_no_admin_403(client, operador_headers):
    resp = client.get("/api/config", headers=operador_headers)
    assert resp.status_code == 403


def test_put_config_no_admin_403(client, operador_headers):
    resp = client.put("/api/config", json={"entidad": "XXXX"}, headers=operador_headers)
    assert resp.status_code == 403


def test_config_sin_token_401(client):
    resp = client.get("/api/config")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT como admin y GET reflejando los valores (clave siempre enmascarada)
# ---------------------------------------------------------------------------
def test_get_config_sin_override_refleja_entorno(client, admin_headers):
    resp = client.get("/api/config", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    settings = get_settings()
    assert body["modo"] == settings.mode
    assert body["entidad"] == settings.entidad
    assert body["hash_encoding"] == settings.hash_encoding
    assert all(v == "env" for v in body["fuente"].values())
    assert "asfi_clave" not in body


def test_put_config_como_admin_y_get_refleja_valores(client, admin_headers):
    resp = client.put(
        "/api/config",
        json={
            "modo": "mock",
            "entidad": "ENT-TEST",
            "asfi_usuario": "usuario_panel",
            "asfi_clave": "clave_panel",
            "hash_encoding": "HEX",
            "tls_verify": False,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["modo"] == "mock"
    assert body["entidad"] == "ENT-TEST"
    assert body["asfi_usuario"] == "usuario_panel"
    assert body["hash_encoding"] == "HEX"
    assert body["tls_verify"] is False
    assert body["asfi_clave_definida"] is True
    assert "asfi_clave" not in body
    assert body["fuente"] == {
        "modo": "db",
        "wsdl_url": "env",
        "asfi_usuario": "db",
        "entidad": "db",
        "hash_encoding": "db",
        "tls_verify": "db",
    }

    resp_get = client.get("/api/config", headers=admin_headers)
    assert resp_get.status_code == 200, resp_get.text
    body_get = resp_get.json()
    assert body_get["entidad"] == "ENT-TEST"
    assert body_get["asfi_usuario"] == "usuario_panel"
    assert body_get["asfi_clave_definida"] is True
    assert "asfi_clave" not in body_get


def test_put_config_clave_vacia_o_ausente_mantiene_la_actual(client, admin_headers):
    resp1 = client.put(
        "/api/config", json={"asfi_usuario": "u1", "asfi_clave": "c1"}, headers=admin_headers
    )
    assert resp1.status_code == 200, resp1.text
    assert resp1.json()["asfi_clave_definida"] is True

    # Cadena vacia: se mantiene la clave 'c1' ya guardada.
    resp2 = client.put(
        "/api/config", json={"asfi_usuario": "u2", "asfi_clave": ""}, headers=admin_headers
    )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["asfi_usuario"] == "u2"
    assert resp2.json()["asfi_clave_definida"] is True

    # Campo ausente: tambien se mantiene.
    resp3 = client.put("/api/config", json={"entidad": "ENT-2"}, headers=admin_headers)
    assert resp3.status_code == 200, resp3.text
    assert resp3.json()["asfi_clave_definida"] is True


def test_put_config_null_limpia_el_override(client, admin_headers):
    resp1 = client.put("/api/config", json={"entidad": "TEMPORAL"}, headers=admin_headers)
    assert resp1.status_code == 200, resp1.text
    assert resp1.json()["fuente"]["entidad"] == "db"

    resp2 = client.put("/api/config", json={"entidad": None}, headers=admin_headers)
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["fuente"]["entidad"] == "env"
    assert resp2.json()["entidad"] == get_settings().entidad


def test_put_config_null_en_clave_la_limpia(client, admin_headers):
    resp1 = client.put("/api/config", json={"asfi_clave": "algo"}, headers=admin_headers)
    assert resp1.status_code == 200, resp1.text
    assert resp1.json()["asfi_clave_definida"] is True

    resp2 = client.put("/api/config", json={"asfi_clave": None}, headers=admin_headers)
    assert resp2.status_code == 200, resp2.text
    # Sin override en BD ni en entorno de pruebas... salvo que el entorno ya
    # tenga una clave (test_api.py la fija): el resultado depende del entorno.
    assert resp2.json()["asfi_clave_definida"] == bool(get_settings().asfi_clave)


def test_put_config_modo_invalido_400(client, admin_headers):
    resp = client.put("/api/config", json={"modo": "invalido"}, headers=admin_headers)
    assert resp.status_code == 400


def test_put_config_hash_encoding_invalido_400(client, admin_headers):
    resp = client.put("/api/config", json={"hash_encoding": "base32"}, headers=admin_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Fin a fin: con credenciales de ENTORNO vacias, configurarlas via /api/config
# debe alcanzar para poder crear una solicitud (prueba que el gateway usa la
# configuracion efectiva, no solo `Settings`/entorno).
# ---------------------------------------------------------------------------
def test_credenciales_desde_bd_permiten_crear_solicitud(client, admin_headers):
    usuario_previo = os.environ.get("SIREFO_ASFI_USUARIO")
    clave_previa = os.environ.get("SIREFO_ASFI_CLAVE")
    os.environ["SIREFO_ASFI_USUARIO"] = ""
    os.environ["SIREFO_ASFI_CLAVE"] = ""
    get_settings.cache_clear()
    get_gateway.cache_clear()
    try:
        assert get_settings().asfi_usuario == ""
        assert get_settings().asfi_clave == ""

        # Sin override en BD y con el entorno vacio, el mock debe rechazar el envio.
        resp_falla = _post_solicitud(
            client, admin_headers, _solicitud_valida(codigo="CITE-CFG-0001/2026")
        )
        assert resp_falla.status_code == 502, resp_falla.text
        assert "usuario" in resp_falla.json()["detail"].lower() or "clave" in resp_falla.json()["detail"].lower()

        resp_config = client.put(
            "/api/config",
            json={"asfi_usuario": "usuario_bd", "asfi_clave": "clave_bd"},
            headers=admin_headers,
        )
        assert resp_config.status_code == 200, resp_config.text
        assert resp_config.json()["asfi_clave_definida"] is True

        resp_ok = _post_solicitud(
            client, admin_headers, _solicitud_valida(codigo="CITE-CFG-0002/2026")
        )
        assert resp_ok.status_code == 201, resp_ok.text
        body = resp_ok.json()
        assert body["estado_local"] == "enviada"
        assert body["confirmacion"] is True
        assert body["respuesta_codigo"] == 0
    finally:
        if usuario_previo is None:
            os.environ.pop("SIREFO_ASFI_USUARIO", None)
        else:
            os.environ["SIREFO_ASFI_USUARIO"] = usuario_previo
        if clave_previa is None:
            os.environ.pop("SIREFO_ASFI_CLAVE", None)
        else:
            os.environ["SIREFO_ASFI_CLAVE"] = clave_previa
        get_settings.cache_clear()
        get_gateway.cache_clear()

# SIREFO Web — Alcaldía de Warnes

Sistema web para consumir el servicio SOAP **SIREFO** de ASFI (Sistema de Notificación de
Retenciones, Suspensiones y Remisión de Retención de Fondos), según la "Documentación
Técnica - Web Services" de ASFI (22/11/2022).

Permite a la entidad registrar y remitir a ASFI solicitudes de **retención (R)** y
**suspensión (S)** de fondos, **remisiones de fondos**, consultar el estado de los envíos
(Carta Circular) y administrar usuarios, todo desde una interfaz web en español.

## Arquitectura

```
React SPA (Vite, :5173)  ──REST/JSON──▶  Backend FastAPI (:8000)  ──SOAP──▶  ASFI SIREFO
                                              │
                                              └─ modo mock (por defecto): simula ASFI localmente
```

- Las credenciales ASFI, los hashes SHA-1 (`HashDatos`, `HashDetalle`, `HashImagen`) y el
  armado del mensaje SOAP viven **solo en el backend**.
- `SIREFO_MODE=mock` (por defecto) permite desarrollar y probar sin conectividad SIGMA.
  Con acceso real: `SIREFO_MODE=soap` + `SIREFO_WSDL_URL` + credenciales.

## Puesta en marcha

### Con Docker

Requiere Docker 28+ y Compose v2. `backend/.env` ya incluye valores de desarrollo (modo
mock) y no necesita modificarse.

```bash
docker compose up -d --build
```

- Frontend (servido por nginx, con `/api/` proxeado al backend): http://localhost:8080
- Usuario inicial: `admin` / `admin123`
- La base SQLite persiste en el volumen nombrado `sirefo_data` (montado en `/data` dentro
  del contenedor del backend), sobrevive a `docker compose down` y a reconstrucciones.
- Detener el stack: `docker compose down` (agregar `-v` para borrar también el volumen de
  datos).

El backend no publica ningún puerto en el host (solo es accesible desde `frontend` vía la
red interna de Compose); el frontend publica únicamente el puerto 8080.

### Manual (alternativa)

Backend (Python 3.11+):

```bash
cd backend
# backend/.env ya incluye valores de desarrollo (modo mock). Nota: incluso en modo
# mock las credenciales ASFI no pueden estar vacías (el mock imita al servicio real);
# cualquier valor no vacío sirve en mock.
./run.sh          # crea venv, instala dependencias y levanta la API en :8000
```

Frontend (Node 18+):

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173 (proxy /api → :8000)
```

Usuario inicial: `admin` / `admin123` (cámbielo vía `SIREFO_ADMIN_PASSWORD` y desde la UI).

Pruebas del backend: `cd backend && .venv/bin/pytest`.

## Configuración (variables `SIREFO_*`)

Ver `backend/.env.example` y `docs/SPEC.md` §1. Las más importantes:

| Variable | Descripción |
|---|---|
| `SIREFO_MODE` | `mock` (local) o `soap` (servicio real de ASFI) |
| `SIREFO_WSDL_URL` | WSDL del servicio (pruebas: `.../retencionesDev/ServicioRetencionFondos.svc?wsdl`) |
| `SIREFO_ASFI_USUARIO` / `SIREFO_ASFI_CLAVE` | Credenciales asignadas por ASFI (rol `ServicioRetenciones`) |
| `SIREFO_ENTIDAD` | Código de entidad asignado por ASFI |
| `SIREFO_HASH_ENCODING` | `hex` / `HEX` / `base64` — coordinar con ASFI |
| `SIREFO_JWT_SECRET` | Secreto JWT del backend (obligatorio cambiar en producción) |

## Antes de pasar a producción con ASFI

1. **Gestión formal ante ASFI**: solicitar usuario(s) con rol `ServicioRetenciones`
   (nota formal con nombre, cargo, CI y correo de cada usuario) y el código de entidad.
2. **Conectividad**: el servicio solo es accesible por la red **SIGMA** hacia la Supernet
   de ASFI (puerto 443; resolver `servicios.asfi.gov.bo` en el host si corresponde,
   `MaxReceivedMessageSize` 128 MB). No está en internet público.
3. **Coordinación técnica de hashes**: el documento exige SHA-1 sobre concatenaciones
   definidas, pero **no fija la codificación de salida** (hex/base64) — ajústela con
   `SIREFO_HASH_ENCODING` según lo que indique la contraparte técnica de ASFI.
4. Probar primero contra el endpoint de **pruebas** (`retencionesDev`) con `Ping` y una
   solicitud de ensayo; verificar contra el WSDL real los nombres exactos de tipos
   (el gateway zeep se genera del WSDL en runtime).
5. Cambiar `SIREFO_JWT_SECRET`, la clave de `admin`, y servir el frontend compilado
   (`npm run build`) detrás de HTTPS.

## Estructura

- `docs/MANUAL_USUARIO.md` — manual breve para operadores y usuarios de consulta.
- `docs/MANUAL_ADMIN.md` — manual breve de administración (usuarios, configuración, respaldo, producción).
- `docs/SPEC.md` — especificación técnica completa (contrato SOAP, hashes, API REST, UI).
- `docs/Documentación Técnica - Web Services (ASFI).pdf` — documento original de ASFI del que deriva la especificación.
- `backend/` — FastAPI + SQLAlchemy (SQLite) + gateway SIREFO (mock/zeep) + pruebas.
- `frontend/` — React 18 + Vite, SPA en español con control de roles (admin/operador/consulta).

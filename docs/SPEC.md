# SIREFO Web — Especificación técnica (v1)

Sistema para la Alcaldía de Warnes que consume el servicio SOAP **SIREFO** de ASFI
(retención, suspensión y remisión de retención de fondos) y provee una interfaz web
completa para usuarios finales.

Arquitectura: **React SPA** → **Backend FastAPI (REST/JSON)** → **Gateway SIREFO**
(modo `mock` local o modo `soap` real vía zeep). Las credenciales ASFI y los hashes
SHA-1 viven SOLO en el backend.

```
sirefo-web/
├── docs/SPEC.md
├── backend/
│   ├── requirements.txt
│   ├── run.sh                  # crea venv si falta, instala deps, uvicorn app.main:app --reload --port 8000
│   ├── .env.example
│   ├── app/
│   │   ├── main.py             # FastAPI app, CORS (localhost:5173), incluye routers, crea tablas, seed admin
│   │   ├── config.py           # Settings via pydantic-settings (prefijo SIREFO_)
│   │   ├── database.py         # SQLAlchemy 2.x, SQLite ./sirefo.db, session dependency
│   │   ├── models.py           # ORM
│   │   ├── schemas.py          # Pydantic v2
│   │   ├── auth.py             # JWT (PyJWT), bcrypt via passlib, get_current_user, require_role
│   │   ├── sirefo/
│   │   │   ├── hashes.py       # algoritmos SHA-1 del documento (ver §4)
│   │   │   ├── gateway.py      # clase abstracta SirefoGateway + factory por config
│   │   │   ├── mock_gateway.py # simula ASFI en proceso (ver §6)
│   │   │   └── soap_gateway.py # zeep contra WSDL real (ver §7)
│   │   └── routers/
│   │       ├── auth.py, users.py, solicitudes.py, remisiones.py, consultas.py
│   └── tests/
│       ├── test_hashes.py      # vectores del §4
│       └── test_api.py         # flujo completo contra el mock (httpx TestClient)
└── frontend/                   # React 18 + Vite + react-router-dom (JS, sin TS)
```

---

## 1. Configuración (backend/.env, prefijo `SIREFO_`)

| Variable | Default | Descripción |
|---|---|---|
| `SIREFO_MODE` | `mock` | `mock` o `soap` |
| `SIREFO_WSDL_URL` | `https://srvservicios.asfi.gov.bo/retencionesDev/ServicioRetencionFondos.svc?wsdl` | WSDL real (solo modo soap) |
| `SIREFO_ASFI_USUARIO` / `SIREFO_ASFI_CLAVE` | vacíos | Credenciales asignadas por ASFI (rol ServicioRetenciones) |
| `SIREFO_ENTIDAD` | `GAMW` | Código de entidad asignado por ASFI (ej. doc: AN, SIN, AJ) |
| `SIREFO_HASH_ENCODING` | `hex` | `hex`, `HEX` o `base64` (el doc no fija la codificación; se coordina con ASFI) |
| `SIREFO_JWT_SECRET` | `change-me` | secreto JWT |
| `SIREFO_DB_URL` | `sqlite:///./sirefo.db` | |
| `SIREFO_ADMIN_PASSWORD` | `admin123` | password del usuario semilla `admin` |

## 2. Modelo de datos (SQLAlchemy)

- **User**: id, username (unique), full_name, hashed_password, role (`admin`|`operador`|`consulta`), is_active, created_at.
- **Solicitud** (retención o suspensión): id, id_solicitud (int, correlativo enviado a ASFI, unique),
  codigo_solicitud (str, cite de la nota, unique), tipo_proceso (`R`|`S`), autoridad_solicitante,
  autoridad_cargo, gerencia, usuario_registro (str), adjunto_nombre, adjunto_pdf (LargeBinary),
  fecha_envio (str YYYYMMDDHHMISS), estado_local (`borrador`|`enviada`|`error_envio`),
  respuesta_codigo (int nullable), respuesta_detalle (text), confirmacion (bool nullable),
  estado_asfi (str nullable: Procesada/No Procesada/Con error), circular (str), fecha_circular (str),
  error_envio_asfi (text), created_by → User, created_at, detalles → SolicitudDetalle.
- **SolicitudDetalle**: id, solicitud_id FK, item (int, 1..n), tipo_persona (`natural`|`juridica`),
  nombres, apellido_paterno, apellido_materno, razon_social, documento_tipo (int 1..5),
  documento_numero, documento_complemento, documento_extension, documento_respaldo,
  tipo_respaldo (int 1..4), monto_bs (Numeric(18,2) nullable), monto_ufv (Numeric(18,2) nullable),
  auto_conclusion (str, solo suspensiones).
- **Remision**: id, id_remision (int unique), numero_sirefo, identificador_remision,
  autoridad_solicitante, gerencia_solicitante, cargo_solicitante, fecha_hora_emision,
  adjunto_nombre, adjunto_pdf, usuario_registro, estado_local, respuesta_codigo,
  respuesta_detalle, confirmacion, created_by, created_at, detalles → RemisionDetalle.
- **RemisionDetalle**: id, remision_id FK, item, tipo_persona, nombres, apellido_paterno,
  apellido_materno, razon_social, numero_documento, documento_complemento,
  extension_documento, tipo_documento (int 1..5), documento_respaldo, tipo_respaldo (1..4),
  monto_remision (Numeric(18,2)), numero_cuenta, cuenta_moneda (int 1..4), codigo_envio.
- **EnvioLog** (auditoría): id, ts, usuario, operacion, request_resumen (json/text), respuesta (text), exito (bool).

## 3. Contrato SOAP SIREFO (resumen del documento ASFI 22/11/2022)

Métodos que el gateway debe exponer (nombres de método Python → operación SOAP):

| Gateway | Operación SOAP | Uso |
|---|---|---|
| `ping(texto)` | `Ping` | prueba de vida; retorna "Servicio-Versión-eco" |
| `remitir_solicitud(cabecera, detalles)` | `RemitirSolicitud` (`RemitirSolicitudBsoUFVRequest`) | enviar retención (R) o suspensión (S) |
| `remitir_remision(cabecera, detalles)` | `RemitirRemisionFondos` (`RemitirRemisionRequest`) | remisión de fondos (requiere NumeroSIREFO de una retención previa) |
| `consulta_cabecera()` | `ConsultaCabecera` | máximo IdSolicitud registrado por la entidad |
| `consultar_estado_envio(id_solicitud, tipo)` | `ConsultarEstadoEnvio` | estado de un envío: tipo 1=Retención, 2=Suspensión/Levantamiento, 4=Remisión |
| `consultar_lista_estado_envio(fecha_envio)` | `ConsultarListaEstadoEnvio` | lista de estados |
| `consulta_entidad_vigente()` | `ConsultaEntidadVigente` | entidades financieras vigentes |

NO implementar `ConsultarEstadoSolicitud` (deprecado por ASFI). `RemitirConfirmacionEntidad`
es para uso de ASFI→autoridad; fuera de alcance v1.

Todos los requests llevan `Login {Usuario, Clave}` (config). Respuesta estándar
`EstadoEnvio {Detalle: str ("OK" o error), Respuesta: int (0=ok), Confirmacion: bool}`.
`EstadoSolicitud/EstadoConsultaEnvio {Circular, ErrorEnvio, Estado, FechaCircular, cTipo, Tipo, cIDSolicitud}`.
`EntidadVigente {CodigoEnvio, Descripcion, CodigoTipoEntidad, DescripcionTipoEntidad, Estado}`.
Errores de servicio: FaultException con `FallaServicio {Mensaje, TipoExcepcion}`.

**CabeceraSolicitud** (campos SOAP): Adjunto (base64 del PDF), AdjuntoNombre, AutoridadCargo,
AutoridadSolicitante, CodigoSolicitud, DetalleCantidad (int, debe cuadrar con len(detalles)),
Entidad, FechaEnvio (`YYYYMMDDHHMISS`), Gerencia, HashDatos, HashImagen, IdSolicitud (int),
TipoProceso (`R`|`S`), Usuario (nombre de la persona que registra).

**ItemSolicitud**: ApellidoMaterno, ApellidoPaterno, AutoConclusion, DocumentoIdentidadComplemento,
DocumentoIdentidadExtension (CH|LP|CB|OR|PO|TJ|SC|BE|PA|PE), DocumentoIdentidadNumero,
DocumentoIdentidadTipo (1=NIT, 2=CI, 3=RUC, 4=Pasaporte, 5=CI extranjero),
DocumentoRespaldo, HashDetalle, Item, MontoRetencionBs, MontoRetencionUFV, Nombres,
RazonSocial, TipoRespaldo (1=PIET, 2=PC, 3=AAPA, 4=RS).

**CabeceraRemision**: IdRemision (int), NumeroSIREFO, IdentificadorRemision, AutoridadSolicitante,
GerenciaSolicitante, CargoSolicitante, FechaHoraEmision, DetalleCantidad, HashDatos, Adjunto,
AdjuntoNombre, HashImagen, Entidad, Usuario.

**ItemRemision**: Item, ApellidoPaterno, ApellidoMaterno, Nombres, RazonSocial, NumeroDocumento,
DocumentoComplemento, ExtensionDocumento, TipoDocumento, DocumentoRespaldo, TipoRespaldo,
MontoRemision, NumeroCuenta, CuentaMoneda (1=BOB, 2=USD, 3=BOB c/MV, 4=MN con MV a UFV),
CodigoEnvio, HashDetalle, Entidad(?), Usuario(?) — incluir Entidad y Usuario como campos del ítem
porque participan en el hash según el documento.

### Reglas de validación de negocio (aplicar en backend, replicar en mock)

1. Persona natural: DocumentoIdentidadTipo ∈ {2,4,5}; requiere Nombres y al menos un apellido;
   RazonSocial vacía. Persona jurídica: tipo ∈ {1,3}; requiere RazonSocial; nombres/apellidos vacíos.
2. Extensión: PE solo con tipos 2 y 5; puede ser vacía para tipos 1,2,3,4 (solicitud) / 1,3,4 (remisión).
3. Monto: Bs **o** UFV, nunca ambos, nunca ninguno (en solicitudes); siempre 2 decimales, separador punto.
4. FechaEnvio/FechaHoraEmision: formato `YYYYMMDDHHMISS` (14 dígitos).
5. Adjunto: solo PDF (validar magic bytes `%PDF`), enviado como base64.
6. DetalleCantidad == número real de detalles.
7. IdSolicitud/CodigoSolicitud/IdRemision no pueden duplicarse (salvo reenvío tras error).
8. AutoConclusion solo aplica a suspensiones (TipoProceso=S).

## 4. Algoritmos de hash (SHA-1) — `app/sirefo/hashes.py`

Función auxiliar `_h(texto: str) -> str`: SHA-1 de `texto.encode("utf-8")`, salida según
`SIREFO_HASH_ENCODING`: `hex` (minúsculas, default), `HEX` (mayúsculas), `base64`.
Null/None → cadena vacía. Enteros → `str(n)`. Montos → formato `f"{monto:.2f}"`.

- `hash_cabecera_solicitud(c)`: concat en este orden exacto:
  `AdjuntoNombre, AutoridadCargo, AutoridadSolicitante, CodigoSolicitud, str(DetalleCantidad), Entidad, FechaEnvio, Gerencia, str(IdSolicitud), TipoProceso`
- `hash_detalle_solicitud(d)`: concat:
  `ApellidoMaterno, ApellidoPaterno, AutoConclusion, DocumentoIdentidadComplemento, DocumentoIdentidadExtension, DocumentoIdentidadNumero, str(DocumentoIdentidadTipo), DocumentoRespaldo, str(Item), montoBs_2dec_o_vacio, Nombres, RazonSocial, str(TipoRespaldo)`
  (nota: el documento NO incluye MontoRetencionUFV en el hash del detalle; respetarlo)
- `hash_imagen(pdf_bytes)`: SHA-1 de los bytes crudos del PDF.
- `hash_cabecera_remision(r)`: concat:
  `NumeroSIREFO, str(IdRemision), IdentificadorRemision, AutoridadSolicitante, GerenciaSolicitante, CargoSolicitante, FechaHoraEmision, str(DetalleCantidad), Entidad`
- `hash_detalle_remision(d)`: concat:
  `str(Item), ApellidoPaterno, ApellidoMaterno, Nombres, RazonSocial, NumeroDocumento, DocumentoComplemento, str(TipoDocumento), DocumentoRespaldo, str(TipoRespaldo), monto_2dec, NumeroCuenta, str(CuentaMoneda), CodigoEnvio, Entidad, Usuario`

Test vectors (calcular en el test con hashlib directamente y comparar contra las funciones;
además un vector fijo: `_h("")` con encoding hex == `da39a3ee5e6b4b0d3255bfef95601890afd80709`).

## 5. API REST del backend (todas bajo `/api`, JSON; auth Bearer JWT salvo login)

- `POST /api/auth/login` `{username, password}` → `{access_token, token_type, user:{id, username, full_name, role}}`
- `GET /api/auth/me` → user actual
- `GET/POST /api/users`, `PATCH /api/users/{id}` (solo admin; PATCH permite role/is_active/password)
- `GET /api/sirefo/ping?texto=...` → `{respuesta}` (proxy a Ping)
- `GET /api/sirefo/entidades` → lista EntidadVigente (para combos en el frontend)
- `GET /api/sirefo/max-id-solicitud` → `{ultimo_id}` (ConsultaCabecera)
- `POST /api/solicitudes` — multipart/form-data: campo `data` (JSON) + campo `adjunto` (PDF).
  `data = {codigo_solicitud, tipo_proceso, autoridad_solicitante, autoridad_cargo, gerencia, detalles:[{tipo_persona, nombres, apellido_paterno, apellido_materno, razon_social, documento_tipo, documento_numero, documento_complemento, documento_extension, documento_respaldo, tipo_respaldo, monto_bs, monto_ufv, auto_conclusion}]}`.
  El backend: valida reglas §3, asigna `id_solicitud` = max(local, ConsultaCabecera)+1, arma cabecera,
  calcula hashes, llama `remitir_solicitud`, persiste todo + respuesta. → 201 con la solicitud.
- `GET /api/solicitudes?estado=&tipo=&q=&page=` → lista paginada (sin PDF)
- `GET /api/solicitudes/{id}` → detalle completo (con detalles, sin binario)
- `GET /api/solicitudes/{id}/adjunto` → PDF (Content-Disposition)
- `POST /api/solicitudes/{id}/reenviar` → re-llama a ASFI (solo si estado_local=error_envio)
- `POST /api/solicitudes/{id}/consultar-estado` → llama ConsultarEstadoEnvio (tipo: R→1, S→2),
  actualiza estado_asfi/circular/fecha_circular → devuelve solicitud actualizada
- `POST /api/remisiones` — multipart igual que solicitudes; `data = {numero_sirefo, identificador_remision, autoridad_solicitante, gerencia_solicitante, cargo_solicitante, detalles:[{... campos ItemRemision en snake_case, codigo_envio}]}`
- `GET /api/remisiones`, `GET /api/remisiones/{id}`, `/adjunto`, `/reenviar`, `/consultar-estado` (tipo 4) — análogos
- `GET /api/consultas/lista-estado?fecha=YYYYMMDDHHMISS` → ConsultarListaEstadoEnvio
- `GET /api/logs?page=` (admin) → EnvioLog paginado

Roles: `consulta` solo GETs; `operador` además POST solicitudes/remisiones/consultar-estado/reenviar;
`admin` todo + usuarios + logs. Errores: 400 validación negocio `{detail}`, 502 si ASFI/gateway
retorna FallaServicio `{detail: "SIREFO: <Mensaje> (<TipoExcepcion>)"}`.

## 6. Mock gateway (`SIREFO_MODE=mock`)

Estado en memoria del proceso (dicts). Comportamiento:
- `ping(t)` → `"ServicioRetencionFondos-v1.0-MOCK - Eco: {t}"`.
- `remitir_solicitud`: valida credenciales config no vacías, valida reglas §3, valida hashes
  (recalcula y compara — así probamos nuestros propios hashes), rechaza IdSolicitud/CodigoSolicitud
  duplicado con `EstadoEnvio{Respuesta:1, Detalle:"...duplicado...", Confirmacion:false}`;
  si ok registra y retorna `{Respuesta:0, Detalle:"OK", Confirmacion:true}` y programa que el estado
  pase a "Procesada" con `Circular` = `ASFI/DEP/CC-{id:05d}/2026` inmediatamente (sin timers:
  primera consulta de estado ya la ve Procesada) y `NumeroSIREFO` = `SIREFO-{id:06d}`.
- `remitir_remision`: exige que NumeroSIREFO exista entre las solicitudes mock procesadas tipo R
  (o acepte cualquiera que empiece con "SIREFO-" para pruebas), mismas validaciones.
- `consulta_cabecera` → max IdSolicitud registrado (0 si ninguno).
- `consultar_estado_envio` / `consultar_lista_estado_envio` → estados registrados.
- `consulta_entidad_vigente` → lista fija de ~6 entidades bolivianas de ejemplo
  (IBBUN Banco Unión S.A., IBPEF Banco PYME Ecofuturo S.A., IIIPM Fundación Pro Mujer IFD, etc.)
- Credenciales vacías → FallaServicio (excepción `SirefoFault(mensaje, tipo_excepcion)`).

## 7. SOAP gateway (zeep)

`zeep.Client(wsdl=SIREFO_WSDL_URL)`, transport con `Session` (verify configurable
`SIREFO_TLS_VERIFY`, default true), timeout 60s. Mapear dataclasses/dicts a los tipos del WSDL por
nombre de campo. Capturar `zeep.exceptions.Fault` → `SirefoFault`. Nota en comentario: nombres
exactos de tipos pueden ajustarse al WSDL real cuando haya acceso vía SIGMA.

## 8. Frontend (React 18 + Vite, JavaScript)

`npm create vite` layout estándar. Dependencias: react-router-dom, axios. Sin librería UI:
CSS propio limpio (archivo `src/styles.css`, look institucional sobrio, sidebar + topbar,
responsive básico). Idioma de la UI: **español**.

- `src/api/client.js`: axios instance baseURL `/api` (proxy Vite → http://localhost:8000),
  interceptor que añade JWT desde localStorage y redirige a /login en 401.
- Contexto de auth (`AuthContext`): login/logout/usuario actual, guarda de rutas por rol.
- Páginas:
  - **/login** — formulario usuario/clave.
  - **/** Dashboard — tarjetas: total solicitudes, enviadas, procesadas, con error; últimos envíos;
    botón "Probar conexión (Ping)" que muestra la respuesta.
  - **/solicitudes** — tabla paginada con filtros (tipo R/S, estado, búsqueda), badge de estado
    (borrador/enviada/error_envio + estado ASFI), acciones: ver, consultar estado, reenviar.
  - **/solicitudes/nueva** — wizard: (1) cabecera (código solicitud/cite, tipo R o S, autoridad,
    cargo, gerencia, adjunto PDF con validación), (2) detalles: tabla editable para añadir N personas,
    formulario condicionado por tipo de persona (natural: nombres+apellidos+doc 2/4/5;
    jurídica: razón social+doc 1/3), extensión (combo de departamentos), tipo respaldo
    (PIET/PC/AAPA/RS), monto Bs o UFV (excluyentes), auto conclusión solo si S; (3) resumen y enviar.
  - **/solicitudes/:id** — detalle: cabecera, tabla de ítems, respuesta ASFI, circular, link al PDF,
    botones consultar estado / reenviar.
  - **/remisiones**, **/remisiones/nueva**, **/remisiones/:id** — análogas (campos remisión:
    NumeroSIREFO, identificador, cuenta, moneda, código de envío de la entidad financiera con
    combo cargado de `/api/sirefo/entidades`).
  - **/consultas** — consulta de lista de estados por fecha.
  - **/usuarios** (admin) — CRUD básico usuarios y roles.
  - **/logs** (admin) — tabla de auditoría.
- Validaciones espejo de §3 en los formularios antes de enviar; mensajes de error del backend
  mostrados en un toast/banner.

## 9. Criterios de aceptación

1. `cd backend && ./run.sh` levanta la API en :8000 con `SIREFO_MODE=mock`; `admin/admin123` puede loguearse.
2. `pytest` en backend pasa: hashes + flujo crear solicitud R → consultar estado → Procesada con circular; solicitud inválida (jurídica con tipo doc 2, ambos montos, PDF falso, duplicado) → 400/502 correctos.
3. `cd frontend && npm install && npm run dev` en :5173; flujo completo end-to-end contra el mock desde la UI.

## 10. Configuración en runtime

Los parámetros de conexión SIREFO (sección 1: modo, WSDL, credenciales ASFI, entidad,
codificación de hash, verificación TLS) pueden gestionarse también desde el panel web
(`/configuracion`, solo `admin`), sin tocar `backend/.env` ni reiniciar el proceso.

- **Modelo** `AppConfig` (`app/models.py`): fila única (`id=1`) con las mismas columnas,
  todas nullable. `None`/cadena vacía en una columna significa "sin override": se usa el
  valor de `Settings` (entorno). Sin fila `AppConfig`, el comportamiento es idéntico al de
  hoy (100% entorno) — retrocompatible.
- **Configuración efectiva** (`app/runtime_config.py`): `get_effective_config(db)` fusiona
  `Settings` (entorno) con la fila `AppConfig`, campo por campo, devolviendo un
  `EffectiveConfig` (dataclass inmutable/hashable) con `mode, wsdl_url, asfi_usuario,
  asfi_clave, entidad, hash_encoding, tls_verify`. `get_config_sources(db)` indica, por
  campo, si el valor viene de `"env"` o `"db"`.
- **Gateway y hashes**: `get_gateway(config)` (antes `get_gateway()`) recibe ahora la
  configuración efectiva y la cachea por valor (mientras no cambie, reutiliza la misma
  instancia — y por tanto el estado en memoria del mock o el cliente zeep ya construido).
  `MockSirefoGateway`/`SoapSirefoGateway` reciben `config` en su constructor. El cliente
  zeep del gateway SOAP se reconstruye si `(wsdl_url, tls_verify)` cambia desde que se
  construyó. Las funciones de `app/sirefo/hashes.py` aceptan un parámetro `encoding`
  opcional (si se omite, usan `Settings().hash_encoding`, igual que antes); los routers y
  el gateway ahora pasan siempre `config.hash_encoding`. Todos los routers que antes leían
  `get_settings()` para `entidad`/credenciales/modo llaman en su lugar a
  `get_effective_config(db)` una vez por request.
- **API** (`app/routers/config.py`, todo bajo `require_admin`):
  - `GET /api/config` → `{modo, wsdl_url, asfi_usuario, entidad, hash_encoding, tls_verify,
    asfi_clave_definida, fuente: {campo: "env"|"db", ...}}`. La clave ASFI **nunca** se
    devuelve; solo si está definida.
  - `PUT /api/config` → body con los campos opcionales de `AppConfig`. Campo ausente: no se
    toca. Campo `null` explícito: limpia el override (vuelve a usar el valor de entorno).
    `asfi_clave` ausente o `""`: se mantiene la clave ya guardada (para no borrarla sin
    querer al reenviar el formulario). Valida `modo ∈ {mock, soap}` y
    `hash_encoding ∈ {hex, HEX, base64}` → 400 si no corresponde. Responde con el mismo
    formato que el GET (upsert de la fila única).
- **Frontend** (`/configuracion`, admin, mismo guard que `/usuarios`): formulario con los
  mismos campos (WSDL solo visible en modo `soap`), una insignia por campo con su origen
  (`entorno`/`BD`), campo de clave tipo password con placeholder
  "•••••• (sin cambios)" cuando ya hay una definida, y botón "Probar conexión (Ping)" que
  reutiliza `GET /api/sirefo/ping`. El botón "Guardar cambios" envía por `PUT` solo los
  campos que el usuario tocó en esa sesión de edición.

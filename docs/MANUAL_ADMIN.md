# Manual de Administrador — SIREFO Web (G.A.M. Warnes)

Para el rol **admin**. Incluye todo lo del manual de usuario, más lo siguiente.

## 1. Instalación (demo)

```bash
git clone https://github.com/jpvargassoruco/sirefo-web.git
cd sirefo-web
docker compose up -d --build
```

Abrir http://localhost:8080 — usuario inicial `admin` / `admin123` (cámbielo de
inmediato en **Usuarios**). Alternativa sin Docker: ver README.

## 2. Usuarios y roles

**Usuarios**: crear, activar/desactivar, cambiar rol y restablecer claves.

| Rol | Permisos |
|---|---|
| consulta | Solo lectura (listados, detalles, consultas) |
| operador | Además: crear/enviar solicitudes y remisiones, consultar estado, reenviar |
| admin | Además: usuarios, configuración y auditoría |

## 3. Configuración del servicio SIREFO

**Configuración** (solo admin): credenciales ASFI (la clave nunca se vuelve a
mostrar), código de entidad, modo, codificación de hashes y TLS. Lo guardado aquí
se almacena en la base de datos y **tiene prioridad sobre `backend/.env`**; cada
campo indica su origen (env/BD). Use **Probar conexión (Ping)** tras cambiar algo.

- **Modo `mock`**: simulador local, sin conectividad con ASFI. Cualquier credencial
  no vacía sirve. Es el modo de la demo.
- **Modo `soap`**: servicio real de ASFI vía red SIGMA. Requiere credenciales con rol
  `ServicioRetenciones` (se gestionan ante ASFI por nota formal), la URL del WSDL
  (pruebas: `.../retencionesDev/ServicioRetencionFondos.svc?wsdl`) y coordinar con
  ASFI la codificación de los hashes SHA-1 (`hex`, `HEX` o `base64`).

## 4. Auditoría

**Logs**: registro de cada operación contra ASFI (quién, qué, respuesta y resultado).
Las claves nunca se registran.

## 5. Datos y respaldo

La base SQLite vive en el volumen Docker `sirefo_data`. Respaldo:

```bash
docker compose exec backend sh -c "cat /data/sirefo.db" > respaldo-$(date +%F).db
```

`docker compose down` conserva los datos; `docker compose down -v` los borra.

## 6. Paso a producción — lista de verificación

1. Credenciales ASFI reales y conectividad SIGMA verificada (`Ping` en modo `soap`
   contra el endpoint de pruebas primero).
2. Cambiar `SIREFO_JWT_SECRET` y la clave de `admin`; **sacar `backend/.env` del
   repositorio** (está versionado solo por ser demo) y volver a ignorarlo en git.
3. Servir detrás de HTTPS y restringir el acceso a la red institucional.
4. Respaldo programado del volumen de datos.

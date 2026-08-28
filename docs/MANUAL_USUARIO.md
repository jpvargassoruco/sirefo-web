# Manual de Usuario — SIREFO Web (G.A.M. Warnes)

Para roles **operador** (registra y envía) y **consulta** (solo lectura).

## 1. Ingreso

Abra la aplicación (demo: http://localhost:8080), ingrese su usuario y clave.
El menú lateral muestra solo las opciones que su rol permite.

## 2. Panel (Dashboard)

Resumen de solicitudes (totales, enviadas, procesadas, con error) y últimos envíos.
El botón **Probar conexión (Ping)** verifica que el servicio SIREFO responde.

## 3. Crear una solicitud de retención o suspensión

**Solicitudes → Nueva solicitud**. Son 3 pasos:

1. **Cabecera**: código de solicitud (cite de la nota dirigida a ASFI, único), tipo
   (**R** retención / **S** suspensión), autoridad solicitante, cargo, gerencia y la
   **nota escaneada en PDF** (solo se aceptan PDF).
2. **Detalles**: agregue una fila por cada persona:
   - *Persona natural*: nombres, al menos un apellido, documento CI/Pasaporte/CI
     extranjero, extensión (departamento; PE solo para CI/CI-extranjero).
   - *Persona jurídica*: razón social y NIT o RUC (sin nombres/apellidos).
   - Monto **en Bs o en UFV, nunca ambos**, con dos decimales.
   - Documento de respaldo y su tipo (PIET, PC, AAPA o RS).
   - *Auto de conclusión*: solo para suspensiones (tipo S).
3. **Resumen**: revise y presione **Enviar**. El sistema calcula los hashes y remite
   a ASFI; verá la respuesta (OK o el error) de inmediato.

## 4. Seguimiento

En **Solicitudes**, cada registro muestra su estado local (*enviada* / *error de envío*)
y el estado en ASFI. Acciones:

- **Consultar estado**: pregunta a ASFI; si fue procesada verá la **Carta Circular**
  y su fecha, además del número SIREFO asignado.
- **Reenviar**: solo disponible cuando el envío falló.
- En el detalle puede descargar el PDF adjunto.

## 5. Remisiones de fondos

**Remisiones → Nueva remisión**. Requiere el **Número SIREFO** de una retención ya
procesada. Complete identificador (cite), autoridad, detalle por persona con monto,
número de cuenta, moneda y la **entidad financiera** (lista oficial de ASFI), más la
nota en PDF. El seguimiento es igual que en solicitudes.

## 6. Consultas

**Consultas** permite listar los estados de envío reportados por ASFI para una fecha
(formato AAAAMMDDHHMMSS).

## Errores frecuentes

| Mensaje | Causa |
|---|---|
| Código de solicitud ya utilizado | El cite ya existe; use *Reenviar* si el envío falló |
| Monto en Bs y UFV a la vez | Informe solo uno de los dos |
| Tipo de documento no válido para el tipo de persona | NIT/RUC solo jurídicas; CI/PAS/CIE solo naturales |
| Solo se aceptan archivos PDF | El adjunto no es un PDF válido |
| SIREFO: ... (AutenticacionException) | Credenciales ASFI no configuradas — avise al administrador |

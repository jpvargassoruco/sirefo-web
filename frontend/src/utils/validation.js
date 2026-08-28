import {
  DOC_TIPOS_NATURAL,
  DOC_TIPOS_JURIDICA,
  EXTENSION_PE_TIPOS_PERMITIDOS,
} from './constants'

// Valida un ítem de detalle (solicitud o remisión) según reglas de negocio §3.
// Devuelve un objeto { campo: mensaje } con los errores encontrados.
export function validarDetallePersona(detalle, { esRemision = false } = {}) {
  const errores = {}
  const tipoPersona = detalle.tipo_persona
  const tipoDoc = Number(detalle.documento_tipo ?? detalle.tipo_documento)

  if (!tipoPersona) {
    errores.tipo_persona = 'Seleccione el tipo de persona.'
  }

  if (tipoPersona === 'natural') {
    if (tipoDoc && !DOC_TIPOS_NATURAL.includes(tipoDoc)) {
      errores.documento_tipo = 'Persona natural requiere tipo de documento 2, 4 o 5.'
    }
    if (!detalle.nombres || !detalle.nombres.trim()) {
      errores.nombres = 'Ingrese los nombres.'
    }
    if (
      (!detalle.apellido_paterno || !detalle.apellido_paterno.trim()) &&
      (!detalle.apellido_materno || !detalle.apellido_materno.trim())
    ) {
      errores.apellido_paterno = 'Ingrese al menos un apellido.'
    }
    if (detalle.razon_social && detalle.razon_social.trim()) {
      errores.razon_social = 'La razón social debe estar vacía para persona natural.'
    }
  } else if (tipoPersona === 'juridica') {
    if (tipoDoc && !DOC_TIPOS_JURIDICA.includes(tipoDoc)) {
      errores.documento_tipo = 'Persona jurídica requiere tipo de documento 1 o 3.'
    }
    if (!detalle.razon_social || !detalle.razon_social.trim()) {
      errores.razon_social = 'Ingrese la razón social.'
    }
    if (
      (detalle.nombres && detalle.nombres.trim()) ||
      (detalle.apellido_paterno && detalle.apellido_paterno.trim()) ||
      (detalle.apellido_materno && detalle.apellido_materno.trim())
    ) {
      errores.nombres = 'Nombres/apellidos deben estar vacíos para persona jurídica.'
    }
  }

  // Regla §3.2: extensión PE solo con tipos 2 y 5
  const ext = detalle.documento_extension ?? detalle.extension_documento
  if (ext === 'PE' && tipoDoc && !EXTENSION_PE_TIPOS_PERMITIDOS.includes(tipoDoc)) {
    errores.documento_extension = 'La extensión PE solo es válida para documento tipo 2 o 5.'
  }

  if (!detalle.documento_numero && !detalle.numero_documento) {
    errores.documento_numero = 'Ingrese el número de documento.'
  }

  if (!detalle.tipo_respaldo) {
    errores.tipo_respaldo = 'Seleccione el tipo de respaldo.'
  }

  if (!esRemision) {
    // Regla §3.3: monto Bs XOR UFV, nunca ambos ni ninguno
    const tieneBs = detalle.monto_bs !== null && detalle.monto_bs !== undefined && detalle.monto_bs !== ''
    const tieneUfv = detalle.monto_ufv !== null && detalle.monto_ufv !== undefined && detalle.monto_ufv !== ''
    if (tieneBs && tieneUfv) {
      errores.monto = 'Indique el monto en Bs o en UFV, no ambos.'
    } else if (!tieneBs && !tieneUfv) {
      errores.monto = 'Indique el monto en Bs o en UFV.'
    } else {
      const valor = tieneBs ? detalle.monto_bs : detalle.monto_ufv
      if (isNaN(Number(valor)) || Number(valor) <= 0) {
        errores.monto = 'El monto debe ser un número mayor a 0.'
      }
    }
  } else {
    const monto = detalle.monto_remision
    if (monto === null || monto === undefined || monto === '' || isNaN(Number(monto)) || Number(monto) <= 0) {
      errores.monto_remision = 'Indique un monto de remisión válido.'
    }
    if (!detalle.numero_cuenta || !String(detalle.numero_cuenta).trim()) {
      errores.numero_cuenta = 'Ingrese el número de cuenta.'
    }
    if (!detalle.cuenta_moneda) {
      errores.cuenta_moneda = 'Seleccione la moneda de la cuenta.'
    }
    if (!detalle.codigo_envio) {
      errores.codigo_envio = 'Seleccione la entidad (código de envío).'
    }
  }

  return errores
}

export function tieneErrores(errores) {
  return Object.keys(errores).length > 0
}

// Formato YYYYMMDDHHMISS (14 dígitos) — regla §3.4
export function fechaHoraCompacta(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return (
    date.getFullYear().toString() +
    pad(date.getMonth() + 1) +
    pad(date.getDate()) +
    pad(date.getHours()) +
    pad(date.getMinutes()) +
    pad(date.getSeconds())
  )
}

export function validarFechaCompacta(valor) {
  return /^\d{14}$/.test(valor)
}

// Regla §3.5: solo PDF, valida magic bytes %PDF
export async function validarArchivoPdf(file) {
  if (!file) {
    return { ok: false, mensaje: 'Debe adjuntar un archivo PDF.' }
  }
  if (file.type && file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
    return { ok: false, mensaje: 'El archivo debe ser un PDF.' }
  }
  try {
    const buf = await file.slice(0, 4).arrayBuffer()
    const header = String.fromCharCode(...new Uint8Array(buf))
    if (header === '%PDF') {
      return { ok: true }
    }
    return { ok: false, mensaje: 'El archivo no parece ser un PDF válido.' }
  } catch {
    return { ok: false, mensaje: 'No se pudo leer el archivo.' }
  }
}

export function validarCabeceraSolicitud(cabecera) {
  const errores = {}
  if (!cabecera.codigo_solicitud || !cabecera.codigo_solicitud.trim()) {
    errores.codigo_solicitud = 'Ingrese el código de solicitud (cite de la nota).'
  }
  if (!cabecera.tipo_proceso) {
    errores.tipo_proceso = 'Seleccione el tipo de proceso.'
  }
  if (!cabecera.autoridad_solicitante || !cabecera.autoridad_solicitante.trim()) {
    errores.autoridad_solicitante = 'Ingrese la autoridad solicitante.'
  }
  if (!cabecera.autoridad_cargo || !cabecera.autoridad_cargo.trim()) {
    errores.autoridad_cargo = 'Ingrese el cargo de la autoridad.'
  }
  if (!cabecera.gerencia || !cabecera.gerencia.trim()) {
    errores.gerencia = 'Ingrese la gerencia.'
  }
  return errores
}

export function validarCabeceraRemision(cabecera) {
  const errores = {}
  if (!cabecera.numero_sirefo || !cabecera.numero_sirefo.trim()) {
    errores.numero_sirefo = 'Ingrese el número SIREFO de la retención previa.'
  }
  if (!cabecera.identificador_remision || !cabecera.identificador_remision.trim()) {
    errores.identificador_remision = 'Ingrese el identificador de la remisión.'
  }
  if (!cabecera.autoridad_solicitante || !cabecera.autoridad_solicitante.trim()) {
    errores.autoridad_solicitante = 'Ingrese la autoridad solicitante.'
  }
  if (!cabecera.gerencia_solicitante || !cabecera.gerencia_solicitante.trim()) {
    errores.gerencia_solicitante = 'Ingrese la gerencia solicitante.'
  }
  if (!cabecera.cargo_solicitante || !cabecera.cargo_solicitante.trim()) {
    errores.cargo_solicitante = 'Ingrese el cargo del solicitante.'
  }
  return errores
}

export const TIPOS_PROCESO = [
  { value: 'R', label: 'Retención' },
  { value: 'S', label: 'Suspensión' },
]

export const TIPOS_DOCUMENTO = [
  { value: 1, label: '1 - NIT' },
  { value: 2, label: '2 - CI' },
  { value: 3, label: '3 - RUC' },
  { value: 4, label: '4 - Pasaporte' },
  { value: 5, label: '5 - CI Extranjero' },
]

// Tipos de documento permitidos por tipo de persona (regla §3.1)
export const DOC_TIPOS_NATURAL = [2, 4, 5]
export const DOC_TIPOS_JURIDICA = [1, 3]

export const TIPOS_RESPALDO = [
  { value: 1, label: '1 - PIET' },
  { value: 2, label: '2 - PC' },
  { value: 3, label: '3 - AAPA' },
  { value: 4, label: '4 - RS' },
]

// Extensión de documento: departamentos de Bolivia + PE (extranjero)
export const EXTENSIONES_DOCUMENTO = [
  { value: '', label: '(ninguna)' },
  { value: 'CH', label: 'CH - Chuquisaca' },
  { value: 'LP', label: 'LP - La Paz' },
  { value: 'CB', label: 'CB - Cochabamba' },
  { value: 'OR', label: 'OR - Oruro' },
  { value: 'PO', label: 'PO - Potosí' },
  { value: 'TJ', label: 'TJ - Tarija' },
  { value: 'SC', label: 'SC - Santa Cruz' },
  { value: 'BE', label: 'BE - Beni' },
  { value: 'PA', label: 'PA - Pando' },
  { value: 'PE', label: 'PE - Extranjero' },
]

// PE solo permitido con tipos 2 y 5 (regla §3.2)
export const EXTENSION_PE_TIPOS_PERMITIDOS = [2, 5]
// Extensión puede ser vacía para estos tipos en solicitudes
export const EXTENSION_VACIA_TIPOS_SOLICITUD = [1, 2, 3, 4]
export const EXTENSION_VACIA_TIPOS_REMISION = [1, 3, 4]

export const CUENTA_MONEDA = [
  { value: 1, label: '1 - BOB' },
  { value: 2, label: '2 - USD' },
  { value: 3, label: '3 - BOB c/MV' },
  { value: 4, label: '4 - MN con MV a UFV' },
]

export const ESTADOS_LOCAL = [
  { value: 'borrador', label: 'Borrador' },
  { value: 'enviada', label: 'Enviada' },
  { value: 'error_envio', label: 'Error de envío' },
]

export const ESTADOS_ASFI = [
  { value: 'Procesada', label: 'Procesada' },
  { value: 'No Procesada', label: 'No Procesada' },
  { value: 'Con error', label: 'Con error' },
]

export const ROLES = [
  { value: 'admin', label: 'Administrador' },
  { value: 'operador', label: 'Operador' },
  { value: 'consulta', label: 'Consulta' },
]

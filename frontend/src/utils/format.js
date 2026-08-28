export function formatFechaCompacta(valor) {
  if (!valor || valor.length !== 14) return valor || '—'
  const y = valor.slice(0, 4)
  const mo = valor.slice(4, 6)
  const d = valor.slice(6, 8)
  const h = valor.slice(8, 10)
  const mi = valor.slice(10, 12)
  const s = valor.slice(12, 14)
  return `${d}/${mo}/${y} ${h}:${mi}:${s}`
}

export function estadoLocalLabel(estado) {
  const map = {
    borrador: 'Borrador',
    enviada: 'Enviada',
    error_envio: 'Error de envío',
  }
  return map[estado] || estado || '—'
}

export function estadoLocalClass(estado) {
  const map = {
    borrador: 'badge-gray',
    enviada: 'badge-blue',
    error_envio: 'badge-red',
  }
  return map[estado] || 'badge-gray'
}

export function estadoAsfiClass(estado) {
  const map = {
    Procesada: 'badge-green',
    'No Procesada': 'badge-yellow',
    'Con error': 'badge-red',
  }
  return map[estado] || 'badge-gray'
}

export function tipoProcesoLabel(tipo) {
  return tipo === 'R' ? 'Retención' : tipo === 'S' ? 'Suspensión' : tipo || '—'
}

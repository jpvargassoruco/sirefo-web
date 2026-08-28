// Normaliza la respuesta paginada del backend. Se asume la forma:
//   { items: [...], total, page, pages, page_size }
// pero se admite también un arreglo plano o variantes comunes (results/data)
// como salvaguarda ante pequeñas diferencias en el contrato real.
export function normalizePage(data) {
  if (Array.isArray(data)) {
    return { items: data, total: data.length, page: 1, pages: 1 }
  }
  if (!data) {
    return { items: [], total: 0, page: 1, pages: 1 }
  }
  const items = data.items || data.results || data.data || []
  const total = data.total ?? data.count ?? items.length
  const page = data.page ?? 1
  const pages = data.pages ?? (data.page_size ? Math.max(1, Math.ceil(total / data.page_size)) : 1)
  return { items, total, page, pages }
}

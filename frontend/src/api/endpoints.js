import client from './client'

// --- Auth ---
export const authApi = {
  login: (username, password) => client.post('/auth/login', { username, password }),
  me: () => client.get('/auth/me'),
}

// --- Usuarios (admin) ---
export const usersApi = {
  list: () => client.get('/users'),
  create: (data) => client.post('/users', data),
  patch: (id, data) => client.patch(`/users/${id}`, data),
}

// --- SIREFO utilidades ---
export const sirefoApi = {
  ping: (texto) => client.get('/sirefo/ping', { params: { texto } }),
  entidades: () => client.get('/sirefo/entidades'),
  maxIdSolicitud: () => client.get('/sirefo/max-id-solicitud'),
}

// --- Configuración de conexión SIREFO (admin) ---
export const configApi = {
  get: () => client.get('/config'),
  update: (data) => client.put('/config', data),
}

// --- Solicitudes ---
export const solicitudesApi = {
  list: (params) => client.get('/solicitudes', { params }),
  get: (id) => client.get(`/solicitudes/${id}`),
  create: (data, adjunto) => {
    const form = new FormData()
    form.append('data', JSON.stringify(data))
    if (adjunto) form.append('adjunto', adjunto)
    return client.post('/solicitudes', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  adjuntoUrl: (id) => `/api/solicitudes/${id}/adjunto`,
  reenviar: (id) => client.post(`/solicitudes/${id}/reenviar`),
  consultarEstado: (id) => client.post(`/solicitudes/${id}/consultar-estado`),
}

// --- Remisiones ---
export const remisionesApi = {
  list: (params) => client.get('/remisiones', { params }),
  get: (id) => client.get(`/remisiones/${id}`),
  create: (data, adjunto) => {
    const form = new FormData()
    form.append('data', JSON.stringify(data))
    if (adjunto) form.append('adjunto', adjunto)
    return client.post('/remisiones', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  adjuntoUrl: (id) => `/api/remisiones/${id}/adjunto`,
  reenviar: (id) => client.post(`/remisiones/${id}/reenviar`),
  consultarEstado: (id) => client.post(`/remisiones/${id}/consultar-estado`),
}

// --- Consultas ---
export const consultasApi = {
  listaEstado: (fecha) => client.get('/consultas/lista-estado', { params: { fecha } }),
}

// --- Logs (admin) ---
export const logsApi = {
  list: (page) => client.get('/logs', { params: { page } }),
}

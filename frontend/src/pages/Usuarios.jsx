import { useCallback, useEffect, useState } from 'react'
import { usersApi } from '../api/endpoints'
import { useToast } from '../context/ToastContext'
import Badge from '../components/Badge'
import Modal from '../components/Modal'
import { ROLES } from '../utils/constants'

const NUEVO_USUARIO = { username: '', full_name: '', password: '', role: 'operador' }

export default function Usuarios() {
  const { showError, showSuccess } = useToast()
  const [usuarios, setUsuarios] = useState([])
  const [loading, setLoading] = useState(true)

  const [modalCrear, setModalCrear] = useState(false)
  const [nuevo, setNuevo] = useState(NUEVO_USUARIO)
  const [erroresNuevo, setErroresNuevo] = useState({})
  const [creando, setCreando] = useState(false)

  const [editando, setEditando] = useState(null) // usuario en edición
  const [formEdicion, setFormEdicion] = useState({ role: '', is_active: true, password: '' })
  const [guardando, setGuardando] = useState(false)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const res = await usersApi.list()
      const data = Array.isArray(res.data) ? res.data : res.data.items || []
      setUsuarios(data)
    } catch (err) {
      showError(err)
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    cargar()
  }, [cargar])

  const abrirCrear = () => {
    setNuevo(NUEVO_USUARIO)
    setErroresNuevo({})
    setModalCrear(true)
  }

  const validarNuevo = () => {
    const err = {}
    if (!nuevo.username.trim()) err.username = 'Ingrese el usuario.'
    if (!nuevo.full_name.trim()) err.full_name = 'Ingrese el nombre completo.'
    if (!nuevo.password || nuevo.password.length < 6) err.password = 'La contraseña debe tener al menos 6 caracteres.'
    if (!nuevo.role) err.role = 'Seleccione un rol.'
    return err
  }

  const crearUsuario = async () => {
    const err = validarNuevo()
    setErroresNuevo(err)
    if (Object.keys(err).length > 0) return
    setCreando(true)
    try {
      await usersApi.create(nuevo)
      showSuccess('Usuario creado correctamente.')
      setModalCrear(false)
      await cargar()
    } catch (err2) {
      showError(err2)
    } finally {
      setCreando(false)
    }
  }

  const abrirEdicion = (usuario) => {
    setEditando(usuario)
    setFormEdicion({ role: usuario.role, is_active: usuario.is_active, password: '' })
  }

  const guardarEdicion = async () => {
    setGuardando(true)
    try {
      const payload = { role: formEdicion.role, is_active: formEdicion.is_active }
      if (formEdicion.password) payload.password = formEdicion.password
      await usersApi.patch(editando.id, payload)
      showSuccess('Usuario actualizado correctamente.')
      setEditando(null)
      await cargar()
    } catch (err) {
      showError(err)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Usuarios</h1>
        <button className="btn btn-primary" onClick={abrirCrear}>
          + Nuevo usuario
        </button>
      </div>

      <div className="panel">
        {loading && <p className="empty-hint">Cargando…</p>}
        {!loading && usuarios.length === 0 && <p className="empty-hint">No hay usuarios registrados.</p>}
        {!loading && usuarios.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Nombre completo</th>
                <th>Rol</th>
                <th>Activo</th>
                <th>Creado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td>{u.full_name}</td>
                  <td>
                    <span className={`role-pill role-${u.role}`}>{u.role}</span>
                  </td>
                  <td>
                    <Badge text={u.is_active ? 'Activo' : 'Inactivo'} className={u.is_active ? 'badge-green' : 'badge-red'} />
                  </td>
                  <td>{u.created_at ? new Date(u.created_at).toLocaleString('es-BO') : '—'}</td>
                  <td className="actions-cell">
                    <button className="link-action" onClick={() => abrirEdicion(u)}>
                      Editar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modalCrear && (
        <Modal
          title="Nuevo usuario"
          onClose={() => setModalCrear(false)}
          footer={
            <>
              <button className="btn btn-ghost" onClick={() => setModalCrear(false)}>
                Cancelar
              </button>
              <button className="btn btn-primary" onClick={crearUsuario} disabled={creando}>
                {creando ? 'Creando…' : 'Crear'}
              </button>
            </>
          }
        >
          <label className="field">
            <span>Usuario</span>
            <input type="text" value={nuevo.username} onChange={(e) => setNuevo({ ...nuevo, username: e.target.value })} />
            {erroresNuevo.username && <span className="field-error">{erroresNuevo.username}</span>}
          </label>
          <label className="field">
            <span>Nombre completo</span>
            <input
              type="text"
              value={nuevo.full_name}
              onChange={(e) => setNuevo({ ...nuevo, full_name: e.target.value })}
            />
            {erroresNuevo.full_name && <span className="field-error">{erroresNuevo.full_name}</span>}
          </label>
          <label className="field">
            <span>Contraseña</span>
            <input
              type="password"
              value={nuevo.password}
              onChange={(e) => setNuevo({ ...nuevo, password: e.target.value })}
            />
            {erroresNuevo.password && <span className="field-error">{erroresNuevo.password}</span>}
          </label>
          <label className="field">
            <span>Rol</span>
            <select value={nuevo.role} onChange={(e) => setNuevo({ ...nuevo, role: e.target.value })}>
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
        </Modal>
      )}

      {editando && (
        <Modal
          title={`Editar usuario: ${editando.username}`}
          onClose={() => setEditando(null)}
          footer={
            <>
              <button className="btn btn-ghost" onClick={() => setEditando(null)}>
                Cancelar
              </button>
              <button className="btn btn-primary" onClick={guardarEdicion} disabled={guardando}>
                {guardando ? 'Guardando…' : 'Guardar'}
              </button>
            </>
          }
        >
          <label className="field">
            <span>Rol</span>
            <select value={formEdicion.role} onChange={(e) => setFormEdicion({ ...formEdicion, role: e.target.value })}>
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field field-checkbox">
            <input
              type="checkbox"
              checked={formEdicion.is_active}
              onChange={(e) => setFormEdicion({ ...formEdicion, is_active: e.target.checked })}
            />
            <span>Usuario activo</span>
          </label>
          <label className="field">
            <span>Nueva contraseña (opcional)</span>
            <input
              type="password"
              value={formEdicion.password}
              onChange={(e) => setFormEdicion({ ...formEdicion, password: e.target.value })}
              placeholder="Dejar en blanco para no cambiar"
            />
          </label>
        </Modal>
      )}
    </div>
  )
}

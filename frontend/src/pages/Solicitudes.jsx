import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { solicitudesApi } from '../api/endpoints'
import { normalizePage } from '../utils/pagination'
import { useToast } from '../context/ToastContext'
import { useAuth } from '../context/AuthContext'
import Badge from '../components/Badge'
import Pagination from '../components/Pagination'
import { estadoLocalLabel, estadoLocalClass, estadoAsfiClass, tipoProcesoLabel, formatFechaCompacta } from '../utils/format'
import { TIPOS_PROCESO, ESTADOS_LOCAL } from '../utils/constants'

export default function Solicitudes() {
  const { showError } = useToast()
  const { user } = useAuth()
  const puedeOperar = user?.role === 'admin' || user?.role === 'operador'

  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [tipo, setTipo] = useState('')
  const [estado, setEstado] = useState('')
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(null)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page }
      if (tipo) params.tipo = tipo
      if (estado) params.estado = estado
      if (q) params.q = q
      const res = await solicitudesApi.list(params)
      const norm = normalizePage(res.data)
      setItems(norm.items)
      setPages(norm.pages || 1)
    } catch (err) {
      showError(err)
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, tipo, estado, q])

  useEffect(() => {
    cargar()
  }, [cargar])

  const onFiltrar = (e) => {
    e.preventDefault()
    setPage(1)
    cargar()
  }

  const consultarEstado = async (id) => {
    setBusy(id)
    try {
      await solicitudesApi.consultarEstado(id)
      await cargar()
    } catch (err) {
      showError(err)
    } finally {
      setBusy(null)
    }
  }

  const reenviar = async (id) => {
    setBusy(id)
    try {
      await solicitudesApi.reenviar(id)
      await cargar()
    } catch (err) {
      showError(err)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Solicitudes</h1>
        {puedeOperar && (
          <Link className="btn btn-primary" to="/solicitudes/nueva">
            + Nueva solicitud
          </Link>
        )}
      </div>

      <form className="filter-bar" onSubmit={onFiltrar}>
        <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="">Todos los tipos</option>
          {TIPOS_PROCESO.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <select value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS_LOCAL.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Buscar por código, autoridad…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button className="btn btn-secondary" type="submit">
          Filtrar
        </button>
      </form>

      <div className="panel">
        {loading && <p className="empty-hint">Cargando…</p>}
        {!loading && items.length === 0 && <p className="empty-hint">No se encontraron solicitudes.</p>}
        {!loading && items.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Código</th>
                <th>Tipo</th>
                <th>Autoridad</th>
                <th>Estado</th>
                <th>Estado ASFI</th>
                <th>Fecha envío</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id}>
                  <td>{s.id_solicitud ?? s.id}</td>
                  <td>{s.codigo_solicitud}</td>
                  <td>{tipoProcesoLabel(s.tipo_proceso)}</td>
                  <td>{s.autoridad_solicitante}</td>
                  <td>
                    <Badge text={estadoLocalLabel(s.estado_local)} className={estadoLocalClass(s.estado_local)} />
                  </td>
                  <td>
                    <Badge text={s.estado_asfi} className={estadoAsfiClass(s.estado_asfi)} />
                  </td>
                  <td>{formatFechaCompacta(s.fecha_envio)}</td>
                  <td className="actions-cell">
                    <Link className="link-action" to={`/solicitudes/${s.id}`}>
                      Ver
                    </Link>
                    {puedeOperar && (
                      <>
                        <button
                          className="link-action"
                          disabled={busy === s.id}
                          onClick={() => consultarEstado(s.id)}
                        >
                          Consultar estado
                        </button>
                        {s.estado_local === 'error_envio' && (
                          <button className="link-action" disabled={busy === s.id} onClick={() => reenviar(s.id)}>
                            Reenviar
                          </button>
                        )}
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <Pagination page={page} totalPages={pages} onChange={setPage} />
      </div>
    </div>
  )
}

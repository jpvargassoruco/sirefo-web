import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { remisionesApi } from '../api/endpoints'
import { normalizePage } from '../utils/pagination'
import { useToast } from '../context/ToastContext'
import { useAuth } from '../context/AuthContext'
import Badge from '../components/Badge'
import Pagination from '../components/Pagination'
import { estadoLocalLabel, estadoLocalClass, formatFechaCompacta } from '../utils/format'
import { ESTADOS_LOCAL } from '../utils/constants'

export default function Remisiones() {
  const { showError } = useToast()
  const { user } = useAuth()
  const puedeOperar = user?.role === 'admin' || user?.role === 'operador'

  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [estado, setEstado] = useState('')
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(null)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page }
      if (estado) params.estado = estado
      if (q) params.q = q
      const res = await remisionesApi.list(params)
      const norm = normalizePage(res.data)
      setItems(norm.items)
      setPages(norm.pages || 1)
    } catch (err) {
      showError(err)
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, estado, q])

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
      await remisionesApi.consultarEstado(id)
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
      await remisionesApi.reenviar(id)
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
        <h1 className="page-title">Remisiones de fondos</h1>
        {puedeOperar && (
          <Link className="btn btn-primary" to="/remisiones/nueva">
            + Nueva remisión
          </Link>
        )}
      </div>

      <form className="filter-bar" onSubmit={onFiltrar}>
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
          placeholder="Buscar por identificador…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button className="btn btn-secondary" type="submit">
          Filtrar
        </button>
      </form>

      <div className="panel">
        {loading && <p className="empty-hint">Cargando…</p>}
        {!loading && items.length === 0 && <p className="empty-hint">No se encontraron remisiones.</p>}
        {!loading && items.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Número SIREFO</th>
                <th>Identificador</th>
                <th>Autoridad</th>
                <th>Estado</th>
                <th>Fecha emisión</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id}>
                  <td>{r.id_remision ?? r.id}</td>
                  <td>{r.numero_sirefo}</td>
                  <td>{r.identificador_remision}</td>
                  <td>{r.autoridad_solicitante}</td>
                  <td>
                    <Badge text={estadoLocalLabel(r.estado_local)} className={estadoLocalClass(r.estado_local)} />
                  </td>
                  <td>{formatFechaCompacta(r.fecha_hora_emision)}</td>
                  <td className="actions-cell">
                    <Link className="link-action" to={`/remisiones/${r.id}`}>
                      Ver
                    </Link>
                    {puedeOperar && (
                      <>
                        <button className="link-action" disabled={busy === r.id} onClick={() => consultarEstado(r.id)}>
                          Consultar estado
                        </button>
                        {r.estado_local === 'error_envio' && (
                          <button className="link-action" disabled={busy === r.id} onClick={() => reenviar(r.id)}>
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

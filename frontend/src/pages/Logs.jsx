import { useCallback, useEffect, useState } from 'react'
import { logsApi } from '../api/endpoints'
import { normalizePage } from '../utils/pagination'
import { useToast } from '../context/ToastContext'
import Badge from '../components/Badge'
import Pagination from '../components/Pagination'

export default function Logs() {
  const { showError } = useToast()
  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const res = await logsApi.list(page)
      const norm = normalizePage(res.data)
      setItems(norm.items)
      setPages(norm.pages || 1)
    } catch (err) {
      showError(err)
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  useEffect(() => {
    cargar()
  }, [cargar])

  return (
    <div>
      <h1 className="page-title">Auditoría de envíos</h1>

      <div className="panel">
        {loading && <p className="empty-hint">Cargando…</p>}
        {!loading && items.length === 0 && <p className="empty-hint">No hay registros de auditoría.</p>}
        {!loading && items.length > 0 && (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Usuario</th>
                  <th>Operación</th>
                  <th>Resultado</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {items.map((log) => (
                  <tr key={log.id}>
                    <td>{log.ts ? new Date(log.ts).toLocaleString('es-BO') : '—'}</td>
                    <td>{log.usuario}</td>
                    <td>{log.operacion}</td>
                    <td>
                      <Badge text={log.exito ? 'Éxito' : 'Error'} className={log.exito ? 'badge-green' : 'badge-red'} />
                    </td>
                    <td className="log-detail-cell" title={log.respuesta}>
                      {log.respuesta}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} totalPages={pages} onChange={setPage} />
      </div>
    </div>
  )
}

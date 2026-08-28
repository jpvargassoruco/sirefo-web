import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { solicitudesApi, sirefoApi } from '../api/endpoints'
import { normalizePage } from '../utils/pagination'
import { useToast } from '../context/ToastContext'
import Card from '../components/Card'
import Badge from '../components/Badge'
import { estadoLocalLabel, estadoLocalClass, estadoAsfiClass, tipoProcesoLabel, formatFechaCompacta } from '../utils/format'

const MAX_PAGES_TO_SCAN = 25

export default function Dashboard() {
  const { showError } = useToast()
  const [loadingStats, setLoadingStats] = useState(true)
  const [stats, setStats] = useState({ total: 0, enviadas: 0, procesadas: 0, conError: 0 })
  const [ultimos, setUltimos] = useState([])
  const [pingTexto, setPingTexto] = useState('SIREFO')
  const [pingResultado, setPingResultado] = useState(null)
  const [pingCargando, setPingCargando] = useState(false)

  useEffect(() => {
    let cancelado = false

    async function cargar() {
      setLoadingStats(true)
      try {
        const first = await solicitudesApi.list({ page: 1 })
        const firstPage = normalizePage(first.data)
        let items = [...firstPage.items]

        const totalPages = Math.min(firstPage.pages || 1, MAX_PAGES_TO_SCAN)
        const pendientes = []
        for (let p = 2; p <= totalPages; p++) {
          pendientes.push(solicitudesApi.list({ page: p }))
        }
        if (pendientes.length > 0) {
          const resto = await Promise.all(pendientes)
          resto.forEach((r) => {
            items = items.concat(normalizePage(r.data).items)
          })
        }

        if (cancelado) return

        const enviadas = items.filter((s) => s.estado_local === 'enviada').length
        const procesadas = items.filter((s) => s.estado_asfi === 'Procesada').length
        const conError = items.filter((s) => s.estado_local === 'error_envio' || s.estado_asfi === 'Con error').length

        setStats({
          total: firstPage.total ?? items.length,
          enviadas,
          procesadas,
          conError,
        })
        setUltimos(items.slice(0, 8))
      } catch (err) {
        if (!cancelado) showError(err)
      } finally {
        if (!cancelado) setLoadingStats(false)
      }
    }

    cargar()
    return () => {
      cancelado = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const probarPing = async () => {
    setPingCargando(true)
    setPingResultado(null)
    try {
      const res = await sirefoApi.ping(pingTexto)
      setPingResultado(res.data.respuesta ?? JSON.stringify(res.data))
    } catch (err) {
      showError(err)
      setPingResultado(null)
    } finally {
      setPingCargando(false)
    }
  }

  return (
    <div>
      <h1 className="page-title">Panel</h1>

      <div className="stat-grid">
        <Card title="Total de solicitudes" value={loadingStats ? '…' : stats.total} />
        <Card title="Enviadas" value={loadingStats ? '…' : stats.enviadas} tone="info" />
        <Card title="Procesadas (ASFI)" value={loadingStats ? '…' : stats.procesadas} tone="success" />
        <Card title="Con error" value={loadingStats ? '…' : stats.conError} tone="danger" />
      </div>

      <div className="panel-grid">
        <section className="panel">
          <h2 className="panel-title">Últimos envíos</h2>
          {ultimos.length === 0 && !loadingStats && <p className="empty-hint">Aún no hay solicitudes registradas.</p>}
          {ultimos.length > 0 && (
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Código</th>
                  <th>Tipo</th>
                  <th>Estado</th>
                  <th>Estado ASFI</th>
                  <th>Fecha envío</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {ultimos.map((s) => (
                  <tr key={s.id}>
                    <td>{s.id_solicitud ?? s.id}</td>
                    <td>{s.codigo_solicitud}</td>
                    <td>{tipoProcesoLabel(s.tipo_proceso)}</td>
                    <td>
                      <Badge text={estadoLocalLabel(s.estado_local)} className={estadoLocalClass(s.estado_local)} />
                    </td>
                    <td>
                      <Badge text={s.estado_asfi} className={estadoAsfiClass(s.estado_asfi)} />
                    </td>
                    <td>{formatFechaCompacta(s.fecha_envio)}</td>
                    <td>
                      <Link className="link-action" to={`/solicitudes/${s.id}`}>
                        Ver
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="panel">
          <h2 className="panel-title">Probar conexión (Ping)</h2>
          <p className="panel-hint">Verifica la disponibilidad del servicio SIREFO en el modo configurado.</p>
          <div className="ping-form">
            <input
              type="text"
              value={pingTexto}
              onChange={(e) => setPingTexto(e.target.value)}
              placeholder="Texto de eco"
            />
            <button className="btn btn-primary" onClick={probarPing} disabled={pingCargando}>
              {pingCargando ? 'Probando…' : 'Probar conexión'}
            </button>
          </div>
          {pingResultado && (
            <div className="ping-result">
              <strong>Respuesta:</strong> {pingResultado}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

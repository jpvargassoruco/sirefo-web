import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { solicitudesApi } from '../api/endpoints'
import { useToast } from '../context/ToastContext'
import { useAuth } from '../context/AuthContext'
import Badge from '../components/Badge'
import { estadoLocalLabel, estadoLocalClass, estadoAsfiClass, tipoProcesoLabel, formatFechaCompacta } from '../utils/format'
import { TIPOS_DOCUMENTO, TIPOS_RESPALDO } from '../utils/constants'

function labelDe(lista, valor) {
  const item = lista.find((i) => i.value === Number(valor))
  return item ? item.label : valor
}

export default function SolicitudDetalle() {
  const { id } = useParams()
  const { showError, showSuccess } = useToast()
  const { user } = useAuth()
  const puedeOperar = user?.role === 'admin' || user?.role === 'operador'

  const [solicitud, setSolicitud] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const res = await solicitudesApi.get(id)
      setSolicitud(res.data)
    } catch (err) {
      showError(err)
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    cargar()
  }, [cargar])

  const consultarEstado = async () => {
    setBusy(true)
    try {
      const res = await solicitudesApi.consultarEstado(id)
      setSolicitud(res.data)
      showSuccess('Estado actualizado.')
    } catch (err) {
      showError(err)
    } finally {
      setBusy(false)
    }
  }

  const reenviar = async () => {
    setBusy(true)
    try {
      const res = await solicitudesApi.reenviar(id)
      setSolicitud(res.data)
      showSuccess('Solicitud reenviada.')
    } catch (err) {
      showError(err)
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <p className="empty-hint">Cargando…</p>
  if (!solicitud) return <p className="empty-hint">No se encontró la solicitud.</p>

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Solicitud {solicitud.codigo_solicitud}</h1>
        <Link className="btn btn-secondary" to="/solicitudes">
          Volver
        </Link>
      </div>

      <section className="panel">
        <h2 className="panel-title">Cabecera</h2>
        <dl className="detail-grid">
          <div>
            <dt>ID Solicitud</dt>
            <dd>{solicitud.id_solicitud}</dd>
          </div>
          <div>
            <dt>Código / Cite</dt>
            <dd>{solicitud.codigo_solicitud}</dd>
          </div>
          <div>
            <dt>Tipo de proceso</dt>
            <dd>{tipoProcesoLabel(solicitud.tipo_proceso)}</dd>
          </div>
          <div>
            <dt>Autoridad solicitante</dt>
            <dd>{solicitud.autoridad_solicitante}</dd>
          </div>
          <div>
            <dt>Cargo</dt>
            <dd>{solicitud.autoridad_cargo}</dd>
          </div>
          <div>
            <dt>Gerencia</dt>
            <dd>{solicitud.gerencia}</dd>
          </div>
          <div>
            <dt>Usuario de registro</dt>
            <dd>{solicitud.usuario_registro}</dd>
          </div>
          <div>
            <dt>Fecha de envío</dt>
            <dd>{formatFechaCompacta(solicitud.fecha_envio)}</dd>
          </div>
          <div>
            <dt>Estado local</dt>
            <dd>
              <Badge text={estadoLocalLabel(solicitud.estado_local)} className={estadoLocalClass(solicitud.estado_local)} />
            </dd>
          </div>
          <div>
            <dt>Estado ASFI</dt>
            <dd>
              <Badge text={solicitud.estado_asfi} className={estadoAsfiClass(solicitud.estado_asfi)} />
            </dd>
          </div>
          <div>
            <dt>Circular</dt>
            <dd>{solicitud.circular || '—'}</dd>
          </div>
          <div>
            <dt>Fecha circular</dt>
            <dd>{formatFechaCompacta(solicitud.fecha_circular) || '—'}</dd>
          </div>
          <div>
            <dt>Adjunto</dt>
            <dd>
              {solicitud.adjunto_nombre ? (
                <a className="link-action" href={solicitudesApi.adjuntoUrl(id)} target="_blank" rel="noreferrer">
                  {solicitud.adjunto_nombre}
                </a>
              ) : (
                '—'
              )}
            </dd>
          </div>
        </dl>

        {solicitud.error_envio_asfi && (
          <div className="alert alert-error">
            <strong>Error de envío ASFI:</strong> {solicitud.error_envio_asfi}
          </div>
        )}
        {solicitud.respuesta_detalle && (
          <div className="alert alert-info">
            <strong>Respuesta ASFI:</strong> {solicitud.respuesta_detalle}
            {solicitud.respuesta_codigo !== null && solicitud.respuesta_codigo !== undefined && (
              <> (código {solicitud.respuesta_codigo})</>
            )}
          </div>
        )}

        {puedeOperar && (
          <div className="action-bar">
            <button className="btn btn-secondary" disabled={busy} onClick={consultarEstado}>
              Consultar estado
            </button>
            {solicitud.estado_local === 'error_envio' && (
              <button className="btn btn-primary" disabled={busy} onClick={reenviar}>
                Reenviar
              </button>
            )}
          </div>
        )}
      </section>

      <section className="panel">
        <h2 className="panel-title">Detalle de ítems</h2>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Tipo persona</th>
                <th>Nombre / Razón social</th>
                <th>Documento</th>
                <th>Ext.</th>
                <th>Respaldo</th>
                <th>Monto Bs</th>
                <th>Monto UFV</th>
                {solicitud.tipo_proceso === 'S' && <th>Auto conclusión</th>}
              </tr>
            </thead>
            <tbody>
              {(solicitud.detalles || []).map((d) => (
                <tr key={d.id ?? d.item}>
                  <td>{d.item}</td>
                  <td>{d.tipo_persona === 'natural' ? 'Natural' : 'Jurídica'}</td>
                  <td>
                    {d.tipo_persona === 'natural'
                      ? `${d.nombres || ''} ${d.apellido_paterno || ''} ${d.apellido_materno || ''}`.trim()
                      : d.razon_social}
                  </td>
                  <td>
                    {labelDe(TIPOS_DOCUMENTO, d.documento_tipo)} — {d.documento_numero}
                    {d.documento_complemento ? `-${d.documento_complemento}` : ''}
                  </td>
                  <td>{d.documento_extension || '—'}</td>
                  <td>{labelDe(TIPOS_RESPALDO, d.tipo_respaldo)}</td>
                  <td>{d.monto_bs ?? '—'}</td>
                  <td>{d.monto_ufv ?? '—'}</td>
                  {solicitud.tipo_proceso === 'S' && <td>{d.auto_conclusion || '—'}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

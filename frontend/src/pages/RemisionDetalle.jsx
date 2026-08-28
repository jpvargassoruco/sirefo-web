import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { remisionesApi } from '../api/endpoints'
import { useToast } from '../context/ToastContext'
import { useAuth } from '../context/AuthContext'
import Badge from '../components/Badge'
import { estadoLocalLabel, estadoLocalClass, formatFechaCompacta } from '../utils/format'
import { TIPOS_DOCUMENTO, TIPOS_RESPALDO, CUENTA_MONEDA } from '../utils/constants'

function labelDe(lista, valor) {
  const item = lista.find((i) => Number(i.value) === Number(valor))
  return item ? item.label : valor
}

export default function RemisionDetalle() {
  const { id } = useParams()
  const { showError, showSuccess } = useToast()
  const { user } = useAuth()
  const puedeOperar = user?.role === 'admin' || user?.role === 'operador'

  const [remision, setRemision] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const res = await remisionesApi.get(id)
      setRemision(res.data)
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
      const res = await remisionesApi.consultarEstado(id)
      setRemision(res.data)
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
      const res = await remisionesApi.reenviar(id)
      setRemision(res.data)
      showSuccess('Remisión reenviada.')
    } catch (err) {
      showError(err)
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <p className="empty-hint">Cargando…</p>
  if (!remision) return <p className="empty-hint">No se encontró la remisión.</p>

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Remisión {remision.identificador_remision}</h1>
        <Link className="btn btn-secondary" to="/remisiones">
          Volver
        </Link>
      </div>

      <section className="panel">
        <h2 className="panel-title">Cabecera</h2>
        <dl className="detail-grid">
          <div>
            <dt>ID Remisión</dt>
            <dd>{remision.id_remision}</dd>
          </div>
          <div>
            <dt>Número SIREFO</dt>
            <dd>{remision.numero_sirefo}</dd>
          </div>
          <div>
            <dt>Identificador</dt>
            <dd>{remision.identificador_remision}</dd>
          </div>
          <div>
            <dt>Autoridad solicitante</dt>
            <dd>{remision.autoridad_solicitante}</dd>
          </div>
          <div>
            <dt>Gerencia</dt>
            <dd>{remision.gerencia_solicitante}</dd>
          </div>
          <div>
            <dt>Cargo</dt>
            <dd>{remision.cargo_solicitante}</dd>
          </div>
          <div>
            <dt>Usuario de registro</dt>
            <dd>{remision.usuario_registro}</dd>
          </div>
          <div>
            <dt>Fecha de emisión</dt>
            <dd>{formatFechaCompacta(remision.fecha_hora_emision)}</dd>
          </div>
          <div>
            <dt>Estado local</dt>
            <dd>
              <Badge text={estadoLocalLabel(remision.estado_local)} className={estadoLocalClass(remision.estado_local)} />
            </dd>
          </div>
          <div>
            <dt>Adjunto</dt>
            <dd>
              {remision.adjunto_nombre ? (
                <a className="link-action" href={remisionesApi.adjuntoUrl(id)} target="_blank" rel="noreferrer">
                  {remision.adjunto_nombre}
                </a>
              ) : (
                '—'
              )}
            </dd>
          </div>
        </dl>

        {remision.respuesta_detalle && (
          <div className="alert alert-info">
            <strong>Respuesta ASFI:</strong> {remision.respuesta_detalle}
            {remision.respuesta_codigo !== null && remision.respuesta_codigo !== undefined && (
              <> (código {remision.respuesta_codigo})</>
            )}
          </div>
        )}

        {puedeOperar && (
          <div className="action-bar">
            <button className="btn btn-secondary" disabled={busy} onClick={consultarEstado}>
              Consultar estado
            </button>
            {remision.estado_local === 'error_envio' && (
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
                <th>Respaldo</th>
                <th>Monto</th>
                <th>Cuenta</th>
                <th>Moneda</th>
                <th>Cód. envío</th>
              </tr>
            </thead>
            <tbody>
              {(remision.detalles || []).map((d) => (
                <tr key={d.id ?? d.item}>
                  <td>{d.item}</td>
                  <td>{d.tipo_persona === 'natural' ? 'Natural' : 'Jurídica'}</td>
                  <td>
                    {d.tipo_persona === 'natural'
                      ? `${d.nombres || ''} ${d.apellido_paterno || ''} ${d.apellido_materno || ''}`.trim()
                      : d.razon_social}
                  </td>
                  <td>
                    {labelDe(TIPOS_DOCUMENTO, d.tipo_documento)} — {d.numero_documento}
                    {d.documento_complemento ? `-${d.documento_complemento}` : ''}
                  </td>
                  <td>{labelDe(TIPOS_RESPALDO, d.tipo_respaldo)}</td>
                  <td>{d.monto_remision}</td>
                  <td>{d.numero_cuenta}</td>
                  <td>{labelDe(CUENTA_MONEDA, d.cuenta_moneda)}</td>
                  <td>{d.codigo_envio}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

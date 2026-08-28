import { useState } from 'react'
import { consultasApi } from '../api/endpoints'
import { useToast } from '../context/ToastContext'
import { validarFechaCompacta, fechaHoraCompacta } from '../utils/validation'
import { formatFechaCompacta } from '../utils/format'

export default function Consultas() {
  const { showError } = useToast()
  const [fecha, setFecha] = useState(fechaHoraCompacta())
  const [errorFecha, setErrorFecha] = useState('')
  const [resultados, setResultados] = useState(null)
  const [buscando, setBuscando] = useState(false)
  const [buscado, setBuscado] = useState(false)

  const buscar = async (e) => {
    e.preventDefault()
    if (!validarFechaCompacta(fecha)) {
      setErrorFecha('La fecha debe tener el formato YYYYMMDDHHMISS (14 dígitos).')
      return
    }
    setErrorFecha('')
    setBuscando(true)
    setBuscado(false)
    try {
      const res = await consultasApi.listaEstado(fecha)
      const data = res.data
      const lista = Array.isArray(data) ? data : data.items || data.lista || []
      setResultados(lista)
    } catch (err) {
      showError(err)
      setResultados(null)
    } finally {
      setBuscando(false)
      setBuscado(true)
    }
  }

  return (
    <div>
      <h1 className="page-title">Consulta de lista de estados</h1>

      <section className="panel">
        <form className="filter-bar" onSubmit={buscar}>
          <label className="field field-inline">
            <span>Fecha de envío</span>
            <input
              type="text"
              placeholder="YYYYMMDDHHMISS"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              maxLength={14}
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={buscando}>
            {buscando ? 'Consultando…' : 'Consultar'}
          </button>
        </form>
        {errorFecha && <span className="field-error">{errorFecha}</span>}
      </section>

      <section className="panel">
        <h2 className="panel-title">Resultados</h2>
        {buscando && <p className="empty-hint">Consultando…</p>}
        {!buscando && buscado && (!resultados || resultados.length === 0) && (
          <p className="empty-hint">No se encontraron resultados para la fecha indicada.</p>
        )}
        {!buscando && resultados && resultados.length > 0 && (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID Solicitud</th>
                  <th>Tipo</th>
                  <th>Estado</th>
                  <th>Circular</th>
                  <th>Fecha circular</th>
                  <th>Error de envío</th>
                </tr>
              </thead>
              <tbody>
                {resultados.map((r, idx) => (
                  <tr key={idx}>
                    <td>{r.cIDSolicitud ?? r.id_solicitud ?? '—'}</td>
                    <td>{r.cTipo ?? r.tipo ?? '—'}</td>
                    <td>{r.Estado ?? r.estado ?? '—'}</td>
                    <td>{r.Circular ?? r.circular ?? '—'}</td>
                    <td>{formatFechaCompacta(r.FechaCircular ?? r.fecha_circular)}</td>
                    <td>{r.ErrorEnvio ?? r.error_envio ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

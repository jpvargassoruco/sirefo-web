import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { solicitudesApi } from '../api/endpoints'
import { useToast } from '../context/ToastContext'
import {
  TIPOS_PROCESO,
  TIPOS_DOCUMENTO,
  TIPOS_RESPALDO,
  EXTENSIONES_DOCUMENTO,
  DOC_TIPOS_NATURAL,
  DOC_TIPOS_JURIDICA,
} from '../utils/constants'
import { validarCabeceraSolicitud, validarDetallePersona, tieneErrores, validarArchivoPdf } from '../utils/validation'

const ITEM_VACIO = {
  tipo_persona: 'natural',
  nombres: '',
  apellido_paterno: '',
  apellido_materno: '',
  razon_social: '',
  documento_tipo: '',
  documento_numero: '',
  documento_complemento: '',
  documento_extension: '',
  documento_respaldo: '',
  tipo_respaldo: '',
  monto_bs: '',
  monto_ufv: '',
  auto_conclusion: '',
}

function labelDe(lista, valor) {
  const item = lista.find((i) => String(i.value) === String(valor))
  return item ? item.label : valor
}

export default function SolicitudNueva() {
  const navigate = useNavigate()
  const { showError, showSuccess } = useToast()

  const [step, setStep] = useState(1)
  const [cabecera, setCabecera] = useState({
    codigo_solicitud: '',
    tipo_proceso: 'R',
    autoridad_solicitante: '',
    autoridad_cargo: '',
    gerencia: '',
  })
  const [adjunto, setAdjunto] = useState(null)
  const [erroresCabecera, setErroresCabecera] = useState({})
  const [errorAdjunto, setErrorAdjunto] = useState('')

  const [detalles, setDetalles] = useState([])
  const [item, setItem] = useState(ITEM_VACIO)
  const [erroresItem, setErroresItem] = useState({})
  const [editandoIndex, setEditandoIndex] = useState(null)

  const [enviando, setEnviando] = useState(false)

  const esSuspension = cabecera.tipo_proceso === 'S'

  // --- Paso 1 ---
  const onArchivoChange = async (e) => {
    const file = e.target.files?.[0] || null
    setAdjunto(file)
    if (file) {
      const res = await validarArchivoPdf(file)
      setErrorAdjunto(res.ok ? '' : res.mensaje)
    } else {
      setErrorAdjunto('')
    }
  }

  const avanzarDesdePaso1 = async () => {
    const errores = validarCabeceraSolicitud(cabecera)
    setErroresCabecera(errores)
    const pdfCheck = await validarArchivoPdf(adjunto)
    if (!pdfCheck.ok) {
      setErrorAdjunto(pdfCheck.mensaje)
    }
    if (tieneErrores(errores) || !pdfCheck.ok) return
    setStep(2)
  }

  // --- Paso 2 ---
  const onTipoPersonaChange = (tipo_persona) => {
    setItem((prev) => ({
      ...ITEM_VACIO,
      tipo_persona,
      documento_extension: prev.documento_extension,
    }))
    setErroresItem({})
  }

  const resetItemForm = () => {
    setItem(ITEM_VACIO)
    setErroresItem({})
    setEditandoIndex(null)
  }

  const agregarOActualizarItem = () => {
    const errores = validarDetallePersona(item, { esRemision: false })
    setErroresItem(errores)
    if (tieneErrores(errores)) return

    const normalizado = {
      ...item,
      documento_tipo: item.documento_tipo ? Number(item.documento_tipo) : '',
      tipo_respaldo: item.tipo_respaldo ? Number(item.tipo_respaldo) : '',
      monto_bs: item.monto_bs !== '' ? Number(item.monto_bs).toFixed(2) : '',
      monto_ufv: item.monto_ufv !== '' ? Number(item.monto_ufv).toFixed(2) : '',
      auto_conclusion: esSuspension ? item.auto_conclusion : '',
    }

    setDetalles((prev) => {
      const copia = [...prev]
      if (editandoIndex !== null) {
        copia[editandoIndex] = normalizado
      } else {
        copia.push(normalizado)
      }
      return copia
    })
    resetItemForm()
  }

  const editarItem = (idx) => {
    setItem(detalles[idx])
    setEditandoIndex(idx)
    setErroresItem({})
  }

  const eliminarItem = (idx) => {
    setDetalles((prev) => prev.filter((_, i) => i !== idx))
    if (editandoIndex === idx) resetItemForm()
  }

  const avanzarDesdePaso2 = () => {
    if (detalles.length === 0) {
      setErroresItem({ general: 'Agregue al menos un ítem antes de continuar.' })
      return
    }
    setStep(3)
  }

  // --- Paso 3 ---
  const enviar = async () => {
    setEnviando(true)
    try {
      const payload = {
        codigo_solicitud: cabecera.codigo_solicitud.trim(),
        tipo_proceso: cabecera.tipo_proceso,
        autoridad_solicitante: cabecera.autoridad_solicitante.trim(),
        autoridad_cargo: cabecera.autoridad_cargo.trim(),
        gerencia: cabecera.gerencia.trim(),
        detalles: detalles.map((d, idx) => ({
          item: idx + 1,
          tipo_persona: d.tipo_persona,
          nombres: d.tipo_persona === 'natural' ? d.nombres : '',
          apellido_paterno: d.tipo_persona === 'natural' ? d.apellido_paterno : '',
          apellido_materno: d.tipo_persona === 'natural' ? d.apellido_materno : '',
          razon_social: d.tipo_persona === 'juridica' ? d.razon_social : '',
          documento_tipo: Number(d.documento_tipo),
          documento_numero: d.documento_numero,
          documento_complemento: d.documento_complemento || '',
          documento_extension: d.documento_extension || '',
          documento_respaldo: d.documento_respaldo || '',
          tipo_respaldo: Number(d.tipo_respaldo),
          monto_bs: d.monto_bs !== '' ? Number(d.monto_bs) : null,
          monto_ufv: d.monto_ufv !== '' ? Number(d.monto_ufv) : null,
          auto_conclusion: esSuspension ? d.auto_conclusion || '' : '',
        })),
      }
      const res = await solicitudesApi.create(payload, adjunto)
      showSuccess('Solicitud enviada correctamente.')
      navigate(`/solicitudes/${res.data.id}`)
    } catch (err) {
      showError(err)
    } finally {
      setEnviando(false)
    }
  }

  const tiposDocumentoDisponibles =
    item.tipo_persona === 'natural'
      ? TIPOS_DOCUMENTO.filter((t) => DOC_TIPOS_NATURAL.includes(t.value))
      : TIPOS_DOCUMENTO.filter((t) => DOC_TIPOS_JURIDICA.includes(t.value))

  return (
    <div>
      <h1 className="page-title">Nueva solicitud</h1>

      <div className="wizard-steps">
        <span className={step === 1 ? 'wizard-step active' : 'wizard-step'}>1. Cabecera</span>
        <span className={step === 2 ? 'wizard-step active' : 'wizard-step'}>2. Detalles</span>
        <span className={step === 3 ? 'wizard-step active' : 'wizard-step'}>3. Resumen</span>
      </div>

      {step === 1 && (
        <section className="panel">
          <h2 className="panel-title">Cabecera</h2>
          <div className="form-grid">
            <label className="field">
              <span>Código de solicitud / Cite</span>
              <input
                type="text"
                value={cabecera.codigo_solicitud}
                onChange={(e) => setCabecera({ ...cabecera, codigo_solicitud: e.target.value })}
              />
              {erroresCabecera.codigo_solicitud && <span className="field-error">{erroresCabecera.codigo_solicitud}</span>}
            </label>

            <label className="field">
              <span>Tipo de proceso</span>
              <select
                value={cabecera.tipo_proceso}
                onChange={(e) => setCabecera({ ...cabecera, tipo_proceso: e.target.value })}
              >
                {TIPOS_PROCESO.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Autoridad solicitante</span>
              <input
                type="text"
                value={cabecera.autoridad_solicitante}
                onChange={(e) => setCabecera({ ...cabecera, autoridad_solicitante: e.target.value })}
              />
              {erroresCabecera.autoridad_solicitante && (
                <span className="field-error">{erroresCabecera.autoridad_solicitante}</span>
              )}
            </label>

            <label className="field">
              <span>Cargo de la autoridad</span>
              <input
                type="text"
                value={cabecera.autoridad_cargo}
                onChange={(e) => setCabecera({ ...cabecera, autoridad_cargo: e.target.value })}
              />
              {erroresCabecera.autoridad_cargo && <span className="field-error">{erroresCabecera.autoridad_cargo}</span>}
            </label>

            <label className="field">
              <span>Gerencia</span>
              <input
                type="text"
                value={cabecera.gerencia}
                onChange={(e) => setCabecera({ ...cabecera, gerencia: e.target.value })}
              />
              {erroresCabecera.gerencia && <span className="field-error">{erroresCabecera.gerencia}</span>}
            </label>

            <label className="field">
              <span>Adjunto (PDF)</span>
              <input type="file" accept="application/pdf" onChange={onArchivoChange} />
              {errorAdjunto && <span className="field-error">{errorAdjunto}</span>}
            </label>
          </div>

          <div className="action-bar">
            <button className="btn btn-primary" onClick={avanzarDesdePaso1}>
              Siguiente
            </button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="panel">
          <h2 className="panel-title">Detalles ({detalles.length})</h2>

          <div className="form-grid">
            <label className="field">
              <span>Tipo de persona</span>
              <select value={item.tipo_persona} onChange={(e) => onTipoPersonaChange(e.target.value)}>
                <option value="natural">Natural</option>
                <option value="juridica">Jurídica</option>
              </select>
              {erroresItem.tipo_persona && <span className="field-error">{erroresItem.tipo_persona}</span>}
            </label>

            {item.tipo_persona === 'natural' ? (
              <>
                <label className="field">
                  <span>Nombres</span>
                  <input type="text" value={item.nombres} onChange={(e) => setItem({ ...item, nombres: e.target.value })} />
                  {erroresItem.nombres && <span className="field-error">{erroresItem.nombres}</span>}
                </label>
                <label className="field">
                  <span>Apellido paterno</span>
                  <input
                    type="text"
                    value={item.apellido_paterno}
                    onChange={(e) => setItem({ ...item, apellido_paterno: e.target.value })}
                  />
                  {erroresItem.apellido_paterno && <span className="field-error">{erroresItem.apellido_paterno}</span>}
                </label>
                <label className="field">
                  <span>Apellido materno</span>
                  <input
                    type="text"
                    value={item.apellido_materno}
                    onChange={(e) => setItem({ ...item, apellido_materno: e.target.value })}
                  />
                </label>
              </>
            ) : (
              <label className="field">
                <span>Razón social</span>
                <input
                  type="text"
                  value={item.razon_social}
                  onChange={(e) => setItem({ ...item, razon_social: e.target.value })}
                />
                {erroresItem.razon_social && <span className="field-error">{erroresItem.razon_social}</span>}
              </label>
            )}

            <label className="field">
              <span>Tipo de documento</span>
              <select value={item.documento_tipo} onChange={(e) => setItem({ ...item, documento_tipo: e.target.value })}>
                <option value="">Seleccione…</option>
                {tiposDocumentoDisponibles.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
              {erroresItem.documento_tipo && <span className="field-error">{erroresItem.documento_tipo}</span>}
            </label>

            <label className="field">
              <span>Número de documento</span>
              <input
                type="text"
                value={item.documento_numero}
                onChange={(e) => setItem({ ...item, documento_numero: e.target.value })}
              />
              {erroresItem.documento_numero && <span className="field-error">{erroresItem.documento_numero}</span>}
            </label>

            <label className="field">
              <span>Complemento</span>
              <input
                type="text"
                value={item.documento_complemento}
                onChange={(e) => setItem({ ...item, documento_complemento: e.target.value })}
              />
            </label>

            <label className="field">
              <span>Extensión (departamento)</span>
              <select
                value={item.documento_extension}
                onChange={(e) => setItem({ ...item, documento_extension: e.target.value })}
              >
                {EXTENSIONES_DOCUMENTO.map((ex) => (
                  <option key={ex.value} value={ex.value}>
                    {ex.label}
                  </option>
                ))}
              </select>
              {erroresItem.documento_extension && <span className="field-error">{erroresItem.documento_extension}</span>}
            </label>

            <label className="field">
              <span>Documento de respaldo</span>
              <input
                type="text"
                value={item.documento_respaldo}
                onChange={(e) => setItem({ ...item, documento_respaldo: e.target.value })}
              />
            </label>

            <label className="field">
              <span>Tipo de respaldo</span>
              <select value={item.tipo_respaldo} onChange={(e) => setItem({ ...item, tipo_respaldo: e.target.value })}>
                <option value="">Seleccione…</option>
                {TIPOS_RESPALDO.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
              {erroresItem.tipo_respaldo && <span className="field-error">{erroresItem.tipo_respaldo}</span>}
            </label>

            <label className="field">
              <span>Monto en Bs</span>
              <input
                type="number"
                step="0.01"
                value={item.monto_bs}
                onChange={(e) => setItem({ ...item, monto_bs: e.target.value, monto_ufv: e.target.value ? '' : item.monto_ufv })}
              />
            </label>

            <label className="field">
              <span>Monto en UFV</span>
              <input
                type="number"
                step="0.01"
                value={item.monto_ufv}
                onChange={(e) => setItem({ ...item, monto_ufv: e.target.value, monto_bs: e.target.value ? '' : item.monto_bs })}
              />
            </label>
            {erroresItem.monto && <span className="field-error">{erroresItem.monto}</span>}

            {esSuspension && (
              <label className="field">
                <span>Auto conclusión</span>
                <input
                  type="text"
                  value={item.auto_conclusion}
                  onChange={(e) => setItem({ ...item, auto_conclusion: e.target.value })}
                />
              </label>
            )}
          </div>

          <div className="action-bar">
            <button className="btn btn-secondary" onClick={agregarOActualizarItem}>
              {editandoIndex !== null ? 'Actualizar ítem' : 'Agregar ítem'}
            </button>
            {editandoIndex !== null && (
              <button className="btn btn-ghost" onClick={resetItemForm}>
                Cancelar edición
              </button>
            )}
          </div>

          {erroresItem.general && <div className="alert alert-error">{erroresItem.general}</div>}

          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Tipo</th>
                  <th>Nombre / Razón social</th>
                  <th>Documento</th>
                  <th>Respaldo</th>
                  <th>Monto</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {detalles.map((d, idx) => (
                  <tr key={idx}>
                    <td>{idx + 1}</td>
                    <td>{d.tipo_persona === 'natural' ? 'Natural' : 'Jurídica'}</td>
                    <td>
                      {d.tipo_persona === 'natural'
                        ? `${d.nombres} ${d.apellido_paterno} ${d.apellido_materno}`.trim()
                        : d.razon_social}
                    </td>
                    <td>
                      {labelDe(TIPOS_DOCUMENTO, d.documento_tipo)} — {d.documento_numero}
                    </td>
                    <td>{labelDe(TIPOS_RESPALDO, d.tipo_respaldo)}</td>
                    <td>{d.monto_bs ? `Bs ${d.monto_bs}` : d.monto_ufv ? `UFV ${d.monto_ufv}` : '—'}</td>
                    <td className="actions-cell">
                      <button className="link-action" onClick={() => editarItem(idx)}>
                        Editar
                      </button>
                      <button className="link-action" onClick={() => eliminarItem(idx)}>
                        Quitar
                      </button>
                    </td>
                  </tr>
                ))}
                {detalles.length === 0 && (
                  <tr>
                    <td colSpan={7} className="empty-hint">
                      Sin ítems agregados.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="action-bar">
            <button className="btn btn-ghost" onClick={() => setStep(1)}>
              Atrás
            </button>
            <button className="btn btn-primary" onClick={avanzarDesdePaso2}>
              Siguiente
            </button>
          </div>
        </section>
      )}

      {step === 3 && (
        <section className="panel">
          <h2 className="panel-title">Resumen</h2>
          <dl className="detail-grid">
            <div>
              <dt>Código</dt>
              <dd>{cabecera.codigo_solicitud}</dd>
            </div>
            <div>
              <dt>Tipo</dt>
              <dd>{labelDe(TIPOS_PROCESO, cabecera.tipo_proceso)}</dd>
            </div>
            <div>
              <dt>Autoridad</dt>
              <dd>{cabecera.autoridad_solicitante}</dd>
            </div>
            <div>
              <dt>Cargo</dt>
              <dd>{cabecera.autoridad_cargo}</dd>
            </div>
            <div>
              <dt>Gerencia</dt>
              <dd>{cabecera.gerencia}</dd>
            </div>
            <div>
              <dt>Adjunto</dt>
              <dd>{adjunto?.name}</dd>
            </div>
            <div>
              <dt>Cantidad de ítems</dt>
              <dd>{detalles.length}</dd>
            </div>
          </dl>

          <div className="action-bar">
            <button className="btn btn-ghost" onClick={() => setStep(2)} disabled={enviando}>
              Atrás
            </button>
            <button className="btn btn-primary" onClick={enviar} disabled={enviando}>
              {enviando ? 'Enviando…' : 'Enviar solicitud'}
            </button>
          </div>
        </section>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { remisionesApi, sirefoApi } from '../api/endpoints'
import { useToast } from '../context/ToastContext'
import {
  TIPOS_DOCUMENTO,
  TIPOS_RESPALDO,
  EXTENSIONES_DOCUMENTO,
  CUENTA_MONEDA,
  DOC_TIPOS_NATURAL,
  DOC_TIPOS_JURIDICA,
} from '../utils/constants'
import { validarCabeceraRemision, validarDetallePersona, tieneErrores, validarArchivoPdf } from '../utils/validation'

const ITEM_VACIO = {
  tipo_persona: 'natural',
  nombres: '',
  apellido_paterno: '',
  apellido_materno: '',
  razon_social: '',
  tipo_documento: '',
  numero_documento: '',
  documento_complemento: '',
  extension_documento: '',
  documento_respaldo: '',
  tipo_respaldo: '',
  monto_remision: '',
  numero_cuenta: '',
  cuenta_moneda: '',
  codigo_envio: '',
}

function labelDe(lista, valor) {
  const item = lista.find((i) => String(i.value) === String(valor))
  return item ? item.label : valor
}

function extraerCodigoEnvio(entidad) {
  return entidad.codigo_envio ?? entidad.CodigoEnvio
}
function extraerDescripcion(entidad) {
  return entidad.descripcion ?? entidad.Descripcion
}

export default function RemisionNueva() {
  const navigate = useNavigate()
  const { showError, showSuccess } = useToast()

  const [step, setStep] = useState(1)
  const [cabecera, setCabecera] = useState({
    numero_sirefo: '',
    identificador_remision: '',
    autoridad_solicitante: '',
    gerencia_solicitante: '',
    cargo_solicitante: '',
  })
  const [adjunto, setAdjunto] = useState(null)
  const [erroresCabecera, setErroresCabecera] = useState({})
  const [errorAdjunto, setErrorAdjunto] = useState('')

  const [entidades, setEntidades] = useState([])

  const [detalles, setDetalles] = useState([])
  const [item, setItem] = useState(ITEM_VACIO)
  const [erroresItem, setErroresItem] = useState({})
  const [editandoIndex, setEditandoIndex] = useState(null)

  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    sirefoApi
      .entidades()
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : res.data.items || []
        setEntidades(data)
      })
      .catch((err) => showError(err))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
    const errores = validarCabeceraRemision(cabecera)
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
    setItem((prev) => ({ ...ITEM_VACIO, tipo_persona, codigo_envio: prev.codigo_envio }))
    setErroresItem({})
  }

  const resetItemForm = () => {
    setItem(ITEM_VACIO)
    setErroresItem({})
    setEditandoIndex(null)
  }

  const agregarOActualizarItem = () => {
    const errores = validarDetallePersona(item, { esRemision: true })
    setErroresItem(errores)
    if (tieneErrores(errores)) return

    const normalizado = {
      ...item,
      tipo_documento: item.tipo_documento ? Number(item.tipo_documento) : '',
      tipo_respaldo: item.tipo_respaldo ? Number(item.tipo_respaldo) : '',
      cuenta_moneda: item.cuenta_moneda ? Number(item.cuenta_moneda) : '',
      monto_remision: item.monto_remision !== '' ? Number(item.monto_remision).toFixed(2) : '',
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
        numero_sirefo: cabecera.numero_sirefo.trim(),
        identificador_remision: cabecera.identificador_remision.trim(),
        autoridad_solicitante: cabecera.autoridad_solicitante.trim(),
        gerencia_solicitante: cabecera.gerencia_solicitante.trim(),
        cargo_solicitante: cabecera.cargo_solicitante.trim(),
        detalles: detalles.map((d, idx) => ({
          item: idx + 1,
          tipo_persona: d.tipo_persona,
          nombres: d.tipo_persona === 'natural' ? d.nombres : '',
          apellido_paterno: d.tipo_persona === 'natural' ? d.apellido_paterno : '',
          apellido_materno: d.tipo_persona === 'natural' ? d.apellido_materno : '',
          razon_social: d.tipo_persona === 'juridica' ? d.razon_social : '',
          numero_documento: d.numero_documento,
          documento_complemento: d.documento_complemento || '',
          extension_documento: d.extension_documento || '',
          tipo_documento: Number(d.tipo_documento),
          documento_respaldo: d.documento_respaldo || '',
          tipo_respaldo: Number(d.tipo_respaldo),
          monto_remision: Number(d.monto_remision),
          numero_cuenta: d.numero_cuenta,
          cuenta_moneda: Number(d.cuenta_moneda),
          codigo_envio: d.codigo_envio,
        })),
      }
      const res = await remisionesApi.create(payload, adjunto)
      showSuccess('Remisión enviada correctamente.')
      navigate(`/remisiones/${res.data.id}`)
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
      <h1 className="page-title">Nueva remisión de fondos</h1>

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
              <span>Número SIREFO (retención previa)</span>
              <input
                type="text"
                value={cabecera.numero_sirefo}
                onChange={(e) => setCabecera({ ...cabecera, numero_sirefo: e.target.value })}
              />
              {erroresCabecera.numero_sirefo && <span className="field-error">{erroresCabecera.numero_sirefo}</span>}
            </label>

            <label className="field">
              <span>Identificador de remisión</span>
              <input
                type="text"
                value={cabecera.identificador_remision}
                onChange={(e) => setCabecera({ ...cabecera, identificador_remision: e.target.value })}
              />
              {erroresCabecera.identificador_remision && (
                <span className="field-error">{erroresCabecera.identificador_remision}</span>
              )}
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
              <span>Gerencia solicitante</span>
              <input
                type="text"
                value={cabecera.gerencia_solicitante}
                onChange={(e) => setCabecera({ ...cabecera, gerencia_solicitante: e.target.value })}
              />
              {erroresCabecera.gerencia_solicitante && (
                <span className="field-error">{erroresCabecera.gerencia_solicitante}</span>
              )}
            </label>

            <label className="field">
              <span>Cargo del solicitante</span>
              <input
                type="text"
                value={cabecera.cargo_solicitante}
                onChange={(e) => setCabecera({ ...cabecera, cargo_solicitante: e.target.value })}
              />
              {erroresCabecera.cargo_solicitante && <span className="field-error">{erroresCabecera.cargo_solicitante}</span>}
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
              <select value={item.tipo_documento} onChange={(e) => setItem({ ...item, tipo_documento: e.target.value })}>
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
                value={item.numero_documento}
                onChange={(e) => setItem({ ...item, numero_documento: e.target.value })}
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
                value={item.extension_documento}
                onChange={(e) => setItem({ ...item, extension_documento: e.target.value })}
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
              <span>Monto de remisión</span>
              <input
                type="number"
                step="0.01"
                value={item.monto_remision}
                onChange={(e) => setItem({ ...item, monto_remision: e.target.value })}
              />
              {erroresItem.monto_remision && <span className="field-error">{erroresItem.monto_remision}</span>}
            </label>

            <label className="field">
              <span>Número de cuenta</span>
              <input
                type="text"
                value={item.numero_cuenta}
                onChange={(e) => setItem({ ...item, numero_cuenta: e.target.value })}
              />
              {erroresItem.numero_cuenta && <span className="field-error">{erroresItem.numero_cuenta}</span>}
            </label>

            <label className="field">
              <span>Moneda de la cuenta</span>
              <select value={item.cuenta_moneda} onChange={(e) => setItem({ ...item, cuenta_moneda: e.target.value })}>
                <option value="">Seleccione…</option>
                {CUENTA_MONEDA.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
              {erroresItem.cuenta_moneda && <span className="field-error">{erroresItem.cuenta_moneda}</span>}
            </label>

            <label className="field">
              <span>Entidad (código de envío)</span>
              <select value={item.codigo_envio} onChange={(e) => setItem({ ...item, codigo_envio: e.target.value })}>
                <option value="">Seleccione…</option>
                {entidades.map((ent) => (
                  <option key={extraerCodigoEnvio(ent)} value={extraerCodigoEnvio(ent)}>
                    {extraerCodigoEnvio(ent)} - {extraerDescripcion(ent)}
                  </option>
                ))}
              </select>
              {erroresItem.codigo_envio && <span className="field-error">{erroresItem.codigo_envio}</span>}
            </label>
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
                  <th>Monto</th>
                  <th>Cuenta</th>
                  <th>Cód. envío</th>
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
                      {labelDe(TIPOS_DOCUMENTO, d.tipo_documento)} — {d.numero_documento}
                    </td>
                    <td>{d.monto_remision}</td>
                    <td>{d.numero_cuenta}</td>
                    <td>{d.codigo_envio}</td>
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
                    <td colSpan={8} className="empty-hint">
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
              <dt>Número SIREFO</dt>
              <dd>{cabecera.numero_sirefo}</dd>
            </div>
            <div>
              <dt>Identificador</dt>
              <dd>{cabecera.identificador_remision}</dd>
            </div>
            <div>
              <dt>Autoridad</dt>
              <dd>{cabecera.autoridad_solicitante}</dd>
            </div>
            <div>
              <dt>Gerencia</dt>
              <dd>{cabecera.gerencia_solicitante}</dd>
            </div>
            <div>
              <dt>Cargo</dt>
              <dd>{cabecera.cargo_solicitante}</dd>
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
              {enviando ? 'Enviando…' : 'Enviar remisión'}
            </button>
          </div>
        </section>
      )}
    </div>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { configApi, sirefoApi } from '../api/endpoints'
import { useToast } from '../context/ToastContext'
import Badge from '../components/Badge'

const HASH_ENCODINGS = [
  { value: 'hex', label: 'hex (minúsculas)' },
  { value: 'HEX', label: 'HEX (mayúsculas)' },
  { value: 'base64', label: 'base64' },
]

const VACIO = {
  modo: 'mock',
  wsdl_url: '',
  asfi_usuario: '',
  asfi_clave: '',
  entidad: '',
  hash_encoding: 'hex',
  tls_verify: true,
}

function FuenteBadge({ fuente }) {
  if (!fuente) return null
  return (
    <Badge
      text={fuente === 'db' ? 'BD' : 'entorno'}
      className={fuente === 'db' ? 'badge-green' : 'badge-blue'}
    />
  )
}

export default function Configuracion() {
  const { showError, showSuccess } = useToast()
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [form, setForm] = useState(VACIO)
  const [fuente, setFuente] = useState({})
  const [claveDefinida, setClaveDefinida] = useState(false)
  const [tocados, setTocados] = useState(new Set())

  const [pingTexto, setPingTexto] = useState('SIREFO')
  const [pingResultado, setPingResultado] = useState(null)
  const [pingCargando, setPingCargando] = useState(false)

  const aplicarRespuesta = (data) => {
    setForm({
      modo: data.modo,
      wsdl_url: data.wsdl_url,
      asfi_usuario: data.asfi_usuario,
      asfi_clave: '',
      entidad: data.entidad,
      hash_encoding: data.hash_encoding,
      tls_verify: data.tls_verify,
    })
    setFuente(data.fuente)
    setClaveDefinida(data.asfi_clave_definida)
    setTocados(new Set())
  }

  const cargar = useCallback(async () => {
    setCargando(true)
    try {
      const res = await configApi.get()
      aplicarRespuesta(res.data)
    } catch (err) {
      showError(err)
    } finally {
      setCargando(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    cargar()
  }, [cargar])

  const actualizarCampo = (campo, valor) => {
    setForm((prev) => ({ ...prev, [campo]: valor }))
    setTocados((prev) => new Set(prev).add(campo))
  }

  const guardar = async () => {
    const payload = {}
    tocados.forEach((campo) => {
      // Clave vacía = "sin cambios" (no se envía; el backend mantiene la actual).
      if (campo === 'asfi_clave' && !form.asfi_clave) return
      payload[campo] = form[campo]
    })
    if (Object.keys(payload).length === 0) {
      showSuccess('No hay cambios para guardar.')
      return
    }
    setGuardando(true)
    try {
      const res = await configApi.update(payload)
      showSuccess('Configuración actualizada correctamente.')
      aplicarRespuesta(res.data)
    } catch (err) {
      showError(err)
    } finally {
      setGuardando(false)
    }
  }

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

  if (cargando) {
    return <p className="empty-hint">Cargando…</p>
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Configuración</h1>
      </div>

      <div className="panel">
        <p className="panel-hint">
          Estos parámetros de conexión con SIREFO viven por defecto en <code>backend/.env</code>.
          Guardar un valor aquí lo sobreescribe (queda almacenado en la base de datos); el
          origen actual de cada campo se indica con la etiqueta <Badge text="entorno" className="badge-blue" />{' '}
          o <Badge text="BD" className="badge-green" />.
        </p>

        <div className="form-grid">
          <label className="field">
            <span>
              Modo <FuenteBadge fuente={fuente.modo} />
            </span>
            <select value={form.modo} onChange={(e) => actualizarCampo('modo', e.target.value)}>
              <option value="mock">mock (simulado)</option>
              <option value="soap">soap (ASFI real)</option>
            </select>
          </label>

          {form.modo === 'soap' && (
            <label className="field">
              <span>
                WSDL URL <FuenteBadge fuente={fuente.wsdl_url} />
              </span>
              <input
                type="text"
                value={form.wsdl_url}
                onChange={(e) => actualizarCampo('wsdl_url', e.target.value)}
              />
            </label>
          )}

          <label className="field">
            <span>
              Usuario ASFI <FuenteBadge fuente={fuente.asfi_usuario} />
            </span>
            <input
              type="text"
              value={form.asfi_usuario}
              onChange={(e) => actualizarCampo('asfi_usuario', e.target.value)}
            />
          </label>

          <label className="field">
            <span>Clave ASFI</span>
            <input
              type="password"
              value={form.asfi_clave}
              onChange={(e) => actualizarCampo('asfi_clave', e.target.value)}
              placeholder={claveDefinida ? '•••••• (sin cambios)' : '(no configurada)'}
              autoComplete="new-password"
            />
          </label>

          <label className="field">
            <span>
              Entidad <FuenteBadge fuente={fuente.entidad} />
            </span>
            <input
              type="text"
              value={form.entidad}
              onChange={(e) => actualizarCampo('entidad', e.target.value)}
            />
          </label>

          <label className="field">
            <span>
              Codificación de hash <FuenteBadge fuente={fuente.hash_encoding} />
            </span>
            <select
              value={form.hash_encoding}
              onChange={(e) => actualizarCampo('hash_encoding', e.target.value)}
            >
              {HASH_ENCODINGS.map((h) => (
                <option key={h.value} value={h.value}>
                  {h.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field field-checkbox">
            <input
              type="checkbox"
              checked={form.tls_verify}
              onChange={(e) => actualizarCampo('tls_verify', e.target.checked)}
            />
            <span>
              Verificar TLS (modo soap) <FuenteBadge fuente={fuente.tls_verify} />
            </span>
          </label>
        </div>

        <button className="btn btn-primary" onClick={guardar} disabled={guardando || tocados.size === 0}>
          {guardando ? 'Guardando…' : 'Guardar cambios'}
        </button>
      </div>

      <div className="panel">
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
      </div>
    </div>
  )
}

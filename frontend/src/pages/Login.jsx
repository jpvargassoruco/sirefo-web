import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function Login() {
  const { user, login, loading } = useAuth()
  const { showError } = useToast()
  const navigate = useNavigate()
  const location = useLocation()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [errores, setErrores] = useState({})

  if (!loading && user) {
    const dest = location.state?.from || '/'
    return <Navigate to={dest} replace />
  }

  const validar = () => {
    const err = {}
    if (!username.trim()) err.username = 'Ingrese su usuario.'
    if (!password) err.password = 'Ingrese su contraseña.'
    setErrores(err)
    return Object.keys(err).length === 0
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    if (!validar()) return
    setSubmitting(true)
    try {
      await login(username.trim(), password)
      navigate('/', { replace: true })
    } catch (err) {
      showError(err)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={onSubmit}>
        <div className="login-brand">
          <span className="brand-mark">SIREFO</span>
          <span className="brand-sub">G.A.M. Warnes</span>
        </div>
        <h1>Iniciar sesión</h1>

        <label className="field">
          <span>Usuario</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            autoComplete="username"
          />
          {errores.username && <span className="field-error">{errores.username}</span>}
        </label>

        <label className="field">
          <span>Contraseña</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
          {errores.password && <span className="field-error">{errores.password}</span>}
        </label>

        <button className="btn btn-primary btn-block" type="submit" disabled={submitting}>
          {submitting ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
    </div>
  )
}

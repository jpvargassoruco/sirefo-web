import { createContext, useCallback, useContext, useRef, useState } from 'react'

const ToastContext = createContext(null)

let nextId = 1

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timers = useRef({})

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
    if (timers.current[id]) {
      clearTimeout(timers.current[id])
      delete timers.current[id]
    }
  }, [])

  const push = useCallback(
    (message, type = 'error') => {
      const id = nextId++
      setToasts((prev) => [...prev, { id, message, type }])
      timers.current[id] = setTimeout(() => dismiss(id), 8000)
      return id
    },
    [dismiss]
  )

  const showError = useCallback(
    (err) => {
      let message = 'Ocurrió un error inesperado.'
      if (typeof err === 'string') {
        message = err
      } else if (err?.response?.data?.detail) {
        const d = err.response.data.detail
        message = typeof d === 'string' ? d : JSON.stringify(d)
      } else if (err?.message) {
        message = err.message
      }
      return push(message, 'error')
    },
    [push]
  )

  const showSuccess = useCallback((message) => push(message, 'success'), [push])

  return (
    <ToastContext.Provider value={{ push, showError, showSuccess, dismiss }}>
      {children}
      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            <span>{t.message}</span>
            <button className="toast-close" onClick={() => dismiss(t.id)} aria-label="Cerrar">
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast debe usarse dentro de ToastProvider')
  return ctx
}

import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { authApi } from '../api/endpoints'

const AuthContext = createContext(null)

function readStoredUser() {
  try {
    const raw = localStorage.getItem('sirefo_user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readStoredUser)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('sirefo_token')
    if (!token) {
      setLoading(false)
      return
    }
    authApi
      .me()
      .then((res) => {
        setUser(res.data)
        localStorage.setItem('sirefo_user', JSON.stringify(res.data))
      })
      .catch(() => {
        localStorage.removeItem('sirefo_token')
        localStorage.removeItem('sirefo_user')
        setUser(null)
      })
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = useCallback(async (username, password) => {
    const res = await authApi.login(username, password)
    const { access_token, user: loggedUser } = res.data
    localStorage.setItem('sirefo_token', access_token)
    localStorage.setItem('sirefo_user', JSON.stringify(loggedUser))
    setUser(loggedUser)
    return loggedUser
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('sirefo_token')
    localStorage.removeItem('sirefo_user')
    setUser(null)
  }, [])

  const value = { user, login, logout, loading, isAuthenticated: !!user }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}

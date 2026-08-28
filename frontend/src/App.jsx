import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'

import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Solicitudes from './pages/Solicitudes'
import SolicitudNueva from './pages/SolicitudNueva'
import SolicitudDetalle from './pages/SolicitudDetalle'
import Remisiones from './pages/Remisiones'
import RemisionNueva from './pages/RemisionNueva'
import RemisionDetalle from './pages/RemisionDetalle'
import Consultas from './pages/Consultas'
import Usuarios from './pages/Usuarios'
import Logs from './pages/Logs'
import Configuracion from './pages/Configuracion'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />

            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route path="/" element={<Dashboard />} />

                <Route path="/solicitudes" element={<Solicitudes />} />
                <Route path="/solicitudes/:id" element={<SolicitudDetalle />} />

                <Route path="/remisiones" element={<Remisiones />} />
                <Route path="/remisiones/:id" element={<RemisionDetalle />} />

                <Route path="/consultas" element={<Consultas />} />
              </Route>
            </Route>

            <Route element={<ProtectedRoute roles={['admin', 'operador']} />}>
              <Route element={<Layout />}>
                <Route path="/solicitudes/nueva" element={<SolicitudNueva />} />
                <Route path="/remisiones/nueva" element={<RemisionNueva />} />
              </Route>
            </Route>

            <Route element={<ProtectedRoute roles={['admin']} />}>
              <Route element={<Layout />}>
                <Route path="/usuarios" element={<Usuarios />} />
                <Route path="/logs" element={<Logs />} />
                <Route path="/configuracion" element={<Configuracion />} />
              </Route>
            </Route>

            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ToastProvider>
  )
}

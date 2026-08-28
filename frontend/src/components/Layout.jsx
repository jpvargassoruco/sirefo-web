import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/', label: 'Panel', end: true, roles: null },
  { to: '/solicitudes', label: 'Solicitudes', roles: null },
  { to: '/remisiones', label: 'Remisiones', roles: null },
  { to: '/consultas', label: 'Consultas', roles: null },
  { to: '/usuarios', label: 'Usuarios', roles: ['admin'] },
  { to: '/logs', label: 'Auditoría', roles: ['admin'] },
  { to: '/configuracion', label: 'Configuración', roles: ['admin'] },
]

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-mark">SIREFO</span>
          <span className="brand-sub">G.A.M. Warnes</span>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.filter((item) => !item.roles || item.roles.includes(user?.role)).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => 'sidebar-link' + (isActive ? ' active' : '')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="main-area">
        <header className="topbar">
          <div className="topbar-title">SIREFO — G.A.M. Warnes</div>
          <div className="topbar-user">
            <span className="user-name">{user?.full_name || user?.username}</span>
            <span className={`role-pill role-${user?.role}`}>{user?.role}</span>
            <button className="btn btn-ghost" onClick={logout}>
              Salir
            </button>
          </div>
        </header>
        <main className="content-area">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

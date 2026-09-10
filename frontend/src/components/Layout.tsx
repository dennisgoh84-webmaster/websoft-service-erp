import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="brand">Websoft Service ERP</div>
        <NavLink to="/" end>
          Customers
        </NavLink>
        <NavLink to="/contracts">Contracts</NavLink>
        <NavLink to="/tickets">Tickets</NavLink>
        <NavLink to="/excess-review">Excess Review</NavLink>
        <NavLink to="/invoices">Invoices</NavLink>
        <div className="user-info">
          <div>
            <strong>{user?.full_name}</strong>
          </div>
          <div>{user?.role}</div>
          <button className="secondary" style={{ marginTop: 10, width: '100%' }} onClick={logout}>
            Sign out
          </button>
        </div>
      </nav>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}

import { NavLink, Outlet } from 'react-router-dom'
import ThemeToggle from './ThemeToggle'
import { useAuth } from '../lib/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="brand">Websoft Service ERP</div>
        <NavLink to="/" end>
          Dashboard
        </NavLink>
        <NavLink to="/customers">Customers</NavLink>
        <NavLink to="/contracts">Contracts</NavLink>
        <NavLink to="/job-orders">Job Orders</NavLink>
        <NavLink to="/excess-review">Excess Review</NavLink>
        <NavLink to="/invoices">Invoices</NavLink>
        {user?.role === 'owner' && <NavLink to="/modules">Module Control</NavLink>}
        {user?.role === 'owner' && <NavLink to="/staff">Staff Master</NavLink>}
        {user?.role === 'owner' && <NavLink to="/groups">Group Authority</NavLink>}
        {user?.role === 'owner' && <NavLink to="/event-logs">Event Logs</NavLink>}
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
        <div className="main-topbar">
          <ThemeToggle />
        </div>
        <Outlet />
      </main>
    </div>
  )
}

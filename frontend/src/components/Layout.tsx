import { NavLink, Outlet } from 'react-router-dom'
import CompanySwitcher from './CompanySwitcher'
import ThemeToggle from './ThemeToggle'
import { useAuth } from '../lib/AuthContext'

export default function Layout() {
  const { user, logout, activeCompany } = useAuth()

  return (
    <div className="app-shell">
      <nav className="sidebar">
        {/* Company logo sits above the product name -- it does not
            replace it. Set it in Company Setup. */}
        <div className="brand-block">
          {activeCompany?.logo && (
            <img
              className="company-logo"
              src={activeCompany.logo}
              alt={`${activeCompany.name} logo`}
            />
          )}
          <div className="brand">Websoft Service ERP</div>
          {activeCompany && <div className="brand-company">{activeCompany.name}</div>}
        </div>
        <NavLink to="/" end>
          Dashboard
        </NavLink>

        <div className="nav-section">
          <div className="nav-section-label">Operations</div>
          <NavLink to="/customers">Customers</NavLink>
          <NavLink to="/contracts">Contracts</NavLink>
          <NavLink to="/job-orders">Job Orders</NavLink>
          <NavLink to="/service-records">Service Records</NavLink>
          <NavLink to="/excess-review">Excess Review</NavLink>
          <NavLink to="/support-monitoring">Support Monitoring</NavLink>
          <NavLink to="/software-tasks">Software Tasks</NavLink>
        </div>

        <div className="nav-section">
          <div className="nav-section-label">Accounts</div>
          <NavLink to="/quotations">Sales Quotation</NavLink>
          <NavLink to="/invoices">Invoices</NavLink>
          <NavLink to="/receipts">Receipts</NavLink>
          <NavLink to="/accounts-payable">Accounts Payable</NavLink>
          <NavLink to="/payment-voucher">Payment Voucher</NavLink>
          <NavLink to="/chart-of-accounts">Chart of Accounts</NavLink>
          <NavLink to="/general-ledger">General Ledger</NavLink>
        </div>

        {user?.role === 'owner' && (
          <div className="nav-section">
            <div className="nav-section-label">Maintenance</div>
            <NavLink to="/company-setup">Company Setup</NavLink>
            <NavLink to="/staff">Staff Master</NavLink>
            <NavLink to="/modules">Module Control</NavLink>
            <NavLink to="/groups">Group Authority</NavLink>
            <NavLink to="/product-catalog">Product Catalog</NavLink>
            <NavLink to="/event-logs">Event Logs</NavLink>
          </div>
        )}
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
          <CompanySwitcher />
          <ThemeToggle />
        </div>
        <Outlet />
      </main>
    </div>
  )
}

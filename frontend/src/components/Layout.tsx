import { NavLink, Outlet } from 'react-router-dom'
import CompanySwitcher from './CompanySwitcher'
import ThemeToggle from './ThemeToggle'
import { useAuth } from '../lib/AuthContext'

/** Which module_key gates each nav link -- mirrors the `MODULE` constant
    at the top of each router (see app/routers/*.py). A link only shows
    when moduleAccess[key] is true: Group Authority grants at least VIEW
    AND Module Control has the module enabled for the active company
    (see app/services/authority.py / GET /api/modules/my-access). The
    owner role always reads as true for every built module (backend
    bypass mirrored there), so this never hides a link Dennis can
    actually use. */
export default function Layout() {
  const { user, logout, activeCompany, moduleAccess } = useAuth()
  const can = (moduleKey: string) => moduleAccess[moduleKey] === true

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

        {/* Scrolls independently of the brand-block above and the
            user-info below once there are more links than fit one
            screen -- the menu is expected to keep growing as modules
            are added, so this must never depend on the viewport being
            tall enough. */}
        <div className="sidebar-nav">
          <NavLink to="/" end>
            Company Dashboard
          </NavLink>

          <div className="nav-section">
            <div className="nav-section-label">Operations</div>
            {can('reporting') && <NavLink to="/support-monitoring">Support Monitoring</NavLink>}
            {can('customer_management') && <NavLink to="/customers">Customers</NavLink>}
            {can('service_contracts') && <NavLink to="/contracts">Contracts</NavLink>}
            {can('service_operations') && <NavLink to="/job-orders">Job Orders</NavLink>}
            {can('service_records') && <NavLink to="/service-records">Service Records</NavLink>}
            {can('service_contracts') && <NavLink to="/excess-review">Excess Review</NavLink>}
            {can('software_development') && <NavLink to="/software-tasks">Software Tasks</NavLink>}
            {can('operations_reports') && <NavLink to="/operations-reports">Operations Reports</NavLink>}
          </div>

          <div className="nav-section">
            <div className="nav-section-label">Accounts</div>
            {can('sales') && <NavLink to="/quotations">Sales Quotation</NavLink>}
            {can('billing') && <NavLink to="/invoices">Invoices</NavLink>}
            {can('accounts_receivable') && <NavLink to="/receipts">Receipts</NavLink>}
            {can('accounts_payable') && <NavLink to="/accounts-payable">Accounts Payable</NavLink>}
            {can('accounts_payable') && <NavLink to="/payment-voucher">Payment Voucher</NavLink>}
            {can('finance_accounting') && <NavLink to="/chart-of-accounts">Chart of Accounts</NavLink>}
            {can('finance_accounting') && <NavLink to="/general-ledger">General Ledger</NavLink>}
            {can('accounting_reports') && <NavLink to="/accounting-reports">Accounting Reports</NavLink>}
          </div>

          {(can('core_administration') || can('event_logs') || can('sales')) && (
            <div className="nav-section">
              <div className="nav-section-label">Maintenance</div>
              {can('core_administration') && <NavLink to="/company-setup">Company Setup</NavLink>}
              {can('core_administration') && <NavLink to="/staff">Staff Master</NavLink>}
              {can('core_administration') && <NavLink to="/modules">Module Control</NavLink>}
              {can('core_administration') && <NavLink to="/groups">Group Authority</NavLink>}
              {can('sales') && <NavLink to="/product-catalog">Product Catalog</NavLink>}
              {can('event_logs') && <NavLink to="/event-logs">Event Logs</NavLink>}
            </div>
          )}
        </div>

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

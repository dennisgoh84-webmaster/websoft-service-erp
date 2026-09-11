import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import CompanySwitcher from './CompanySwitcher'
import ThemeToggle from './ThemeToggle'
import { useAuth } from '../lib/AuthContext'

const NAV_COLLAPSE_KEY = 'websoft_nav_collapsed'

function loadCollapsed(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(NAV_COLLAPSE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

/** Which module_key gates each nav link -- mirrors the `MODULE` constant
    at the top of each router (see app/routers/*.py). A link only shows
    when moduleAccess[key] is true: Group Authority grants at least VIEW
    AND Module Control has the module enabled for the active company
    (see app/services/authority.py / GET /api/modules/my-access). The
    owner role always reads as true for every built module (backend
    bypass mirrored there), so this never hides a link Dennis can
    actually use.

    Confirmed 2026-09-11: each section (Operations / Accounts /
    Maintenance) can be minimized independently -- a chevron toggle,
    state kept in localStorage (a per-browser display preference, not a
    permission, so it's fine to keep client-side only). This sits ON
    TOP of Group Authority, not instead of it: a section header itself
    only renders when at least one link inside it is visible to this
    user, exactly like the pre-existing Maintenance section already
    did -- collapsing a section never reveals anything a user's Group
    Authority already hides. */
export default function Layout() {
  const { user, logout, activeCompany, moduleAccess } = useAuth()
  const can = (moduleKey: string) => moduleAccess[moduleKey] === true
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(loadCollapsed)

  function toggleSection(key: string) {
    setCollapsed((prev) => {
      const next = { ...prev, [key]: !prev[key] }
      try {
        localStorage.setItem(NAV_COLLAPSE_KEY, JSON.stringify(next))
      } catch {
        /* private browsing / storage blocked -- collapse state just won't persist */
      }
      return next
    })
  }

  const opsVisible =
    can('reporting') ||
    can('customer_management') ||
    can('service_contracts') ||
    can('service_operations') ||
    can('service_records') ||
    can('software_development') ||
    can('operations_reports')

  const accountsVisible =
    can('sales') ||
    can('billing') ||
    can('accounts_receivable') ||
    can('accounts_payable') ||
    can('finance_accounting') ||
    can('accounting_reports')

  const maintenanceVisible = can('core_administration') || can('event_logs') || can('sales')

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

          {opsVisible && (
            <div className="nav-section">
              <button
                type="button"
                className="nav-section-label"
                aria-expanded={!collapsed.operations}
                onClick={() => toggleSection('operations')}
              >
                <span>Operations</span>
                <span className="nav-section-chevron">{collapsed.operations ? '▸' : '▾'}</span>
              </button>
              {!collapsed.operations && (
                <>
                  {can('reporting') && <NavLink to="/support-monitoring">Support Monitoring</NavLink>}
                  {can('customer_management') && <NavLink to="/customers">Customers</NavLink>}
                  {can('service_contracts') && <NavLink to="/contracts">Service Contracts</NavLink>}
                  {can('service_operations') && <NavLink to="/job-orders">Job Orders</NavLink>}
                  {can('service_records') && <NavLink to="/service-records">Service Records</NavLink>}
                  {can('service_contracts') && <NavLink to="/excess-review">Excess Review</NavLink>}
                  {can('software_development') && <NavLink to="/software-tasks">Software Tasks</NavLink>}
                  {can('operations_reports') && <NavLink to="/operations-reports">Operations Reports</NavLink>}
                </>
              )}
            </div>
          )}

          {accountsVisible && (
            <div className="nav-section">
              <button
                type="button"
                className="nav-section-label"
                aria-expanded={!collapsed.accounts}
                onClick={() => toggleSection('accounts')}
              >
                <span>Accounts</span>
                <span className="nav-section-chevron">{collapsed.accounts ? '▸' : '▾'}</span>
              </button>
              {!collapsed.accounts && (
                <>
                  {can('sales') && <NavLink to="/quotations">Sales Quotation</NavLink>}
                  {can('billing') && <NavLink to="/invoices">Invoices</NavLink>}
                  {can('accounts_receivable') && <NavLink to="/receipts">Receipts</NavLink>}
                  {can('accounts_payable') && <NavLink to="/accounts-payable">Accounts Payable</NavLink>}
                  {can('accounts_payable') && <NavLink to="/payment-voucher">Payment Voucher</NavLink>}
                  {can('finance_accounting') && <NavLink to="/chart-of-accounts">Chart of Accounts</NavLink>}
                  {can('finance_accounting') && <NavLink to="/gl-types">GL Types</NavLink>}
                  {can('finance_accounting') && <NavLink to="/tax-types">Tax Types</NavLink>}
                  {can('finance_accounting') && <NavLink to="/bank-accounts">Bank Master File</NavLink>}
                  {can('finance_accounting') && <NavLink to="/currency-rates">Currency Rate Table</NavLink>}
                  {can('finance_accounting') && <NavLink to="/general-ledger">General Ledger</NavLink>}
                  {can('finance_accounting') && <NavLink to="/accounting-periods">Accounting Periods</NavLink>}
                  {can('accounting_reports') && <NavLink to="/accounting-reports">Accounting Reports</NavLink>}
                </>
              )}
            </div>
          )}

          {maintenanceVisible && (
            <div className="nav-section">
              <button
                type="button"
                className="nav-section-label"
                aria-expanded={!collapsed.maintenance}
                onClick={() => toggleSection('maintenance')}
              >
                <span>Maintenance</span>
                <span className="nav-section-chevron">{collapsed.maintenance ? '▸' : '▾'}</span>
              </button>
              {!collapsed.maintenance && (
                <>
                  {can('core_administration') && <NavLink to="/company-setup">Company Setup</NavLink>}
                  {can('core_administration') && <NavLink to="/staff">Staff Master</NavLink>}
                  {can('core_administration') && <NavLink to="/modules">Module Control</NavLink>}
                  {can('core_administration') && <NavLink to="/groups">Group Authority</NavLink>}
                  {can('sales') && <NavLink to="/product-catalog">Product Catalog</NavLink>}
                  {can('core_administration') && <NavLink to="/setup-lists">Setup Lists</NavLink>}
                  {can('core_administration') && <NavLink to="/document-control">Document Control</NavLink>}
                  {can('event_logs') && <NavLink to="/event-logs">Event Logs</NavLink>}
                </>
              )}
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

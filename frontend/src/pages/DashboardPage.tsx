import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type DashboardSummary } from '../lib/api'
import { useAuth } from '../lib/AuthContext'

function Stat({
  label,
  value,
  hint,
  to,
  small,
}: {
  label: string
  value: string | number
  hint?: string
  to?: string
  /** Currency/text values (e.g. "SGD 12345.67") need the smaller variant to
      fit a tile on one line -- see .stat-value-text in index.css. */
  small?: boolean
}) {
  const inner = (
    <div className="card stat-tile">
      <div className={`stat-value${small ? ' stat-value-text' : ''}`}>{value}</div>
      <div className="stat-label">{label}</div>
      {hint && <div className="muted" style={{ marginTop: 4 }}>{hint}</div>}
    </div>
  )
  return to ? (
    <Link to={to} style={{ textDecoration: 'none', color: 'inherit' }}>
      {inner}
    </Link>
  ) : (
    inner
  )
}

export default function DashboardPage() {
  const { activeCompany } = useAuth()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)

  useEffect(() => {
    api.dashboardSummary().then(setSummary)
  }, [])

  if (!summary) return <p>Loading...</p>

  const netReceivable = summary.ar_outstanding_sgd - summary.ap_outstanding_sgd

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {activeCompany?.logo && (
          <img
            src={activeCompany.logo}
            alt={`${activeCompany.name} logo`}
            style={{ height: 40, width: 'auto', maxWidth: 160, objectFit: 'contain' }}
          />
        )}
        <h1 style={{ margin: 0 }}>Company Dashboard</h1>
      </div>
      <p className="muted">
        Financial and operations summary for {activeCompany?.name ?? 'this company'} -- see
        docs/business-requirements.md for the full requirements list. Company details (address, GST no.,
        logo) live under Company Setup.
      </p>

      <h2>Financial Summary</h2>
      <div className="stat-grid">
        <Stat
          small
          label="AR outstanding"
          value={`SGD ${summary.ar_outstanding_sgd.toFixed(2)}`}
          hint={`incl. SGD ${summary.ar_overdue_sgd.toFixed(2)} overdue`}
          to="/invoices"
        />
        <Stat
          small
          label="AP outstanding"
          value={`SGD ${summary.ap_outstanding_sgd.toFixed(2)}`}
          hint={`incl. SGD ${summary.ap_overdue_sgd.toFixed(2)} overdue`}
          to="/accounts-payable"
        />
        <Stat
          small
          label="Net receivable position"
          value={`SGD ${netReceivable.toFixed(2)}`}
          hint="AR outstanding less AP outstanding"
        />
        <Stat small label="Invoiced to date" value={`SGD ${summary.invoices_total_sgd.toFixed(2)}`} to="/invoices" />
        <div className="card stat-tile">
          <span className={`badge ${summary.gl_is_balanced ? 'active' : 'exceeded'}`}>
            {summary.gl_is_balanced ? 'Balanced' : 'OUT OF BALANCE'}
          </span>
          <div className="stat-label" style={{ marginTop: 4 }}>
            GL Trial Balance
          </div>
        </div>
      </div>
      <p className="muted" style={{ marginTop: -4 }}>
        Full breakdowns: <Link to="/accounting-reports">Accounting Reports</Link> (AR/AP aging, trial
        balance).
      </p>

      <h2>Service Operations</h2>
      <div className="stat-grid">
        <Stat label="Active contracts" value={summary.active_contracts} to="/contracts?status=active" />
        <Stat
          label="Expiring soon"
          value={summary.contracts_expiring_soon}
          hint="within 30 days (SRV-014)"
          to="/contracts"
        />
        <Stat label="Open job orders" value={summary.open_job_orders} to="/job-orders?status=open" />
        <Stat
          label="Excess awaiting review"
          value={summary.excess_awaiting_review}
          to="/excess-review"
        />
        <Stat
          label="Late service records"
          value={summary.missing_service_records}
          hint="submitted >3 business days late (SRV-015)"
        />
        <Stat label="Invoices issued" value={summary.invoices_count} to="/invoices" />
      </div>

      <div className="card">
        <h2>Contracted hours across all contracts</h2>
        <div className="progress-bar" style={{ height: 12 }}>
          <div
            style={{
              width: `${summary.total_contracted_hours ? (summary.total_consumed_hours / summary.total_contracted_hours) * 100 : 0}%`,
            }}
          />
        </div>
        <p>
          {summary.total_consumed_hours.toFixed(1)} used / {summary.total_contracted_hours.toFixed(1)} contracted --{' '}
          <strong>{summary.total_remaining_hours.toFixed(1)} hrs remaining</strong>
        </p>
      </div>

    </div>
  )
}

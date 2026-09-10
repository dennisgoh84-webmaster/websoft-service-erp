import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type DashboardSummary } from '../lib/api'

function Stat({ label, value, hint, to }: { label: string; value: string | number; hint?: string; to?: string }) {
  const inner = (
    <div className="card stat-tile">
      <div className="stat-value">{value}</div>
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
  const [summary, setSummary] = useState<DashboardSummary | null>(null)

  useEffect(() => {
    api.dashboardSummary().then(setSummary)
  }, [])

  if (!summary) return <p>Loading...</p>

  return (
    <div>
      <h1>Dashboard</h1>
      <p className="muted">Service Operations summary -- see docs/business-requirements.md for the full requirements list.</p>

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

      <div className="card">
        <h2>Billing</h2>
        <p>
          <strong>SGD {summary.invoices_total_sgd.toFixed(2)}</strong> invoiced across {summary.invoices_count} invoice
          {summary.invoices_count === 1 ? '' : 's'} (BILL-001/002/005).
        </p>
      </div>
    </div>
  )
}

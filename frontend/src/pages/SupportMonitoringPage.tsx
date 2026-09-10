import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type StaffMonitoring, type SupportMonitoring } from '../lib/api'

function StaffCard({ row }: { row: StaffMonitoring }) {
  const overloaded = row.overdue_job_orders > 0
  return (
    <div className="card" style={{ borderColor: overloaded ? 'var(--danger, #b33)' : undefined }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong>{row.full_name}</strong>
        {overloaded && <span className="badge exceeded">overloaded</span>}
      </div>
      <table style={{ marginTop: 8 }}>
        <tbody>
          <tr>
            <td className="muted">Open Job Orders</td>
            <td style={{ textAlign: 'right' }}>{row.open_job_orders}</td>
          </tr>
          <tr>
            <td className="muted">Overdue</td>
            <td style={{ textAlign: 'right' }}>
              <strong style={{ color: row.overdue_job_orders > 0 ? '#b33' : undefined }}>
                {row.overdue_job_orders}
              </strong>
            </td>
          </tr>
          <tr>
            <td className="muted">Due soon</td>
            <td style={{ textAlign: 'right' }}>{row.due_soon_job_orders}</td>
          </tr>
          <tr>
            <td className="muted">Pending Service Records</td>
            <td style={{ textAlign: 'right' }}>{row.pending_service_records}</td>
          </tr>
          <tr>
            <td className="muted">Un-Tested Software Tasks</td>
            <td style={{ textAlign: 'right' }}>{row.untested_software_tasks}</td>
          </tr>
          <tr>
            <td className="muted">CM Svc. Records (month / today)</td>
            <td style={{ textAlign: 'right' }}>
              {row.cm_svc_records_month} / {row.cm_svc_records_today}
            </td>
          </tr>
          <tr>
            <td className="muted">CM Svc. Hrs (month / today)</td>
            <td style={{ textAlign: 'right' }}>
              {row.cm_svc_hours_month.toFixed(2)} / {row.cm_svc_hours_today.toFixed(2)}
            </td>
          </tr>
          <tr>
            <td className="muted">Avg. Daily Contract Hrs</td>
            <td style={{ textAlign: 'right' }}>
              <strong>{row.avg_daily_contract_hours.toFixed(2)}</strong>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

export default function SupportMonitoringPage() {
  const [data, setData] = useState<SupportMonitoring | null>(null)
  const [error, setError] = useState<string | null>(null)

  function refresh() {
    api.supportMonitoring().then(setData).catch((e) => setError(e.message))
  }

  useEffect(refresh, [])

  return (
    <div>
      <h1>Support Monitoring</h1>
      <p className="muted">
        Job Order workload and contract-hours throughput per support staff, as at{' '}
        {data ? new Date(data.as_at).toLocaleDateString() : '...'}. "Overdue" only counts Job Orders
        with a due date set -- due dates are set manually by Sales/Coordinator, not automatic.
        <Link to="/job-orders" style={{ marginLeft: 6 }}>
          Set a due date from a Job Order
        </Link>
        .
      </p>
      {error && <div className="error-banner">{error}</div>}

      {data && (
        <div className="card">
          <div className="stat-grid">
            <div className="card stat-tile">
              <div className="stat-value">{data.summary.total_open_job_orders}</div>
              <div className="stat-label">Open Job Orders</div>
            </div>
            <div className="card stat-tile">
              <div className="stat-value">{data.summary.total_overdue_job_orders}</div>
              <div className="stat-label">Overdue</div>
            </div>
            <div className="card stat-tile">
              <div className="stat-value">{data.summary.unassigned_job_orders}</div>
              <div className="stat-label">Unassigned</div>
            </div>
            <div className="card stat-tile">
              <div className="stat-value">{data.summary.total_pending_service_records}</div>
              <div className="stat-label">Pending Service Records</div>
            </div>
            <div className="card stat-tile">
              <div className="stat-value">{data.summary.total_untested_software_tasks}</div>
              <div className="stat-label">Un-Tested Software Tasks</div>
            </div>
            <div className="card stat-tile">
              <div className="stat-value">{data.summary.total_job_orders}</div>
              <div className="stat-label">Total Job Orders</div>
            </div>
          </div>
        </div>
      )}

      {data && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
          {data.unassigned.open_job_orders > 0 && <StaffCard row={data.unassigned} />}
          {data.staff.map((row) => (
            <StaffCard key={row.user_id} row={row} />
          ))}
        </div>
      )}
    </div>
  )
}

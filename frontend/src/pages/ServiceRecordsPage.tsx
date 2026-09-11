import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ExportControl from '../components/ExportControl'
import { api, downloadBlob, type CurrentUser, type JobOrder, type ServiceRecord } from '../lib/api'

export default function ServiceRecordsPage() {
  const [records, setRecords] = useState<ServiceRecord[]>([])
  const [jobOrders, setJobOrders] = useState<JobOrder[]>([])
  const [users, setUsers] = useState<CurrentUser[]>([])
  const [error, setError] = useState<string | null>(null)

  const [filterEmployee, setFilterEmployee] = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  function refresh() {
    api
      .listServiceRecords({ employee_user_id: filterEmployee || undefined, status: filterStatus || undefined })
      .then(setRecords)
      .catch((e) => setError(e.message))
    api.listJobOrders().then(setJobOrders).catch((e) => setError(e.message))
    api.listUsers().then(setUsers).catch((e) => setError(e.message))
  }

  useEffect(refresh, [filterEmployee, filterStatus])

  const userName = (uid: string) => users.find((u) => u.id === uid)?.full_name ?? uid.slice(0, 8)
  const jobOrderSubject = (id: string) => jobOrders.find((j) => j.id === id)?.subject ?? id.slice(0, 8)

  function resetFilters() {
    setFilterEmployee('')
    setFilterStatus('')
  }

  async function onExport(format: string) {
    setError(null)
    const filters = { employee_user_id: filterEmployee || undefined, status: filterStatus || undefined }
    if (format === 'csv') {
      downloadBlob(await api.exportServiceRecordsCsv(filters), 'service-records.csv')
    } else {
      downloadBlob(await api.exportServiceRecordsExcel(filters), 'service-records.xlsx')
    }
  }

  async function onApprove(id: string) {
    setError(null)
    try {
      await api.approveServiceRecord(id)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve')
    }
  }

  return (
    <div>
      <h1>Service Records</h1>
      <p className="muted">
        Time logged against Job Orders (SRV-007: rounds up to the nearest 15 min). To log a new one,
        open the Job Order it belongs to.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="filter-bar">
          <div className="form-row" style={{ margin: 0 }}>
            <label>Employee</label>
            <select value={filterEmployee} onChange={(e) => setFilterEmployee(e.target.value)}>
              <option value="">All</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row" style={{ margin: 0 }}>
            <label>Status</label>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">All</option>
              <option value="submitted">Submitted</option>
              <option value="approved">Approved</option>
            </select>
          </div>
          <button type="button" className="secondary" onClick={resetFilters}>
            Reset filters
          </button>
          <ExportControl
            formats={[
              { value: 'csv', label: 'CSV' },
              { value: 'excel', label: 'Excel' },
            ]}
            onExport={onExport}
            onError={setError}
          />
        </div>

        <h2>Records ({records.length})</h2>
        <table>
          <thead>
            <tr>
              <th>Job Order</th>
              <th>Employee</th>
              <th>Date</th>
              <th>Raw / Rounded</th>
              <th>Status</th>
              <th>Outcome</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.id}>
                <td>
                  <Link to={`/job-orders/${r.job_order_id}`}>{jobOrderSubject(r.job_order_id)}</Link>
                </td>
                <td>{userName(r.employee_user_id)}</td>
                <td>{r.work_date}</td>
                <td>
                  {r.raw_minutes}m &rarr; {r.rounded_minutes}m
                </td>
                <td>
                  {r.status}
                  {r.is_late && (
                    <span className="badge exceeded" style={{ marginLeft: 6 }}>
                      late
                    </span>
                  )}
                </td>
                <td>{r.outcome}</td>
                <td>{r.status === 'submitted' && <button onClick={() => onApprove(r.id)}>Approve</button>}</td>
              </tr>
            ))}
            {records.length === 0 && (
              <tr>
                <td colSpan={7} className="muted">
                  No Service Records match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

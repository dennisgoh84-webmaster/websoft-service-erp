import { useEffect, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { api, type CurrentUser, type ServiceRecord, type JobOrder } from '../lib/api'

export default function JobOrderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [jobOrder, setJobOrder] = useState<JobOrder | null>(null)
  const [records, setRecords] = useState<ServiceRecord[]>([])
  const [users, setUsers] = useState<CurrentUser[]>([])
  const [error, setError] = useState<string | null>(null)

  const [assignee, setAssignee] = useState('')
  const [employee, setEmployee] = useState('')
  const [workDate, setWorkDate] = useState(new Date().toISOString().slice(0, 10))
  const [minutes, setMinutes] = useState('30')
  const [dueDate, setDueDate] = useState('')

  function refresh() {
    if (!id) return
    api.getJobOrder(id).then((jo) => {
      setJobOrder(jo)
      setDueDate(jo.due_date ?? '')
    })
    api.listServiceRecords({ job_order_id: id }).then(setRecords)
    api.listUsers().then(setUsers)
  }

  useEffect(refresh, [id])

  const userName = (uid: string | null) => users.find((u) => u.id === uid)?.full_name ?? '-'

  async function onAssign(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setError(null)
    try {
      await api.assignJobOrder(id, assignee)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign')
    }
  }

  async function onLogRecord(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setError(null)
    try {
      await api.submitServiceRecord({
        job_order_id: id,
        employee_user_id: employee,
        work_date: workDate,
        raw_minutes: parseInt(minutes, 10),
      })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to log service record')
    }
  }

  async function onApprove(recordId: string) {
    setError(null)
    try {
      await api.approveServiceRecord(recordId)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve')
    }
  }

  async function onSetDueDate(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setError(null)
    try {
      await api.setJobOrderDueDate(id, dueDate || null)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set due date')
    }
  }

  if (!jobOrder) return <p>Loading...</p>

  return (
    <div>
      <h1>{jobOrder.subject}</h1>
      <p>
        <span className="muted">{jobOrder.job_order_number}</span>{' '}
        <span className="badge active">{jobOrder.status}</span>{' '}
        <span className="muted">Priority: {jobOrder.priority} (SRV-009: no formal SLA target yet)</span>
        {jobOrder.due_date && (
          <>
            {' '}
            &middot; <span className="muted">Due {jobOrder.due_date}</span>
          </>
        )}
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <h2>Due date</h2>
        <p className="muted">
          Set manually by Sales/Coordinator after discussion with Support -- not derived from
          priority.
        </p>
        <form onSubmit={onSetDueDate} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
          <div className="form-row" style={{ margin: 0 }}>
            <label>Due date</label>
            <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </div>
          <button type="submit">Save</button>
        </form>
      </div>

      <div className="card">
        <h2>Assignment</h2>
        <p>Currently assigned to: {userName(jobOrder.assigned_to_user_id)}</p>
        <form onSubmit={onAssign}>
          <div className="form-row">
            <label>Assign to</label>
            <select value={assignee} onChange={(e) => setAssignee(e.target.value)} required>
              <option value="">Select...</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} ({u.role})
                </option>
              ))}
            </select>
          </div>
          <button type="submit">Assign</button>
        </form>
      </div>

      <div className="card">
        <h2>Log a Service Record (SRV-007: rounds up to nearest 15 min)</h2>
        <form onSubmit={onLogRecord}>
          <div className="form-row">
            <label>Employee</label>
            <select value={employee} onChange={(e) => setEmployee(e.target.value)} required>
              <option value="">Select...</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Work date</label>
            <input type="date" value={workDate} onChange={(e) => setWorkDate(e.target.value)} />
          </div>
          <div className="form-row">
            <label>Minutes worked</label>
            <input type="number" min={1} value={minutes} onChange={(e) => setMinutes(e.target.value)} />
          </div>
          <button type="submit">Submit Service Record</button>
        </form>
      </div>

      <div className="card">
        <h2>Service Records</h2>
        <table>
          <thead>
            <tr>
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
                <td>{userName(r.employee_user_id)}</td>
                <td>{r.work_date}</td>
                <td>
                  {r.raw_minutes}m &rarr; {r.rounded_minutes}m
                </td>
                <td>
                  {r.status}
                  {r.is_late && <span className="badge exceeded" style={{ marginLeft: 6 }}>late</span>}
                </td>
                <td>{r.outcome}</td>
                <td>
                  {r.status === 'submitted' && <button onClick={() => onApprove(r.id)}>Approve</button>}
                </td>
              </tr>
            ))}
            {records.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No Service Records yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

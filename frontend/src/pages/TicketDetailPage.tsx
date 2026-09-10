import { useEffect, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { api, type CurrentUser, type TimesheetEntry, type Ticket } from '../lib/api'

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [ticket, setTicket] = useState<Ticket | null>(null)
  const [entries, setEntries] = useState<TimesheetEntry[]>([])
  const [users, setUsers] = useState<CurrentUser[]>([])
  const [error, setError] = useState<string | null>(null)

  const [assignee, setAssignee] = useState('')
  const [employee, setEmployee] = useState('')
  const [workDate, setWorkDate] = useState(new Date().toISOString().slice(0, 10))
  const [minutes, setMinutes] = useState('30')

  function refresh() {
    if (!id) return
    api.getTicket(id).then(setTicket)
    api.listTimesheets(id).then(setEntries)
    api.listUsers().then(setUsers)
  }

  useEffect(refresh, [id])

  const userName = (uid: string | null) => users.find((u) => u.id === uid)?.full_name ?? '-'

  async function onAssign(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setError(null)
    try {
      await api.assignTicket(id, assignee)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign')
    }
  }

  async function onLogTime(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setError(null)
    try {
      await api.submitTimesheet({
        ticket_id: id,
        employee_user_id: employee,
        work_date: workDate,
        raw_minutes: parseInt(minutes, 10),
      })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to log time')
    }
  }

  async function onApprove(entryId: string) {
    setError(null)
    try {
      await api.approveTimesheet(entryId)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve')
    }
  }

  if (!ticket) return <p>Loading...</p>

  return (
    <div>
      <h1>{ticket.subject}</h1>
      <p>
        <span className="badge active">{ticket.status}</span>{' '}
        <span className="muted">Priority: {ticket.priority} (SRV-009: no formal SLA target yet)</span>
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <h2>Assignment</h2>
        <p>Currently assigned to: {userName(ticket.assigned_to_user_id)}</p>
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
        <h2>Log time (SRV-007: rounds up to nearest 15 min)</h2>
        <form onSubmit={onLogTime}>
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
          <button type="submit">Submit timesheet entry</button>
        </form>
      </div>

      <div className="card">
        <h2>Timesheet entries</h2>
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
            {entries.map((e) => (
              <tr key={e.id}>
                <td>{userName(e.employee_user_id)}</td>
                <td>{e.work_date}</td>
                <td>
                  {e.raw_minutes}m &rarr; {e.rounded_minutes}m
                </td>
                <td>{e.status}</td>
                <td>{e.outcome}</td>
                <td>
                  {e.status === 'submitted' && <button onClick={() => onApprove(e.id)}>Approve</button>}
                </td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No timesheet entries yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

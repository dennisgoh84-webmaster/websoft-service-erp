import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import CompanyAccessCard from '../components/CompanyAccessCard'
import { api, type AuditLogEntry, type StaffUser, type UserRole } from '../lib/api'
import { useAuth } from '../lib/AuthContext'

const ROLES: UserRole[] = ['owner', 'service_lead', 'sales_manager', 'support_engineer', 'finance']

const ACTION_LABELS: Record<string, string> = {
  created: 'Account created',
  updated: 'Profile updated',
  deactivated: 'Deactivated',
  reactivated: 'Reactivated',
  password_reset: 'Password reset',
}

export default function StaffDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user: me } = useAuth()

  const [staff, setStaff] = useState<StaffUser | null>(null)
  const [allStaff, setAllStaff] = useState<StaffUser[]>([])
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState<UserRole>('support_engineer')
  const [saving, setSaving] = useState(false)

  const [newPassword, setNewPassword] = useState('')
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null)

  function refresh() {
    if (!id) return
    api
      .getStaff(id)
      .then((u) => {
        setStaff(u)
        setFullName(u.full_name)
        setRole(u.role)
      })
      .catch(() => setNotFound(true))
    api.getStaffAuditLog(id).then(setAuditLog).catch((e) => setError(e.message))
  }

  useEffect(refresh, [id])
  useEffect(() => {
    api.listStaff(true).then(setAllStaff).catch((e) => setError(e.message))
  }, [])

  function actorName(actorId: string | null) {
    if (!actorId) return 'System'
    return allStaff.find((u) => u.id === actorId)?.full_name ?? actorId.slice(0, 8)
  }

  async function onSave(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setError(null)
    setSaving(true)
    try {
      const updated = await api.updateStaff(id, { full_name: fullName, role })
      setStaff(updated)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  async function onResetPassword(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setError(null)
    setPasswordMessage(null)
    try {
      await api.resetStaffPassword(id, newPassword)
      setNewPassword('')
      setPasswordMessage('Password reset. Share the new password with the staff member securely.')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset password')
    }
  }

  async function onToggleActive() {
    if (!id || !staff) return
    setError(null)
    try {
      if (staff.is_active) await api.deactivateStaff(id)
      else await api.reactivateStaff(id)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update account status')
    }
  }

  if (notFound) return <p>Staff record not found. <Link to="/staff">Back to Staff Master</Link></p>
  if (!staff) return <p>Loading...</p>

  const isSelf = me?.id === staff.id

  return (
    <div>
      <p>
        <Link to="/staff">&larr; Staff Master</Link>
      </p>
      <h1>{staff.full_name}</h1>
      <p>
        <span className={`badge ${staff.is_active ? 'active' : 'draft'}`}>
          {staff.is_active ? 'Active' : 'Deactivated'}
        </span>{' '}
        <span className="muted">
          {staff.email} &middot; joined {new Date(staff.created_at).toLocaleDateString()}
        </span>
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <h2>Profile</h2>
        <form onSubmit={onSave}>
          <div className="form-row">
            <label>Full name</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </div>
          <div className="form-row">
            <label>Email</label>
            <input value={staff.email} disabled title="Email cannot be changed here." />
          </div>
          <div className="form-row">
            <label>Role (named-responsibility rules only, e.g. SRV-004/SRV-011)</label>
            <select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <p className="muted">
            Group Authority (general module access) is set per company below, since a Group belongs
            to a single company.
          </p>
          <button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save changes'}
          </button>
        </form>
      </div>

      {id && <CompanyAccessCard userId={id} />}

      <div className="card">
        <h2>Password</h2>
        <form onSubmit={onResetPassword}>
          <div className="form-row">
            <label>New password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              minLength={8}
              placeholder="Min. 8 characters"
              required
            />
          </div>
          <button type="submit">Reset password</button>
        </form>
        {passwordMessage && <p className="muted" style={{ marginTop: 10 }}>{passwordMessage}</p>}
      </div>

      <div className="card">
        <h2>Account status</h2>
        <p className="muted">
          Deactivating a staff account keeps their history intact but immediately blocks login and
          Group Authority access (per CLAUDE.md: never permanently delete business records).
        </p>
        <button
          className="secondary"
          disabled={isSelf}
          title={isSelf ? 'You cannot deactivate your own account.' : undefined}
          onClick={onToggleActive}
        >
          {staff.is_active ? 'Deactivate account' : 'Reactivate account'}
        </button>
      </div>

      <div className="card">
        <h2>Recent activity</h2>
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Action</th>
              <th>By</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {auditLog.map((entry) => (
              <tr key={entry.id}>
                <td>{new Date(entry.at).toLocaleString()}</td>
                <td>{ACTION_LABELS[entry.action] ?? entry.action}</td>
                <td>{actorName(entry.actor_user_id)}</td>
                <td className="muted">{entry.details ?? entry.reason ?? '-'}</td>
              </tr>
            ))}
            {auditLog.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  No activity recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <button className="secondary" onClick={() => navigate('/staff')}>
        Back to Staff Master
      </button>
    </div>
  )
}

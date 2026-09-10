import { useEffect, useState, type FormEvent } from 'react'
import { api, type Group, type StaffUser, type UserRole } from '../lib/api'

const ROLES: UserRole[] = ['owner', 'service_lead', 'sales_manager', 'support_engineer', 'finance']

export default function StaffMasterPage() {
  const [staff, setStaff] = useState<StaffUser[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [showInactive, setShowInactive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('support_engineer')
  const [groupId, setGroupId] = useState('')

  function refresh() {
    api
      .listStaff(showInactive)
      .then(setStaff)
      .catch((e) => setError(e.message))
  }

  useEffect(refresh, [showInactive])
  useEffect(() => {
    api.listGroups().then(setGroups).catch((e) => setError(e.message))
  }, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await api.createStaff({
        full_name: fullName,
        email,
        password,
        role,
        group_id: groupId || null,
      })
      setFullName('')
      setEmail('')
      setPassword('')
      setRole('support_engineer')
      setGroupId('')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create staff account')
    }
  }

  async function onRoleChange(id: string, newRole: UserRole) {
    setError(null)
    try {
      await api.updateStaff(id, { role: newRole })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role')
    }
  }

  async function onGroupChange(id: string, newGroupId: string) {
    setError(null)
    try {
      await api.updateStaff(id, { group_id: newGroupId || null })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update group')
    }
  }

  async function onToggleActive(u: StaffUser) {
    setError(null)
    try {
      if (u.is_active) await api.deactivateStaff(u.id)
      else await api.reactivateStaff(u.id)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update account status')
    }
  }

  async function onResetPassword(id: string) {
    const newPassword = window.prompt('New password (min 8 characters):')
    if (!newPassword) return
    setError(null)
    try {
      await api.resetStaffPassword(id, newPassword)
      window.alert('Password reset.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset password')
    }
  }

  return (
    <div>
      <h1>Staff Master</h1>
      <p className="muted">
        Every staff account, their Role (used only for the specific named-responsibility rules,
        e.g. who decides excess usage) and their Group (Group Authority -- general module access).
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <h2>Add staff</h2>
        <form onSubmit={onCreate}>
          <div className="form-row">
            <label>Full name</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </div>
          <div className="form-row">
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="form-row">
            <label>Temporary password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </div>
          <div className="form-row">
            <label>Role (named-responsibility rules only)</label>
            <select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Group (Group Authority)</label>
            <select value={groupId} onChange={(e) => setGroupId(e.target.value)}>
              <option value="">No group</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>
          <button type="submit">Add staff</button>
        </form>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>All staff</h2>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            Show deactivated
          </label>
        </div>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Group</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {staff.map((u) => (
              <tr key={u.id} style={{ opacity: u.is_active ? 1 : 0.6 }}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>
                  <select value={u.role} onChange={(e) => onRoleChange(u.id, e.target.value as UserRole)}>
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <select value={u.group_id ?? ''} onChange={(e) => onGroupChange(u.id, e.target.value)}>
                    <option value="">No group</option>
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td>{u.is_active ? 'Active' : 'Deactivated'}</td>
                <td style={{ display: 'flex', gap: 8 }}>
                  <button className="secondary" onClick={() => onResetPassword(u.id)}>
                    Reset password
                  </button>
                  <button className="secondary" onClick={() => onToggleActive(u)}>
                    {u.is_active ? 'Deactivate' : 'Reactivate'}
                  </button>
                </td>
              </tr>
            ))}
            {staff.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No staff found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

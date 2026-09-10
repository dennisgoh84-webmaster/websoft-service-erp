import { useEffect, useState } from 'react'
import { api, type Group, type UserCompanyAccess } from '../lib/api'
import { useAuth } from '../lib/AuthContext'

/** Per-company access and Group for one staff member.
 *
 * A Group applies to one company only, so a staff member holds a Group
 * *per company* they work in -- this is where both are managed: tick the
 * companies they may work in, and pick their Group in each. */
export default function CompanyAccessCard({ userId }: { userId: string }) {
  const { companies, user: me } = useAuth()
  const [access, setAccess] = useState<UserCompanyAccess[]>([])
  const [groupsByCompany, setGroupsByCompany] = useState<Record<string, Group[]>>({})
  const [draft, setDraft] = useState<Record<string, string | null>>({})
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  function load() {
    api
      .getStaffCompanyAccess(userId)
      .then((rows) => {
        setAccess(rows)
        const next: Record<string, string | null> = {}
        rows.forEach((r) => {
          next[r.company_id] = r.group_id
        })
        setDraft(next)
      })
      .catch((e) => setError(e.message))
  }

  useEffect(load, [userId])

  // Each company's Groups are its own, so load them per company.
  useEffect(() => {
    companies.forEach((c) => {
      api
        .listGroups(c.id)
        .then((gs) => setGroupsByCompany((prev) => ({ ...prev, [c.id]: gs })))
        .catch(() => {
          /* a company whose groups we can't read just shows no options */
        })
    })
  }, [companies])

  function toggleCompany(companyId: string, hasAccess: boolean) {
    setSaved(false)
    setDraft((prev) => {
      const next = { ...prev }
      if (hasAccess) next[companyId] = next[companyId] ?? null
      else delete next[companyId]
      return next
    })
  }

  function setGroup(companyId: string, groupId: string) {
    setSaved(false)
    setDraft((prev) => ({ ...prev, [companyId]: groupId || null }))
  }

  async function onSave() {
    setError(null)
    setSaved(false)
    setSaving(true)
    try {
      const payload = Object.entries(draft).map(([company_id, group_id]) => ({
        company_id,
        group_id,
      }))
      await api.setStaffCompanyAccess(userId, payload)
      setSaved(true)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save company access')
    } finally {
      setSaving(false)
    }
  }

  const isSelf = me?.id === userId

  return (
    <div className="card">
      <h2>Company access &amp; Groups</h2>
      <p className="muted">
        Which companies this staff member may work in, and their Group in each. Groups belong to a
        single company, so someone working across entities holds a separate Group in each. Staff
        with more than one company get the company switcher in the top bar.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Access</th>
            <th>Group in this company</th>
          </tr>
        </thead>
        <tbody>
          {companies.map((c) => {
            const hasAccess = c.id in draft
            const groups = groupsByCompany[c.id] ?? []
            const current = access.find((a) => a.company_id === c.id)
            return (
              <tr key={c.id}>
                <td>
                  {c.name}
                  {current && current.group_name && (
                    <div className="muted">currently: {current.group_name}</div>
                  )}
                </td>
                <td>
                  <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <input
                      type="checkbox"
                      checked={hasAccess}
                      onChange={(e) => toggleCompany(c.id, e.target.checked)}
                    />
                    {hasAccess ? 'Yes' : 'No'}
                  </label>
                </td>
                <td>
                  <select
                    value={draft[c.id] ?? ''}
                    disabled={!hasAccess}
                    onChange={(e) => setGroup(c.id, e.target.value)}
                  >
                    <option value="">No group</option>
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.name}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            )
          })}
          {companies.length === 0 && (
            <tr>
              <td colSpan={3} className="muted">
                No companies available.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <button style={{ marginTop: 14 }} disabled={saving} onClick={onSave}>
        {saving ? 'Saving...' : 'Save company access'}
      </button>
      {saved && (
        <span className="muted" style={{ marginLeft: 10 }}>
          Saved.
        </span>
      )}
      {isSelf && (
        <p className="muted" style={{ marginTop: 10 }}>
          This is your own account -- you cannot remove yourself from the company you are currently
          working in.
        </p>
      )}
    </div>
  )
}

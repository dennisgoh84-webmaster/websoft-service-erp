// GL Types -- a finer classification within the 5 account_type classes
// that a Chart of Accounts entry can optionally carry. Same list +
// inline-edit + add-form pattern as Chart of Accounts.
import { useEffect, useState, type FormEvent } from 'react'
import { api, type AccountType, type GLType } from '../lib/api'

const TYPES: AccountType[] = ['asset', 'liability', 'equity', 'revenue', 'expense']

export default function GLTypesPage() {
  const [glTypes, setGlTypes] = useState<GLType[]>([])
  const [showInactive, setShowInactive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [accountType, setAccountType] = useState<AccountType>('asset')
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Record<string, string>>({})

  function refresh() {
    api.listGLTypes(showInactive).then(setGlTypes).catch((e) => setError(e.message))
  }

  useEffect(refresh, [showInactive])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setCreating(true)
    try {
      await api.createGLType({ code, name, account_type: accountType })
      setCode('')
      setName('')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create GL type')
    } finally {
      setCreating(false)
    }
  }

  async function onRename(glType: GLType) {
    const newName = editing[glType.id]
    if (!newName || newName === glType.name) return
    setError(null)
    try {
      await api.updateGLType(glType.id, { name: newName })
      setEditing((prev) => ({ ...prev, [glType.id]: '' }))
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename GL type')
    }
  }

  async function onToggleActive(glType: GLType) {
    setError(null)
    try {
      await api.updateGLType(glType.id, { is_active: !glType.is_active })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update GL type')
    }
  }

  return (
    <div>
      <h1>GL Types</h1>
      <p className="muted">
        An optional finer classification within Asset/Liability/Equity/Revenue/Expense (e.g. "Bank",
        "Fixed Asset", "Current Liability") that an account in the Chart of Accounts can carry for
        reporting/grouping. Purely a label -- it never changes an account's own account_type or the
        ledger.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="filter-bar">
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />
            Show retired
          </label>
        </div>

        <h2>GL Types ({glTypes.length})</h2>
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Account Type</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {glTypes.map((g) => (
              <tr key={g.id} style={{ opacity: g.is_active ? 1 : 0.6 }}>
                <td>{g.code}</td>
                <td>
                  <input
                    value={editing[g.id] ?? g.name}
                    onChange={(e) => setEditing((prev) => ({ ...prev, [g.id]: e.target.value }))}
                    onBlur={() => onRename(g)}
                    style={{ width: '100%', minWidth: 220 }}
                  />
                </td>
                <td>{g.account_type}</td>
                <td>
                  <span className={`badge ${g.is_active ? 'active' : 'draft'}`}>
                    {g.is_active ? 'Active' : 'Retired'}
                  </span>
                </td>
                <td>
                  <button className="secondary" onClick={() => onToggleActive(g)}>
                    {g.is_active ? 'Retire' : 'Reinstate'}
                  </button>
                </td>
              </tr>
            ))}
            {glTypes.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No GL types yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Add a GL Type</h2>
        <form onSubmit={onCreate}>
          <div className="form-row">
            <label>Code</label>
            <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. BANK" required />
          </div>
          <div className="form-row">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Bank" required />
          </div>
          <div className="form-row">
            <label>Account Type</label>
            <select value={accountType} onChange={(e) => setAccountType(e.target.value as AccountType)}>
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={creating}>
            {creating ? 'Adding...' : 'Add GL Type'}
          </button>
        </form>
      </div>
    </div>
  )
}

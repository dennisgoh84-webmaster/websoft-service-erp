import { useEffect, useState, type FormEvent } from 'react'
import ExportControl from '../components/ExportControl'
import { api, downloadBlob, type Account, type AccountType } from '../lib/api'

const TYPES: AccountType[] = ['asset', 'liability', 'equity', 'revenue', 'expense']

export default function ChartOfAccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [showInactive, setShowInactive] = useState(false)
  const [filterType, setFilterType] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [accountType, setAccountType] = useState<AccountType>('expense')
  const [creating, setCreating] = useState(false)

  const [editing, setEditing] = useState<Record<string, string>>({})

  function refresh() {
    api
      .listAccounts({ include_inactive: showInactive, account_type: filterType || undefined })
      .then(setAccounts)
      .catch((e) => setError(e.message))
  }

  useEffect(refresh, [showInactive, filterType])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setCreating(true)
    try {
      await api.createAccount({ code, name, account_type: accountType })
      setCode('')
      setName('')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create account')
    } finally {
      setCreating(false)
    }
  }

  async function onRename(account: Account) {
    const newName = editing[account.id]
    if (!newName || newName === account.name) return
    setError(null)
    try {
      await api.updateAccount(account.id, { name: newName })
      setEditing((prev) => ({ ...prev, [account.id]: '' }))
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename account')
    }
  }

  async function onExport(format: string) {
    setError(null)
    const filters = { include_inactive: showInactive, account_type: filterType || undefined }
    if (format === 'csv') {
      downloadBlob(await api.exportAccountsCsv(filters), 'chart-of-accounts.csv')
    } else {
      downloadBlob(await api.exportAccountsExcel(filters), 'chart-of-accounts.xlsx')
    }
  }

  async function onToggleActive(account: Account) {
    setError(null)
    try {
      await api.updateAccount(account.id, { is_active: !account.is_active })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update account')
    }
  }

  return (
    <div>
      <h1>Chart of Accounts</h1>
      <p className="muted">
        A conventional Singapore SME chart, seeded as a starting point -- rename, add to or retire
        anything here so it matches how Webmaster actually wants its books structured. Accounts are
        retired rather than deleted, so past entries stay readable. Posting transactions into a
        general ledger against these accounts comes with the Finance / Accounting module.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="filter-bar">
          <div className="form-row" style={{ margin: 0 }}>
            <label>Type</label>
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="">All</option>
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            Show retired
          </label>
          <ExportControl
            formats={[
              { value: 'csv', label: 'CSV' },
              { value: 'excel', label: 'Excel' },
            ]}
            onExport={onExport}
            onError={setError}
          />
        </div>

        <h2>Accounts ({accounts.length})</h2>
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id} style={{ opacity: a.is_active ? 1 : 0.6 }}>
                <td>{a.code}</td>
                <td>
                  <input
                    value={editing[a.id] ?? a.name}
                    onChange={(e) => setEditing((prev) => ({ ...prev, [a.id]: e.target.value }))}
                    onBlur={() => onRename(a)}
                    style={{ width: '100%', minWidth: 220 }}
                  />
                </td>
                <td>{a.account_type}</td>
                <td>
                  <span className={`badge ${a.is_active ? 'active' : 'draft'}`}>
                    {a.is_active ? 'Active' : 'Retired'}
                  </span>
                </td>
                <td>
                  <button className="secondary" onClick={() => onToggleActive(a)}>
                    {a.is_active ? 'Retire' : 'Reinstate'}
                  </button>
                </td>
              </tr>
            ))}
            {accounts.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No accounts match.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Add an account</h2>
        <form onSubmit={onCreate}>
          <div className="form-row">
            <label>Account code</label>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. 6800"
              required
            />
          </div>
          <div className="form-row">
            <label>Account name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="form-row">
            <label>Type</label>
            <select
              value={accountType}
              onChange={(e) => setAccountType(e.target.value as AccountType)}
            >
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={creating}>
            {creating ? 'Adding...' : 'Add account'}
          </button>
        </form>
      </div>
    </div>
  )
}

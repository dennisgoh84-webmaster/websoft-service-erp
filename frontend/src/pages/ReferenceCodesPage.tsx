import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import ExportControl from '../components/ExportControl'
import { api, downloadBlob, type Account, type ReferenceCode } from '../lib/api'

export default function ReferenceCodesPage() {
  const [codes, setCodes] = useState<ReferenceCode[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [showInactive, setShowInactive] = useState(false)
  const [filterAccount, setFilterAccount] = useState('')
  const [error, setError] = useState<string | null>(null)

  const [accountId, setAccountId] = useState('')
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [creating, setCreating] = useState(false)

  const [editing, setEditing] = useState<Record<string, string>>({})

  function refresh() {
    api
      .listReferenceCodes({ include_inactive: showInactive, account_id: filterAccount || undefined })
      .then(setCodes)
      .catch((e) => setError(e.message))
  }

  useEffect(refresh, [showInactive, filterAccount])
  useEffect(() => {
    api.listAccounts().then(setAccounts).catch((e) => setError(e.message))
  }, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setCreating(true)
    try {
      await api.createReferenceCode({ account_id: accountId, code, name })
      setCode('')
      setName('')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create reference code')
    } finally {
      setCreating(false)
    }
  }

  async function onRename(rc: ReferenceCode) {
    const newName = editing[rc.id]
    if (!newName || newName === rc.name) return
    setError(null)
    try {
      await api.updateReferenceCode(rc.id, { name: newName })
      setEditing((prev) => ({ ...prev, [rc.id]: '' }))
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename reference code')
    }
  }

  async function onToggleActive(rc: ReferenceCode) {
    setError(null)
    try {
      await api.updateReferenceCode(rc.id, { is_active: !rc.is_active })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update reference code')
    }
  }

  async function onExport(format: string) {
    setError(null)
    const filters = { include_inactive: showInactive, account_id: filterAccount || undefined }
    if (format === 'csv') {
      downloadBlob(await api.exportReferenceCodesCsv(filters), 'reference-codes.csv')
    } else {
      downloadBlob(await api.exportReferenceCodesExcel(filters), 'reference-codes.xlsx')
    }
  }

  return (
    <div>
      <h1>Reference Monitor</h1>
      <p className="muted">
        Sub-codes of one Chart of Accounts row -- e.g. GL 45001 "Sales of Software Revenue" broken
        down into SLS-WEBSOFT-IMPLEMENTATION, SLS-WEBSOFT-SERVICE, SLS-WEBSOFT-STOCK and
        SLS-WEBSOFT-CUSTOMIZATIONS, all posting to the same account. Preset a default on the{' '}
        <Link to="/product-catalog">Product Catalog</Link> so a Sales Quotation line picks it up
        automatically (still overridable per line). Actual posting from documents into General
        Ledger transactions doesn't exist yet for any document type here -- Journal Vouchers are
        entered manually only -- so a captured reference code is recorded for now, not yet summed
        into the ledger; see docs/open-business-decisions.md.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="filter-bar">
          <div className="form-row" style={{ margin: 0, minWidth: 220 }}>
            <label>Chart of Accounts code</label>
            <select value={filterAccount} onChange={(e) => setFilterAccount(e.target.value)}>
              <option value="">All</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.code} -- {a.name}
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
            Show inactive
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

        <h2>Reference codes ({codes.length})</h2>
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Chart of Accounts</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {codes.map((rc) => (
              <tr key={rc.id} style={{ opacity: rc.is_active ? 1 : 0.6 }}>
                <td>{rc.code}</td>
                <td>
                  <input
                    value={editing[rc.id] ?? rc.name}
                    onChange={(e) => setEditing((prev) => ({ ...prev, [rc.id]: e.target.value }))}
                    onBlur={() => onRename(rc)}
                    style={{ width: '100%', minWidth: 220 }}
                  />
                </td>
                <td className="muted">
                  {rc.account_code} -- {rc.account_name}
                </td>
                <td>
                  <span className={`badge ${rc.is_active ? 'active' : 'draft'}`}>
                    {rc.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>
                  <button className="secondary" onClick={() => onToggleActive(rc)}>
                    {rc.is_active ? 'Deactivate' : 'Reactivate'}
                  </button>
                </td>
              </tr>
            ))}
            {codes.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No reference codes match.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Add a reference code</h2>
        <form onSubmit={onCreate}>
          <div className="form-row">
            <label>Chart of Accounts code</label>
            <select value={accountId} onChange={(e) => setAccountId(e.target.value)} required>
              <option value="">Select...</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.code} -- {a.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Reference code</label>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. SLS-WEBSOFT-IMPLEMENTATION"
              required
            />
          </div>
          <div className="form-row">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <button type="submit" disabled={creating || !accountId}>
            {creating ? 'Adding...' : 'Add reference code'}
          </button>
        </form>
      </div>
    </div>
  )
}

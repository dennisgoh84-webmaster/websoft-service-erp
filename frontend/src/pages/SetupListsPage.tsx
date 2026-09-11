// Setup Lists -- Nationality, Country, State, Area Code, Currency
// codes. Global reference data, shared by every company (see
// app/models/setup.py): one generic list_type selector + table rather
// than five near-identical pages.
import { useEffect, useState, type FormEvent } from 'react'
import ExportControl from '../components/ExportControl'
import { api, downloadBlob, type SetupListItem, type SetupListType } from '../lib/api'

const LIST_TYPES: { value: SetupListType; label: string }[] = [
  { value: 'nationality', label: 'Nationality' },
  { value: 'country', label: 'Country' },
  { value: 'state', label: 'State / Province' },
  { value: 'area_code', label: 'Area Code' },
  { value: 'currency', label: 'Currency' },
]

export default function SetupListsPage() {
  const [listType, setListType] = useState<SetupListType>('country')
  const [items, setItems] = useState<SetupListItem[]>([])
  const [countries, setCountries] = useState<SetupListItem[]>([])
  const [showInactive, setShowInactive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [parentCode, setParentCode] = useState('')
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Record<string, string>>({})

  function refresh() {
    api.listSetupItems({ list_type: listType, include_inactive: showInactive }).then(setItems).catch((e) => setError(e.message))
  }

  useEffect(refresh, [listType, showInactive])
  useEffect(() => {
    // Needed for State's "which Country" picker regardless of the
    // currently-selected list_type.
    api.listSetupItems({ list_type: 'country' }).then(setCountries).catch(() => setCountries([]))
  }, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setCreating(true)
    try {
      await api.createSetupItem({
        list_type: listType,
        code: code.toUpperCase(),
        name,
        parent_code: listType === 'state' ? parentCode || null : null,
      })
      setCode('')
      setName('')
      setParentCode('')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add item')
    } finally {
      setCreating(false)
    }
  }

  async function onRename(item: SetupListItem) {
    const newName = editing[item.id]
    if (!newName || newName === item.name) return
    setError(null)
    try {
      await api.updateSetupItem(item.id, { name: newName })
      setEditing((prev) => ({ ...prev, [item.id]: '' }))
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename item')
    }
  }

  async function onToggleActive(item: SetupListItem) {
    setError(null)
    try {
      await api.updateSetupItem(item.id, { is_active: !item.is_active })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update item')
    }
  }

  async function onExport(format: string) {
    setError(null)
    const filters = { list_type: listType, include_inactive: showInactive }
    const blob = format === 'csv' ? await api.exportSetupItemsCsv(filters) : await api.exportSetupItemsExcel(filters)
    downloadBlob(blob, `${listType}.${format === 'csv' ? 'csv' : 'xlsx'}`)
  }

  const countryName = (parentCode: string | null) => {
    if (!parentCode) return '-'
    return countries.find((c) => c.code === parentCode)?.name ?? parentCode
  }

  return (
    <div>
      <h1>Setup Lists</h1>
      <p className="muted">
        General reference data shared by every company -- Nationality, Country, State/Province, Area
        Code and Currency codes.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="filter-bar">
          <div className="form-row" style={{ margin: 0 }}>
            <label>List</label>
            <select value={listType} onChange={(e) => setListType(e.target.value as SetupListType)}>
              {LIST_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />
            Show inactive
          </label>
          <ExportControl formats={[{ value: 'csv', label: 'CSV' }, { value: 'excel', label: 'Excel' }]} onExport={onExport} onError={setError} />
        </div>

        <h2>
          {LIST_TYPES.find((t) => t.value === listType)?.label} ({items.length})
        </h2>
        <div className="report-table-wrap" style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                {listType === 'state' && <th>Country</th>}
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} style={{ opacity: item.is_active ? 1 : 0.6 }}>
                  <td>{item.code}</td>
                  <td>
                    <input
                      value={editing[item.id] ?? item.name}
                      onChange={(e) => setEditing((prev) => ({ ...prev, [item.id]: e.target.value }))}
                      onBlur={() => onRename(item)}
                      style={{ width: '100%', minWidth: 200 }}
                    />
                  </td>
                  {listType === 'state' && <td>{countryName(item.parent_code)}</td>}
                  <td>
                    <span className={`badge ${item.is_active ? 'active' : 'draft'}`}>
                      {item.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <button className="secondary" onClick={() => onToggleActive(item)}>
                      {item.is_active ? 'Deactivate' : 'Reactivate'}
                    </button>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={listType === 'state' ? 4 : 3} className="muted">
                    Nothing set up yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2>Add to {LIST_TYPES.find((t) => t.value === listType)?.label}</h2>
        <form onSubmit={onCreate}>
          <div className="form-row">
            <label>Code</label>
            <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. SG" required />
          </div>
          <div className="form-row">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Singapore" required />
          </div>
          {listType === 'state' && (
            <div className="form-row">
              <label>Country</label>
              <select value={parentCode} onChange={(e) => setParentCode(e.target.value)} required>
                <option value="">Select a country</option>
                {countries.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <button type="submit" disabled={creating}>
            {creating ? 'Adding...' : 'Add'}
          </button>
        </form>
      </div>
    </div>
  )
}

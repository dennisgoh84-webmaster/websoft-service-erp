import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { api, type Company } from '../lib/api'
import { useAuth } from '../lib/AuthContext'

const MAX_LOGO_BYTES = 300 * 1024

function CompanyCard({ company, onSaved }: { company: Company; onSaved: () => void }) {
  const { user } = useAuth()
  const [name, setName] = useState(company.name)
  const [country, setCountry] = useState(company.country)
  const [currency, setCurrency] = useState(company.currency)
  const [timezone, setTimezone] = useState(company.timezone)
  const [address, setAddress] = useState(company.address ?? '')
  const [gstNo, setGstNo] = useState(company.gst_registration_no ?? '')
  const [writeOffThreshold, setWriteOffThreshold] = useState(
    company.write_off_approval_threshold_sgd?.toString() ?? '',
  )
  const [logo, setLogo] = useState<string | null>(company.logo)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const isActiveCompany = user?.company_id === company.id

  function onPickLogo(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    if (!file.type.startsWith('image/')) {
      setError('Please choose an image file.')
      return
    }
    if (file.size > MAX_LOGO_BYTES) {
      setError('That image is too large -- please use one under 300 KB.')
      return
    }
    const reader = new FileReader()
    reader.onload = () => setLogo(reader.result as string)
    reader.onerror = () => setError('Could not read that file.')
    reader.readAsDataURL(file)
  }

  async function onSave(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSaved(false)
    setSaving(true)
    try {
      await api.updateCompany(company.id, {
        name,
        country,
        currency,
        timezone,
        logo,
        address: address || null,
        gst_registration_no: gstNo || null,
        write_off_approval_threshold_sgd:
          writeOffThreshold === '' ? null : parseFloat(writeOffThreshold),
      })
      setSaved(true)
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save company')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card">
      <h2>
        {company.name}
        {isActiveCompany && (
          <span className="badge active" style={{ marginLeft: 8 }}>
            currently active
          </span>
        )}
      </h2>
      {error && <div className="error-banner">{error}</div>}
      <form onSubmit={onSave}>
        <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div>
            <div className="form-row">
              <label>Logo (shown at the top-left)</label>
              <div
                style={{
                  width: 96,
                  height: 96,
                  border: '1px solid var(--border)',
                  borderRadius: 10,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                  background: 'var(--bg)',
                }}
              >
                {logo ? (
                  <img
                    src={logo}
                    alt={`${company.name} logo`}
                    style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                  />
                ) : (
                  <span className="muted">No logo</span>
                )}
              </div>
            </div>
            <input type="file" accept="image/*" onChange={onPickLogo} />
            {logo && (
              <button
                type="button"
                className="secondary"
                style={{ marginTop: 8, display: 'block' }}
                onClick={() => setLogo(null)}
              >
                Remove logo
              </button>
            )}
          </div>

          <div style={{ flex: 1, minWidth: 260 }}>
            <div className="form-row">
              <label>Company name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="form-row">
              <label>Country</label>
              <input value={country} onChange={(e) => setCountry(e.target.value)} />
            </div>
            <div className="form-row">
              <label>Currency</label>
              <input
                value={currency}
                onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                maxLength={3}
              />
            </div>
            <div className="form-row">
              <label>Timezone</label>
              <input value={timezone} onChange={(e) => setTimezone(e.target.value)} />
            </div>
            <div className="form-row">
              <label>Registered address (shown on tax invoices)</label>
              <input value={address} onChange={(e) => setAddress(e.target.value)} />
            </div>
            <div className="form-row">
              <label>GST registration number (shown on tax invoices)</label>
              <input
                value={gstNo}
                onChange={(e) => setGstNo(e.target.value)}
                placeholder="Leave blank if not GST-registered"
              />
            </div>
            <div className="form-row">
              <label>Write-off approval threshold (SGD)</label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={writeOffThreshold}
                onChange={(e) => setWriteOffThreshold(e.target.value)}
                placeholder="Blank = every write-off needs owner approval"
              />
              <span className="muted">
                AR-002: Finance may write off below this; above it, the owner approves. Blank means
                the threshold has not been decided, so the owner approves every write-off.
              </span>
            </div>
            <button type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Save company'}
            </button>
            {saved && (
              <span className="muted" style={{ marginLeft: 10 }}>
                Saved.
              </span>
            )}
          </div>
        </div>
      </form>
    </div>
  )
}

export default function CompanySetupPage() {
  const { companies, refresh } = useAuth()
  const [list, setList] = useState<Company[]>([])
  const [error, setError] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)

  function reload() {
    api.listMyCompanies().then(setList).catch((e) => setError(e.message))
    refresh()
  }

  useEffect(() => {
    setList(companies)
  }, [companies])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setCreating(true)
    try {
      await api.createCompany({ name: newName })
      setNewName('')
      reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create company')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div>
      <h1>Company Setup</h1>
      <p className="muted">
        The legal entities running in this system. Each company has its own logo, customers,
        contracts, job orders, invoices, staff, groups and event logs -- and its own module mix
        under Module Control. Staff with access to more than one company get a company switcher in
        the top bar; everything they see is scoped to whichever company is active.
      </p>
      {error && <div className="error-banner">{error}</div>}

      {list.map((c) => (
        <CompanyCard key={c.id} company={c} onSaved={reload} />
      ))}

      <div className="card">
        <h2>Add a company</h2>
        <p className="muted">
          A new company starts with the same module catalog (built modules enabled), no customers or
          contracts of its own, and you added as a user who can switch into it. Set its logo and
          details above once created.
        </p>
        <form onSubmit={onCreate}>
          <div className="form-row">
            <label>Company name</label>
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. Websoft Digital Pte Ltd"
              required
            />
          </div>
          <button type="submit" disabled={creating}>
            {creating ? 'Creating...' : 'Create company'}
          </button>
        </form>
      </div>
    </div>
  )
}

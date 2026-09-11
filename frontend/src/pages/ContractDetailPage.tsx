import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type Contract, type ExcessUsageRecord, type Invoice, type Product, type StaffUser } from '../lib/api'

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [contract, setContract] = useState<Contract | null>(null)
  const [excessUsage, setExcessUsage] = useState<ExcessUsageRecord[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [staff, setStaff] = useState<StaffUser[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [renewHours, setRenewHours] = useState('10')
  const [renewValue, setRenewValue] = useState('2400')
  const [renewRate, setRenewRate] = useState('150')

  const [editingCoverage, setEditingCoverage] = useState(false)
  const [salesStaffId, setSalesStaffId] = useState('')
  const [productIds, setProductIds] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  function refresh() {
    if (!id) return
    api.getContract(id).then((c) => {
      setContract(c)
      setSalesStaffId(c.sales_staff_id ?? '')
      setProductIds(c.products.map((p) => p.product_id))
    })
    api.listContractExcessUsage(id).then(setExcessUsage)
    api.listInvoices({ contract_id: id }).then(setInvoices)
    api.listStaff().then(setStaff)
    api.listCatalog().then(setProducts)
  }

  useEffect(refresh, [id])

  async function onActivate() {
    if (!id) return
    setError(null)
    try {
      await api.activateContract(id)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate')
    }
  }

  async function onRenew(e: FormEvent) {
    e.preventDefault()
    if (!id || !contract) return
    setError(null)
    try {
      await api.renewContract(id, {
        contracted_hours: parseFloat(renewHours),
        contract_value_sgd: contract.contract_kind === 'ad_hoc' ? 0 : parseFloat(renewValue),
        hourly_rate_sgd: contract.contract_kind === 'ad_hoc' ? parseFloat(renewRate) : null,
      })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to renew')
    }
  }

  async function onSaveCoverage(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setError(null)
    setMessage(null)
    setSaving(true)
    try {
      await api.updateContract(id, { sales_staff_id: salesStaffId || null, product_ids: productIds })
      setMessage('Sales staff / product coverage updated.')
      setEditingCoverage(false)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update')
    } finally {
      setSaving(false)
    }
  }

  if (!contract) return <p>Loading...</p>

  const isAnnual = contract.contract_kind === 'annual'
  const isAdHoc = contract.contract_kind === 'ad_hoc'
  const isHourMetered = contract.contract_kind === 'service_support'
  const pctUsed = isHourMetered ? Math.min(100, (contract.consumed_hours / contract.contracted_hours) * 100) : 0
  const staffName = (uid: string | null) => (uid ? staff.find((s) => s.id === uid)?.full_name ?? uid.slice(0, 8) : null)
  const kindLabel = isAdHoc ? 'Ad Hoc Rate (billed as you go)' : isAnnual ? 'Annual (time coverage)' : 'Service Support (deduct hrs)'

  return (
    <div>
      <h1>Contract {contract.contract_number}</h1>
      <p>
        <span className={`badge ${contract.status}`}>{contract.status}</span>{' '}
        <span className="muted">
          {kindLabel} &middot; {contract.start_date} &rarr; {contract.end_date}
        </span>
      </p>
      {error && <div className="error-banner">{error}</div>}
      {message && (
        <p className="muted" style={{ marginBottom: 12 }}>
          {message}
        </p>
      )}

      <div className="card">
        {isAdHoc ? (
          <>
            <h2>Ad Hoc Rate (no pre-paid hours or value)</h2>
            <p className="muted">
              Job Orders and Service Records can still be logged against it, for history -- nothing
              is deducted, exceeded, or auto-invoiced. Bill manually off the reference rate below.
            </p>
            <p>
              <strong>Reference rate: SGD {contract.hourly_rate_sgd?.toFixed(2)}/hr</strong>
            </p>
          </>
        ) : isAnnual ? (
          <>
            <h2>Time Coverage (no hours)</h2>
            <p className="muted">
              An Annual contract has a term and a value but no contracted hours -- Job Orders and
              Service Records can still be logged against it, they just aren't deducted from
              anything.
            </p>
            <p>
              <strong>Contract value: SGD {contract.contract_value_sgd.toFixed(2)}</strong>
            </p>
          </>
        ) : (
          <>
            <h2>Hours (SRV-001 / SRV-002 / SRV-004)</h2>
            <div className="progress-bar">
              <div style={{ width: `${pctUsed}%` }} />
            </div>
            <p>
              {contract.consumed_hours.toFixed(2)} used / {contract.contracted_hours.toFixed(2)} contracted --{' '}
              <strong>{contract.remaining_hours.toFixed(2)} hrs remaining</strong> (never goes negative)
            </p>
            <p className="muted">
              Contract value: SGD {contract.contract_value_sgd.toFixed(2)} -- blended excess rate: SGD{' '}
              {(contract.contract_value_sgd / contract.contracted_hours).toFixed(2)}/hr (SRV-008)
            </p>
          </>
        )}

        {contract.status === 'draft' && <button onClick={onActivate}>Activate contract</button>}
        <p style={{ marginTop: 10 }}>
          <Link to={`/job-orders?contract=${contract.id}`}>View job orders for this contract</Link>
        </p>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <h2>Sales staff &amp; Product coverage</h2>
          {!editingCoverage && (
            <button type="button" className="secondary" onClick={() => setEditingCoverage(true)}>
              Edit
            </button>
          )}
        </div>
        {editingCoverage ? (
          <form onSubmit={onSaveCoverage}>
            <div className="form-row">
              <label>Sales staff</label>
              <select value={salesStaffId} onChange={(e) => setSalesStaffId(e.target.value)}>
                <option value="">Unassigned</option>
                {staff.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <label>Product coverage (ctrl/cmd-click for more than one)</label>
              <select
                multiple
                size={Math.min(6, Math.max(3, products.length))}
                value={productIds}
                onChange={(e) => setProductIds(Array.from(e.target.selectedOptions, (o) => o.value))}
              >
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button type="button" className="secondary" onClick={() => setEditingCoverage(false)}>
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <>
            <p>
              <strong>Sales staff:</strong> {staffName(contract.sales_staff_id) ?? <span className="muted">Unassigned</span>}
            </p>
            <p>
              <strong>Products covered:</strong>{' '}
              {contract.products.length > 0 ? (
                contract.products.map((p) => p.product_name).join(', ')
              ) : (
                <span className="muted">None specified</span>
              )}
            </p>
          </>
        )}
      </div>

      {(contract.status === 'exceeded' || contract.status === 'expired') && (
        <div className="card">
          <h2>Renew (SRV-010 / SRV-016)</h2>
          <p className="muted">
            Creates a new contract record of the same kind -- product coverage and sales staff carry
            forward automatically. Backdated seamlessly if renewed within 2 weeks of expiry.
          </p>
          <form onSubmit={onRenew}>
            {isHourMetered && (
              <div className="form-row">
                <label>New contracted hours</label>
                <input
                  type="number"
                  min={10}
                  step={0.5}
                  value={renewHours}
                  onChange={(e) => setRenewHours(e.target.value)}
                />
              </div>
            )}
            {isAdHoc ? (
              <div className="form-row">
                <label>New reference hourly rate (SGD/hr)</label>
                <input
                  type="number"
                  min={0}
                  step={0.5}
                  value={renewRate}
                  onChange={(e) => setRenewRate(e.target.value)}
                />
              </div>
            ) : (
              <div className="form-row">
                <label>New contract value (SGD)</label>
                <input
                  type="number"
                  min={0}
                  value={renewValue}
                  onChange={(e) => setRenewValue(e.target.value)}
                />
              </div>
            )}
            <button type="submit">Renew</button>
          </form>
        </div>
      )}

      <div className="card">
        <h2>Excess usage (SRV-003 / SRV-004 / SRV-013)</h2>
        <table>
          <thead>
            <tr>
              <th>Excess hours</th>
              <th>Treatment</th>
              <th>Reason</th>
              <th>Invoiced</th>
            </tr>
          </thead>
          <tbody>
            {excessUsage.map((r) => (
              <tr key={r.id}>
                <td>{r.excess_hours.toFixed(2)}</td>
                <td>{r.treatment ?? <span className="muted">awaiting review</span>}</td>
                <td>{r.reason ?? '-'}</td>
                <td>{r.invoiced ? 'Yes' : 'No'}</td>
              </tr>
            ))}
            {excessUsage.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  None yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Invoices (BILL-001 / BILL-002 / BILL-005)</h2>
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Description</th>
              <th>Amount (SGD)</th>
              <th>Issued</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id}>
                <td>{inv.invoice_type}</td>
                <td>{inv.description}</td>
                <td>{inv.amount_sgd.toFixed(2)}</td>
                <td>{new Date(inv.issued_at).toLocaleDateString()}</td>
              </tr>
            ))}
            {invoices.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  None yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

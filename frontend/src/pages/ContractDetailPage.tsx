import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type Contract, type ExcessUsageRecord, type Invoice } from '../lib/api'

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [contract, setContract] = useState<Contract | null>(null)
  const [excessUsage, setExcessUsage] = useState<ExcessUsageRecord[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [error, setError] = useState<string | null>(null)
  const [renewHours, setRenewHours] = useState('10')
  const [renewValue, setRenewValue] = useState('2400')

  function refresh() {
    if (!id) return
    api.getContract(id).then(setContract)
    api.listContractExcessUsage(id).then(setExcessUsage)
    api.listInvoices({ contract_id: id }).then(setInvoices)
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
    if (!id) return
    setError(null)
    try {
      await api.renewContract(id, {
        contracted_hours: parseFloat(renewHours),
        contract_value_sgd: parseFloat(renewValue),
      })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to renew')
    }
  }

  if (!contract) return <p>Loading...</p>

  const pctUsed = Math.min(100, (contract.consumed_hours / contract.contracted_hours) * 100)

  return (
    <div>
      <h1>Contract {contract.id.slice(0, 8)}</h1>
      <p>
        <span className={`badge ${contract.status}`}>{contract.status}</span>{' '}
        <span className="muted">
          {contract.start_date} &rarr; {contract.end_date}
        </span>
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
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

        {contract.status === 'draft' && <button onClick={onActivate}>Activate contract</button>}
        <p style={{ marginTop: 10 }}>
          <Link to={`/job-orders?contract=${contract.id}`}>View job orders for this contract</Link>
        </p>
      </div>

      {(contract.status === 'exceeded' || contract.status === 'expired') && (
        <div className="card">
          <h2>Renew (SRV-010 / SRV-016)</h2>
          <p className="muted">
            Creates a new contract record with a fresh hour allocation. Backdated seamlessly if renewed
            within 2 weeks of expiry.
          </p>
          <form onSubmit={onRenew}>
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
            <div className="form-row">
              <label>New contract value (SGD)</label>
              <input
                type="number"
                min={0}
                value={renewValue}
                onChange={(e) => setRenewValue(e.target.value)}
              />
            </div>
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

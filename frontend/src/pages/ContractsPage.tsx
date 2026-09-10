import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, type Contract, type Customer } from '../lib/api'

export default function ContractsPage() {
  const [contracts, setContracts] = useState<Contract[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [searchParams] = useSearchParams()
  const preselectedCustomer = searchParams.get('customer') ?? ''

  const [customerId, setCustomerId] = useState(preselectedCustomer)
  const [hours, setHours] = useState('10')
  const [value, setValue] = useState('2400')
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10))
  const [error, setError] = useState<string | null>(null)

  const [filterStatus, setFilterStatus] = useState(searchParams.get('status') ?? '')
  const [filterCustomer, setFilterCustomer] = useState(preselectedCustomer)

  function refresh() {
    api.listContracts({ status: filterStatus || undefined, customer_id: filterCustomer || undefined }).then(setContracts)
    api.listCustomers().then(setCustomers)
  }

  useEffect(refresh, [filterStatus, filterCustomer])

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name ?? id.slice(0, 8)

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await api.createContract({
        customer_id: customerId,
        contracted_hours: parseFloat(hours),
        contract_value_sgd: parseFloat(value),
        start_date: startDate,
      })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create contract')
    }
  }

  function resetFilters() {
    setFilterStatus('')
    setFilterCustomer('')
  }

  return (
    <div>
      <h1>Service Contracts</h1>
      <p className="muted">
        SRV-001: 12-month standard term. SRV-002/SRV-012: 10-hour hard minimum, no override.
      </p>

      <div className="card" style={{ marginTop: 20 }}>
        <h2>New contract</h2>
        <form onSubmit={onCreate}>
          <div className="form-row">
            <label>Customer</label>
            <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
              <option value="">Select a customer...</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Contracted hours (min 10)</label>
            <input type="number" min={0} step={0.5} value={hours} onChange={(e) => setHours(e.target.value)} />
          </div>
          <div className="form-row">
            <label>Contract value (SGD, billed annually upfront)</label>
            <input type="number" min={0} step={1} value={value} onChange={(e) => setValue(e.target.value)} />
          </div>
          <div className="form-row">
            <label>Start date</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          {error && <div className="error-banner">{error}</div>}
          <button type="submit" disabled={!customerId}>
            Create contract (Draft)
          </button>
        </form>
      </div>

      <div className="card">
        <div className="filter-bar">
          <div className="form-row" style={{ margin: 0 }}>
            <label>Status</label>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">All</option>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="exceeded">Exceeded</option>
              <option value="expired">Expired</option>
              <option value="renewed">Renewed</option>
            </select>
          </div>
          <div className="form-row" style={{ margin: 0 }}>
            <label>Customer</label>
            <select value={filterCustomer} onChange={(e) => setFilterCustomer(e.target.value)}>
              <option value="">All</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <button type="button" className="secondary" onClick={resetFilters}>
            Reset filters
          </button>
        </div>

        <h2>Contracts ({contracts.length})</h2>
        <table>
          <thead>
            <tr>
              <th>Customer</th>
              <th>Status</th>
              <th>Hours (used / total)</th>
              <th>Term</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {contracts.map((c) => (
              <tr key={c.id}>
                <td>{customerName(c.customer_id)}</td>
                <td>
                  <span className={`badge ${c.status}`}>{c.status}</span>
                </td>
                <td>
                  {c.consumed_hours.toFixed(2)} / {c.contracted_hours.toFixed(2)} hrs
                </td>
                <td>
                  {c.start_date} &rarr; {c.end_date}
                </td>
                <td>
                  <Link to={`/contracts/${c.id}`}>Open</Link>
                </td>
              </tr>
            ))}
            {contracts.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No contracts match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

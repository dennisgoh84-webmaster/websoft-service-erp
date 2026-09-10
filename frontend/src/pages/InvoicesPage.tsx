import { useEffect, useState } from 'react'
import { api, type Customer, type Invoice } from '../lib/api'

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [filterCustomer, setFilterCustomer] = useState('')
  const [filterType, setFilterType] = useState('')

  function refresh() {
    api.listInvoices({ customer_id: filterCustomer || undefined }).then(setInvoices)
    api.listCustomers().then(setCustomers)
  }

  useEffect(refresh, [filterCustomer])

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name ?? id.slice(0, 8)
  const visible = filterType ? invoices.filter((i) => i.invoice_type === filterType) : invoices
  const total = visible.reduce((sum, i) => sum + i.amount_sgd, 0)

  return (
    <div>
      <h1>Invoices</h1>
      <p className="muted">
        BILL-002: no approval required, issued directly. BILL-005: revenue recognized on invoice.
      </p>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="filter-bar">
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
          <div className="form-row" style={{ margin: 0 }}>
            <label>Type</label>
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="">All</option>
              <option value="contract_annual">Contract (annual)</option>
              <option value="excess_usage">Excess usage</option>
            </select>
          </div>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setFilterCustomer('')
              setFilterType('')
            }}
          >
            Reset filters
          </button>
        </div>

        <h2>
          Invoices ({visible.length}) -- total SGD {total.toFixed(2)}
        </h2>
        <table>
          <thead>
            <tr>
              <th>Customer</th>
              <th>Type</th>
              <th>Description</th>
              <th>Amount (SGD)</th>
              <th>Issued</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((inv) => (
              <tr key={inv.id}>
                <td>{customerName(inv.customer_id)}</td>
                <td>{inv.invoice_type}</td>
                <td>{inv.description}</td>
                <td>{inv.amount_sgd.toFixed(2)}</td>
                <td>{new Date(inv.issued_at).toLocaleString()}</td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No invoices match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

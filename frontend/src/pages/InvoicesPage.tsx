import { useEffect, useState } from 'react'
import { api, type Customer, type Invoice, type InvoiceStatus } from '../lib/api'

const STATUS_BADGE: Record<InvoiceStatus, string> = {
  outstanding: 'draft',
  partially_paid: 'exceeded',
  paid: 'active',
  written_off: 'expired',
}

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
  const net = visible.reduce((sum, i) => sum + i.amount_sgd, 0)
  const gst = visible.reduce((sum, i) => sum + i.gst_amount_sgd, 0)
  const total = visible.reduce((sum, i) => sum + i.total_amount_sgd, 0)
  const outstanding = visible.reduce((sum, i) => sum + i.outstanding_sgd, 0)

  return (
    <div>
      <h1>Invoices</h1>
      <p className="muted">
        Tax invoices. BILL-002: no approval required, issued directly. BILL-005: revenue
        recognized on invoice. GST is charged at the company's standard rate; the net column is the
        revenue figure, since GST collected is owed to IRAS rather than earned.
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

        <h2>Invoices ({visible.length})</h2>
        <p className="muted">
          Net SGD {net.toFixed(2)} + GST SGD {gst.toFixed(2)} = SGD {total.toFixed(2)} billed
          &middot; <strong>SGD {outstanding.toFixed(2)} outstanding</strong>
        </p>
        <div style={{ overflowX: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th>Invoice no.</th>
              <th>Customer</th>
              <th>Description</th>
              <th>Net</th>
              <th>GST</th>
              <th>Total</th>
              <th>Outstanding</th>
              <th>Due</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((inv) => (
              <tr key={inv.id}>
                <td style={{ whiteSpace: 'nowrap' }}>
                  {inv.invoice_number}
                  <div className="muted">{new Date(inv.issued_at).toLocaleDateString()}</div>
                </td>
                <td>{customerName(inv.customer_id)}</td>
                <td>
                  {inv.description}
                  <div className="muted">{inv.invoice_type}</div>
                </td>
                <td>{inv.amount_sgd.toFixed(2)}</td>
                <td>
                  {inv.gst_amount_sgd.toFixed(2)}
                  <div className="muted">
                    {inv.tax_code} {inv.gst_rate}%
                  </div>
                </td>
                <td>
                  <strong>{inv.total_amount_sgd.toFixed(2)}</strong>
                </td>
                <td>{inv.outstanding_sgd.toFixed(2)}</td>
                <td style={{ whiteSpace: 'nowrap' }}>
                  {inv.due_date ?? <span className="muted">no terms set</span>}
                </td>
                <td>
                  <span className={`badge ${STATUS_BADGE[inv.status] ?? 'draft'}`}>
                    {inv.status.replace('_', ' ')}
                  </span>
                  {inv.is_disputed && (
                    <div>
                      <span className="badge exceeded">disputed</span>
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={9} className="muted">
                  No invoices match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  )
}

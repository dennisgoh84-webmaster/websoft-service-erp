import { useEffect, useState } from 'react'
import { api, type Invoice } from '../lib/api'

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([])

  useEffect(() => {
    api.listInvoices().then(setInvoices)
  }, [])

  const total = invoices.reduce((sum, i) => sum + i.amount_sgd, 0)

  return (
    <div>
      <h1>Invoices</h1>
      <p className="muted">
        BILL-002: no approval required, issued directly. BILL-005: revenue recognized on invoice.
      </p>

      <div className="card" style={{ marginTop: 20 }}>
        <h2>All invoices ({invoices.length}) -- total SGD {total.toFixed(2)}</h2>
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
                <td>{new Date(inv.issued_at).toLocaleString()}</td>
              </tr>
            ))}
            {invoices.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  No invoices yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

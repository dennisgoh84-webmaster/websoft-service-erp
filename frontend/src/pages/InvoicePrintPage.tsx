// A printable Tax Invoice "form" -- plain HTML/CSS, rendered with live
// data and printed with the browser's own Print dialog (Save as PDF).
// No report designer, no separate tool: to change the layout, edit the
// JSX/CSS below exactly like any other page in this app.
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, downloadBlob, type Customer, type Invoice } from '../lib/api'
import { useAuth } from '../lib/AuthContext'

const money = (n: number) => n.toFixed(2)

export default function InvoicePrintPage() {
  const { id } = useParams<{ id: string }>()
  const { activeCompany } = useAuth()
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [exportFormat, setExportFormat] = useState<'pdf' | 'word'>('pdf')

  useEffect(() => {
    if (!id) return
    api.getInvoice(id).then((inv) => {
      setInvoice(inv)
      api.getCustomer(inv.customer_id).then(setCustomer)
    })
  }, [id])

  async function onExport() {
    if (!id || !invoice) return
    if (exportFormat === 'pdf') {
      window.print()
      return
    }
    const blob = await api.exportInvoiceDocx(id)
    downloadBlob(blob, `${invoice.invoice_number}.docx`)
  }

  if (!invoice || !customer) return <p>Loading...</p>

  const billTo = [customer.address_line1, customer.address_line2, customer.address_city, customer.address_country]
    .filter(Boolean)
    .join(', ')

  return (
    <div className="invoice-sheet">
      <div className="no-print" style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value as 'pdf' | 'word')}>
          <option value="pdf">PDF (Print)</option>
          <option value="word">Word</option>
        </select>
        <button onClick={onExport}>Export</button>
      </div>

      <div className="invoice-header">
        <div>
          {activeCompany?.logo && <img src={activeCompany.logo} alt="" className="invoice-logo" />}
          <div className="invoice-company-name">{activeCompany?.name}</div>
          <div className="muted">{activeCompany?.address}</div>
          {activeCompany?.gst_registration_no && (
            <div className="muted">GST Reg. No: {activeCompany.gst_registration_no}</div>
          )}
        </div>
        <div className="invoice-title">
          <h1>TAX INVOICE</h1>
          <div>{invoice.invoice_number}</div>
          <div className="muted">Issued {new Date(invoice.issued_at).toLocaleDateString()}</div>
          {invoice.due_date && <div className="muted">Due {invoice.due_date}</div>}
        </div>
      </div>

      <div className="invoice-bill-to">
        <div className="muted">Bill To</div>
        <strong>{customer.name}</strong>
        {customer.uen && <div className="muted">UEN: {customer.uen}</div>}
        {billTo && <div>{billTo}</div>}
      </div>

      <table className="invoice-lines">
        <thead>
          <tr>
            <th>Description</th>
            <th style={{ textAlign: 'right' }}>Net (SGD)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{invoice.description}</td>
            <td style={{ textAlign: 'right' }}>{money(invoice.amount_sgd)}</td>
          </tr>
        </tbody>
      </table>

      <div className="invoice-totals">
        <div>
          <span>Net amount</span>
          <span>{money(invoice.amount_sgd)}</span>
        </div>
        <div>
          <span>
            GST ({invoice.tax_code} {invoice.gst_rate}%)
          </span>
          <span>{money(invoice.gst_amount_sgd)}</span>
        </div>
        <div className="invoice-total-line">
          <span>Total</span>
          <span>SGD {money(invoice.total_amount_sgd)}</span>
        </div>
      </div>

      <p className="muted" style={{ marginTop: 40, fontSize: 12 }}>
        Thank you for your business.
      </p>
    </div>
  )
}

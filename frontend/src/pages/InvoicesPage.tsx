import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, downloadBlob, type AgingReport, type Customer, type CustomerStatement, type Invoice, type InvoiceStatus } from '../lib/api'

const STATUS_BADGE: Record<InvoiceStatus, string> = {
  outstanding: 'draft',
  partially_paid: 'exceeded',
  paid: 'active',
  written_off: 'expired',
}

const money = (n: number) => n.toFixed(2)

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [aging, setAging] = useState<AgingReport | null>(null)
  const [statement, setStatement] = useState<CustomerStatement | null>(null)
  const [filterCustomer, setFilterCustomer] = useState('')
  const [filterType, setFilterType] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  function refresh() {
    api.listInvoices({ customer_id: filterCustomer || undefined }).then(setInvoices)
    api.listCustomers().then(setCustomers)
    api.arAging().then(setAging).catch((e) => setError(e.message))
  }

  useEffect(refresh, [filterCustomer])

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name ?? id.slice(0, 8)
  const visible = filterType ? invoices.filter((i) => i.invoice_type === filterType) : invoices
  const net = visible.reduce((sum, i) => sum + i.amount_sgd, 0)
  const gst = visible.reduce((sum, i) => sum + i.gst_amount_sgd, 0)
  const total = visible.reduce((sum, i) => sum + i.total_amount_sgd, 0)
  const outstanding = visible.reduce((sum, i) => sum + i.outstanding_sgd, 0)

  function openStatement(customerIdToShow: string) {
    api.customerStatement(customerIdToShow).then(setStatement).catch((e) => setError(e.message))
  }

  async function onExportCsv() {
    setError(null)
    try {
      const blob = await api.exportInvoicesCsv({ customer_id: filterCustomer || undefined })
      downloadBlob(blob, 'invoices.csv')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export CSV')
    }
  }

  async function onExportExcel() {
    setError(null)
    try {
      const blob = await api.exportInvoicesExcel({ customer_id: filterCustomer || undefined })
      downloadBlob(blob, 'invoices.xlsx')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export Excel')
    }
  }

  async function onWriteOff(invoice: Invoice) {
    const reason = window.prompt(
      `Write off SGD ${money(invoice.outstanding_sgd)} on ${invoice.invoice_number}?\n\n` +
        'A reason is required and is recorded in the Event Logs (AR-002).',
    )
    if (reason === null) return
    setError(null)
    setMessage(null)
    try {
      await api.writeOffInvoice(invoice.id, reason)
      setMessage(`${invoice.invoice_number} written off.`)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to write off invoice')
    }
  }

  async function onToggleDispute(invoice: Invoice) {
    setError(null)
    setMessage(null)
    try {
      if (invoice.is_disputed) {
        await api.flagInvoiceDispute(invoice.id, false)
      } else {
        const note = window.prompt('What is disputed? (AR-003: collections continue regardless)')
        if (note === null) return
        await api.flagInvoiceDispute(invoice.id, true, note)
      }
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update dispute flag')
    }
  }

  return (
    <div>
      <h1>Invoices</h1>
      <p className="muted">
        Tax invoices. BILL-002: no approval required, issued directly. BILL-005: revenue
        recognized on invoice. GST is charged at the company's standard rate; the net column is the
        revenue figure, since GST collected is owed to IRAS rather than earned. AR-002: write-offs
        need a reason, and the owner's approval above the threshold set in Company Setup. AR-003: a
        disputed invoice is flagged but keeps aging normally -- nothing is put on hold.
      </p>
      {error && <div className="error-banner">{error}</div>}
      {message && (
        <p className="muted" style={{ marginBottom: 12 }}>
          {message}
        </p>
      )}

      {aging && (
        <div className="card">
          <h2>Aging as at {aging.as_at}</h2>
          <div className="stat-grid">
            <div className="card stat-tile">
              <div className="stat-value">{money(aging.current)}</div>
              <div className="stat-label">Current / not yet due</div>
            </div>
            <div className="card stat-tile">
              <div className="stat-value">{money(aging.days_1_30)}</div>
              <div className="stat-label">1-30 days overdue</div>
            </div>
            <div className="card stat-tile">
              <div className="stat-value">{money(aging.days_31_60)}</div>
              <div className="stat-label">31-60 days</div>
            </div>
            <div className="card stat-tile">
              <div className="stat-value">{money(aging.days_61_90)}</div>
              <div className="stat-label">61-90 days</div>
            </div>
            <div className="card stat-tile">
              <div className="stat-value">{money(aging.over_90)}</div>
              <div className="stat-label">Over 90 days</div>
            </div>
            <div className="card stat-tile">
              <div className="stat-value">{money(aging.total)}</div>
              <div className="stat-label">Total outstanding (SGD)</div>
            </div>
          </div>

          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th>Current</th>
                <th>1-30</th>
                <th>31-60</th>
                <th>61-90</th>
                <th>90+</th>
                <th>Total</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {aging.rows.map((r) => (
                <tr key={r.customer_id}>
                  <td>{r.customer_name}</td>
                  <td>{money(r.current)}</td>
                  <td>{money(r.days_1_30)}</td>
                  <td>{money(r.days_31_60)}</td>
                  <td>{money(r.days_61_90)}</td>
                  <td>{money(r.over_90)}</td>
                  <td>
                    <strong>{money(r.total)}</strong>
                  </td>
                  <td>
                    <button className="secondary" onClick={() => openStatement(r.customer_id)}>
                      Statement
                    </button>
                  </td>
                </tr>
              ))}
              {aging.rows.length === 0 && (
                <tr>
                  <td colSpan={8} className="muted">
                    Nothing outstanding.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {statement && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>Statement -- {statement.customer_name}</h2>
            <button className="secondary" onClick={() => setStatement(null)}>
              Close
            </button>
          </div>
          <p className="muted">
            As at {statement.as_at} &middot;{' '}
            {statement.payment_terms_days === null
              ? 'no payment terms agreed'
              : `Net ${statement.payment_terms_days} days`}{' '}
            &middot; outstanding <strong>SGD {money(statement.total_outstanding_sgd)}</strong>
            {statement.unallocated_credit_sgd > 0 && (
              <> &middot; SGD {money(statement.unallocated_credit_sgd)} unallocated on account</>
            )}
          </p>
          <table>
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Issued</th>
                <th>Due</th>
                <th>Total</th>
                <th>Paid</th>
                <th>Outstanding</th>
                <th>Overdue</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {statement.lines.map((l) => (
                <tr key={l.invoice_id}>
                  <td>{l.invoice_number}</td>
                  <td>{l.issued_on}</td>
                  <td>{l.due_date ?? <span className="muted">-</span>}</td>
                  <td>{money(l.total_amount_sgd)}</td>
                  <td>{money(l.amount_paid_sgd)}</td>
                  <td>
                    <strong>{money(l.outstanding_sgd)}</strong>
                  </td>
                  <td>{l.days_overdue > 0 ? `${l.days_overdue} days` : '-'}</td>
                  <td>
                    {l.status.replace('_', ' ')}
                    {l.is_disputed && (
                      <span className="badge exceeded" style={{ marginLeft: 6 }}>
                        disputed
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {statement.lines.length === 0 && (
                <tr>
                  <td colSpan={8} className="muted">
                    Nothing outstanding for this customer.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <div className="card">
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
          <button type="button" className="secondary" onClick={onExportCsv}>
            Export CSV
          </button>
          <button type="button" className="secondary" onClick={onExportExcel}>
            Export Excel
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
              <th></th>
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
                <td style={{ display: 'flex', gap: 6 }}>
                  <Link to={`/invoices/${inv.id}/print`} className="secondary" style={{ padding: '6px 10px' }}>
                    Print
                  </Link>
                  <button className="secondary" onClick={() => onToggleDispute(inv)}>
                    {inv.is_disputed ? 'Clear dispute' : 'Flag dispute'}
                  </button>
                  {inv.outstanding_sgd > 0 && (
                    <button className="secondary" onClick={() => onWriteOff(inv)}>
                      Write off
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={10} className="muted">
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

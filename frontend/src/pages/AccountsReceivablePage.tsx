import { useEffect, useState, type FormEvent } from 'react'
import {
  api,
  type AgingReport,
  type Customer,
  type CustomerStatement,
  type Invoice,
  type Payment,
} from '../lib/api'

const METHODS = [
  { value: 'bank_transfer', label: 'Bank transfer' },
  { value: 'paynow', label: 'PayNow' },
  { value: 'cheque', label: 'Cheque' },
  { value: 'cash', label: 'Cash' },
  { value: 'credit_card', label: 'Credit card' },
  { value: 'other', label: 'Other' },
]

const money = (n: number) => n.toFixed(2)

export default function AccountsReceivablePage() {
  const [aging, setAging] = useState<AgingReport | null>(null)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [payments, setPayments] = useState<Payment[]>([])
  const [statement, setStatement] = useState<CustomerStatement | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  // Record payment form
  const [customerId, setCustomerId] = useState('')
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10))
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState('bank_transfer')
  const [reference, setReference] = useState('')
  const [saving, setSaving] = useState(false)

  // Allocation: which invoice a given unallocated payment settles
  const [allocFor, setAllocFor] = useState<Record<string, { invoiceId: string; amount: string }>>({})

  function refresh() {
    api.arAging().then(setAging).catch((e) => setError(e.message))
    api.listPayments().then(setPayments).catch((e) => setError(e.message))
    api.listInvoices().then(setInvoices).catch((e) => setError(e.message))
    api.listCustomers().then(setCustomers).catch((e) => setError(e.message))
  }

  useEffect(refresh, [])

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name ?? id.slice(0, 8)
  const openInvoices = invoices.filter((i) => i.outstanding_sgd > 0)

  async function onRecordPayment(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setMessage(null)
    setSaving(true)
    try {
      await api.recordPayment({
        customer_id: customerId,
        payment_date: paymentDate,
        amount_sgd: parseFloat(amount),
        method,
        reference: reference || undefined,
      })
      setAmount('')
      setReference('')
      setMessage('Payment recorded. Allocate it below to settle specific invoices (AR-001).')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record payment')
    } finally {
      setSaving(false)
    }
  }

  async function onAllocate(payment: Payment) {
    const choice = allocFor[payment.id]
    if (!choice?.invoiceId || !choice.amount) {
      setError('Pick an invoice and an amount to allocate.')
      return
    }
    setError(null)
    setMessage(null)
    try {
      await api.allocatePayment(payment.id, [
        { invoice_id: choice.invoiceId, amount_sgd: parseFloat(choice.amount) },
      ])
      setAllocFor((prev) => ({ ...prev, [payment.id]: { invoiceId: '', amount: '' } }))
      setMessage('Allocated.')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to allocate payment')
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

  function openStatement(customerIdToShow: string) {
    api
      .customerStatement(customerIdToShow)
      .then(setStatement)
      .catch((e) => setError(e.message))
  }

  return (
    <div>
      <h1>Accounts Receivable</h1>
      <p className="muted">
        Money owed by customers. AR-001: payments are allocated manually by Finance from the
        remittance advice -- there is no automatic matching. AR-002: write-offs need a reason, and
        the owner's approval above the threshold set in Company Setup. AR-003: a disputed invoice is
        flagged but keeps aging normally -- nothing is put on hold.
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
        <h2>Record a customer payment</h2>
        <form onSubmit={onRecordPayment}>
          <div className="form-row">
            <label>Customer</label>
            <select value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
              <option value="">Select...</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Payment date</label>
            <input
              type="date"
              value={paymentDate}
              onChange={(e) => setPaymentDate(e.target.value)}
              required
            />
          </div>
          <div className="form-row">
            <label>Amount received (SGD)</label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </div>
          <div className="form-row">
            <label>Method</label>
            <select value={method} onChange={(e) => setMethod(e.target.value)}>
              {METHODS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Bank / remittance reference</label>
            <input value={reference} onChange={(e) => setReference(e.target.value)} />
          </div>
          <button type="submit" disabled={saving || !customerId}>
            {saving ? 'Recording...' : 'Record payment'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Payments ({payments.length})</h2>
        <p className="muted">
          Unallocated money sits on the customer's account until Finance says what it settles.
        </p>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Customer</th>
              <th>Amount</th>
              <th>Unallocated</th>
              <th>Reference</th>
              <th>Allocate to invoice</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p) => {
              const choice = allocFor[p.id] ?? { invoiceId: '', amount: '' }
              const customerInvoices = openInvoices.filter((i) => i.customer_id === p.customer_id)
              return (
                <tr key={p.id}>
                  <td style={{ whiteSpace: 'nowrap' }}>{p.payment_date}</td>
                  <td>{customerName(p.customer_id)}</td>
                  <td>{money(p.amount_sgd)}</td>
                  <td>
                    {p.unallocated_sgd > 0 ? (
                      <strong>{money(p.unallocated_sgd)}</strong>
                    ) : (
                      <span className="muted">fully allocated</span>
                    )}
                    {p.allocations.length > 0 && (
                      <div className="muted">
                        {p.allocations.map((a) => `${a.invoice_number}: ${money(a.amount_sgd)}`).join(', ')}
                      </div>
                    )}
                  </td>
                  <td className="muted">{p.reference ?? '-'}</td>
                  <td>
                    {p.unallocated_sgd > 0 ? (
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        <select
                          value={choice.invoiceId}
                          onChange={(e) =>
                            setAllocFor((prev) => ({
                              ...prev,
                              [p.id]: { ...choice, invoiceId: e.target.value },
                            }))
                          }
                        >
                          <option value="">Invoice...</option>
                          {customerInvoices.map((i) => (
                            <option key={i.id} value={i.id}>
                              {i.invoice_number} ({money(i.outstanding_sgd)} due)
                            </option>
                          ))}
                        </select>
                        <input
                          type="number"
                          min="0.01"
                          step="0.01"
                          placeholder="Amount"
                          style={{ width: 100 }}
                          value={choice.amount}
                          onChange={(e) =>
                            setAllocFor((prev) => ({
                              ...prev,
                              [p.id]: { ...choice, amount: e.target.value },
                            }))
                          }
                        />
                        <button onClick={() => onAllocate(p)}>Allocate</button>
                      </div>
                    ) : (
                      <span className="muted">-</span>
                    )}
                  </td>
                </tr>
              )
            })}
            {payments.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No payments recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Open invoices ({openInvoices.length})</h2>
        <table>
          <thead>
            <tr>
              <th>Invoice</th>
              <th>Customer</th>
              <th>Total</th>
              <th>Outstanding</th>
              <th>Due</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {openInvoices.map((i) => (
              <tr key={i.id}>
                <td>{i.invoice_number}</td>
                <td>{customerName(i.customer_id)}</td>
                <td>{money(i.total_amount_sgd)}</td>
                <td>
                  <strong>{money(i.outstanding_sgd)}</strong>
                </td>
                <td style={{ whiteSpace: 'nowrap' }}>
                  {i.due_date ?? <span className="muted">no terms</span>}
                </td>
                <td>
                  {i.status.replace('_', ' ')}
                  {i.is_disputed && (
                    <span className="badge exceeded" style={{ marginLeft: 6 }}>
                      disputed
                    </span>
                  )}
                </td>
                <td style={{ display: 'flex', gap: 6 }}>
                  <button className="secondary" onClick={() => onToggleDispute(i)}>
                    {i.is_disputed ? 'Clear dispute' : 'Flag dispute'}
                  </button>
                  <button className="secondary" onClick={() => onWriteOff(i)}>
                    Write off
                  </button>
                </td>
              </tr>
            ))}
            {openInvoices.length === 0 && (
              <tr>
                <td colSpan={7} className="muted">
                  Nothing outstanding.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

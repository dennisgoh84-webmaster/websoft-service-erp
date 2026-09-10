import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type Customer, type Product, type Quotation, type QuotationStatus } from '../lib/api'

const money = (n: number) => n.toFixed(2)

const STATUS_BADGE: Record<QuotationStatus, string> = {
  draft: 'draft',
  sent: 'exceeded',
  accepted: 'active',
  rejected: 'expired',
  expired: 'expired',
}

interface DraftLine {
  productId: string
  description: string
  unitOfMeasure: string
  quantity: string
  unitPrice: string
}

function emptyLine(): DraftLine {
  return { productId: '', description: '', unitOfMeasure: '', quantity: '1', unitPrice: '' }
}

export default function QuotationsPage() {
  const [quotations, setQuotations] = useState<Quotation[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [catalog, setCatalog] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const [filterStatus, setFilterStatus] = useState('')
  const [filterCustomer, setFilterCustomer] = useState('')

  // New quotation form
  const [customerId, setCustomerId] = useState('')
  const [quotationDate, setQuotationDate] = useState(new Date().toISOString().slice(0, 10))
  const [validUntil, setValidUntil] = useState('')
  const [notes, setNotes] = useState('')
  const [lines, setLines] = useState<DraftLine[]>([emptyLine()])
  const [saving, setSaving] = useState(false)

  function refresh() {
    api
      .listQuotations({ status: filterStatus || undefined, customer_id: filterCustomer || undefined })
      .then(setQuotations)
      .catch((e) => setError(e.message))
    api.listCustomers().then(setCustomers).catch((e) => setError(e.message))
    api.listCatalog().then(setCatalog).catch((e) => setError(e.message))
  }

  useEffect(refresh, [filterStatus, filterCustomer])

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name ?? id.slice(0, 8)

  function updateLine(index: number, patch: Partial<DraftLine>) {
    setLines((prev) => prev.map((l, i) => (i === index ? { ...l, ...patch } : l)))
  }

  function pickProduct(index: number, productId: string) {
    const product = catalog.find((p) => p.id === productId)
    if (!product) {
      updateLine(index, { productId: '' })
      return
    }
    updateLine(index, {
      productId,
      description: product.name,
      unitOfMeasure: product.unit_of_measure ?? '',
      unitPrice: String(product.sales_price_sgd),
    })
  }

  function addLine() {
    setLines((prev) => [...prev, emptyLine()])
  }

  function removeLine(index: number) {
    setLines((prev) => prev.filter((_, i) => i !== index))
  }

  const draftTotal = lines.reduce(
    (sum, l) => sum + (parseFloat(l.quantity) || 0) * (parseFloat(l.unitPrice) || 0),
    0,
  )

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setMessage(null)
    setSaving(true)
    try {
      const q = await api.createQuotation({
        customer_id: customerId,
        quotation_date: quotationDate,
        valid_until: validUntil || undefined,
        notes: notes || undefined,
        lines: lines
          .filter((l) => l.description && l.quantity && l.unitPrice)
          .map((l) => ({
            product_id: l.productId || undefined,
            description: l.description,
            unit_of_measure: l.unitOfMeasure || undefined,
            quantity: parseFloat(l.quantity),
            unit_price_sgd: parseFloat(l.unitPrice),
          })),
      })
      setMessage(`${q.quotation_number} created (SGD ${money(q.total_amount_sgd)} incl. GST).`)
      setCustomerId('')
      setValidUntil('')
      setNotes('')
      setLines([emptyLine()])
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create quotation')
    } finally {
      setSaving(false)
    }
  }

  async function onSend(q: Quotation) {
    setError(null)
    try {
      await api.sendQuotation(q.id)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send quotation')
    }
  }

  async function onAccept(q: Quotation) {
    setError(null)
    setMessage(null)
    try {
      const result = await api.acceptQuotation(q.id)
      setMessage(result.message)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to accept quotation')
    }
  }

  async function onReject(q: Quotation) {
    setError(null)
    try {
      await api.rejectQuotation(q.id)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject quotation')
    }
  }

  return (
    <div>
      <h1>Sales Quotation</h1>
      <p className="muted">
        A quotation stands alone until accepted -- accepting it attempts to auto-create a draft
        Service Contract from any lines whose unit is "Hours" (the contract's 10-hour minimum,
        SRV-002/012, has no override, so a quotation with no hourly lines is accepted but stays
        unconverted). Lines can be picked from the <Link to="/product-catalog">Product Catalog</Link> or typed free text.
      </p>
      {error && <div className="error-banner">{error}</div>}
      {message && (
        <p className="muted" style={{ marginBottom: 12 }}>
          {message}
        </p>
      )}

      <div className="card">
        <h2>New quotation</h2>
        <form onSubmit={onCreate}>
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
            <label>Date</label>
            <input type="date" value={quotationDate} onChange={(e) => setQuotationDate(e.target.value)} required />
          </div>
          <div className="form-row">
            <label>Valid until</label>
            <input type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} />
          </div>
          <div className="form-row">
            <label>Notes</label>
            <input value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>

          <table>
            <thead>
              <tr>
                <th>Catalog item</th>
                <th>Description</th>
                <th>Unit</th>
                <th>Qty</th>
                <th>Unit price</th>
                <th>Line total</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, i) => (
                <tr key={i}>
                  <td>
                    <select value={line.productId} onChange={(e) => pickProduct(i, e.target.value)}>
                      <option value="">Free text...</option>
                      {catalog.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      value={line.description}
                      onChange={(e) => updateLine(i, { description: e.target.value })}
                      style={{ minWidth: 160 }}
                      required
                    />
                  </td>
                  <td>
                    <input
                      value={line.unitOfMeasure}
                      onChange={(e) => updateLine(i, { unitOfMeasure: e.target.value })}
                      style={{ width: 90 }}
                      placeholder="Hours..."
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={line.quantity}
                      onChange={(e) => updateLine(i, { quantity: e.target.value })}
                      style={{ width: 70 }}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={line.unitPrice}
                      onChange={(e) => updateLine(i, { unitPrice: e.target.value })}
                      style={{ width: 90 }}
                    />
                  </td>
                  <td>{money((parseFloat(line.quantity) || 0) * (parseFloat(line.unitPrice) || 0))}</td>
                  <td>
                    {lines.length > 1 && (
                      <button type="button" className="secondary" onClick={() => removeLine(i)}>
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              <tr>
                <td colSpan={5}>
                  <strong>Net total</strong>
                </td>
                <td colSpan={2}>
                  <strong>{money(draftTotal)}</strong> (+ GST at acceptance-time rate)
                </td>
              </tr>
            </tbody>
          </table>
          <button type="button" className="secondary" style={{ marginTop: 10 }} onClick={addLine}>
            Add line
          </button>
          <div style={{ marginTop: 14 }}>
            <button type="submit" disabled={saving || !customerId}>
              {saving ? 'Creating...' : 'Create quotation (Draft)'}
            </button>
          </div>
        </form>
      </div>

      <div className="card">
        <div className="filter-bar">
          <div className="form-row" style={{ margin: 0 }}>
            <label>Status</label>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">All</option>
              <option value="draft">Draft</option>
              <option value="sent">Sent</option>
              <option value="accepted">Accepted</option>
              <option value="rejected">Rejected</option>
              <option value="expired">Expired</option>
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
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setFilterStatus('')
              setFilterCustomer('')
            }}
          >
            Reset filters
          </button>
        </div>

        <h2>Quotations ({quotations.length})</h2>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Quotation</th>
                <th>Customer</th>
                <th>Date</th>
                <th>Valid until</th>
                <th>Total (incl. GST)</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {quotations.map((q) => (
                <tr key={q.id}>
                  <td>
                    {q.quotation_number}
                    <div className="muted">
                      {q.lines.map((l) => `${l.description} (${l.quantity}${l.unit_of_measure ? ' ' + l.unit_of_measure : ''})`).join(', ')}
                    </div>
                  </td>
                  <td>{customerName(q.customer_id)}</td>
                  <td>{q.quotation_date}</td>
                  <td>{q.valid_until ?? <span className="muted">-</span>}</td>
                  <td>{money(q.total_amount_sgd)}</td>
                  <td>
                    <span className={`badge ${STATUS_BADGE[q.status]}`}>{q.status}</span>
                    {q.converted_contract_id && (
                      <div className="muted">
                        <Link to="/contracts">converted to contract</Link>
                      </div>
                    )}
                  </td>
                  <td style={{ display: 'flex', gap: 6 }}>
                    {q.status === 'draft' && (
                      <button className="secondary" onClick={() => onSend(q)}>
                        Send
                      </button>
                    )}
                    {(q.status === 'draft' || q.status === 'sent') && (
                      <>
                        <button onClick={() => onAccept(q)}>Accept</button>
                        <button className="secondary" onClick={() => onReject(q)}>
                          Reject
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
              {quotations.length === 0 && (
                <tr>
                  <td colSpan={7} className="muted">
                    No quotations match these filters.
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

import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type Customer, type CustomerType } from '../lib/api'

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [name, setName] = useState('')
  const [customerType, setCustomerType] = useState<CustomerType>('company')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [terms, setTerms] = useState('')
  const [error, setError] = useState<string | null>(null)

  function refresh() {
    api.listCustomers().then(setCustomers).catch((e) => setError(e.message))
  }

  useEffect(refresh, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await api.createCustomer({
        name,
        customer_type: customerType,
        billing_email: email || undefined,
        phone: phone || undefined,
        payment_terms_days: terms === '' ? null : parseInt(terms, 10),
      })
      setName('')
      setCustomerType('company')
      setEmail('')
      setPhone('')
      setTerms('')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create customer')
    }
  }

  return (
    <div>
      <h1>Customers</h1>
      <p className="muted">Customer Management -- the account each contract, job order, and invoice belongs to.</p>

      <div className="card" style={{ marginTop: 20 }}>
        <h2>Add customer</h2>
        <p className="muted">
          This is a quick add -- everything else (address, UEN, GST no., contact people, terms &amp;
          conditions) is filled in from the customer's own page after it's created.
        </p>
        <form onSubmit={onCreate}>
          <div className="form-row">
            <label>Type</label>
            <select value={customerType} onChange={(e) => setCustomerType(e.target.value as CustomerType)}>
              <option value="company">Company</option>
              <option value="individual">Individual</option>
            </select>
          </div>
          <div className="form-row">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="form-row">
            <label>Email (optional)</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
          </div>
          <div className="form-row">
            <label>Phone (optional)</label>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <div className="form-row">
            <label>Payment terms (days from invoice date)</label>
            <input
              type="number"
              min={0}
              value={terms}
              onChange={(e) => setTerms(e.target.value)}
              placeholder="e.g. 30 -- leave blank if not yet agreed"
            />
          </div>
          {error && <div className="error-banner">{error}</div>}
          <button type="submit">Add customer</button>
        </form>
      </div>

      <div className="card">
        <h2>All customers</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Address</th>
              <th>Payment terms</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id}>
                <td>
                  <Link to={`/customers/${c.id}`}>{c.name}</Link>
                </td>
                <td className="muted">{c.customer_type === 'individual' ? 'Individual' : 'Company'}</td>
                <td>{c.billing_email ?? '-'}</td>
                <td>{c.phone ?? '-'}</td>
                <td className="muted">
                  {[c.address_line1, c.address_city, c.address_country].filter(Boolean).join(', ') || '-'}
                </td>
                <td>
                  {c.payment_terms_days === null ? (
                    <span className="muted">not agreed</span>
                  ) : (
                    `Net ${c.payment_terms_days} days`
                  )}
                </td>
                <td>
                  <span className={`badge ${c.is_active ? 'active' : 'draft'}`}>
                    {c.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td style={{ display: 'flex', gap: 10 }}>
                  <Link to={`/customers/${c.id}`}>Open</Link>
                  <Link to={`/contracts?customer=${c.id}`}>Contracts</Link>
                </td>
              </tr>
            ))}
            {customers.length === 0 && (
              <tr>
                <td colSpan={8} className="muted">
                  No customers yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

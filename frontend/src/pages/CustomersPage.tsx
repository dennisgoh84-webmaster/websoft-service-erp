import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type Customer } from '../lib/api'

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [address, setAddress] = useState('')
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
        billing_email: email || undefined,
        billing_address: address || undefined,
        payment_terms_days: terms === '' ? null : parseInt(terms, 10),
      })
      setName('')
      setEmail('')
      setAddress('')
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
        <form onSubmit={onCreate}>
          <div className="form-row">
            <label>Company name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="form-row">
            <label>Billing email (optional)</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
          </div>
          <div className="form-row">
            <label>Billing address (shown on tax invoices)</label>
            <input value={address} onChange={(e) => setAddress(e.target.value)} />
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
              <th>Billing email</th>
              <th>Payment terms</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.billing_email ?? '-'}</td>
                <td>
                  {c.payment_terms_days === null ? (
                    <span className="muted">not agreed</span>
                  ) : (
                    `Net ${c.payment_terms_days} days`
                  )}
                </td>
                <td>
                  <Link to={`/contracts?customer=${c.id}`}>View contracts</Link>
                </td>
              </tr>
            ))}
            {customers.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
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

import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type Customer } from '../lib/api'

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)

  function refresh() {
    api.listCustomers().then(setCustomers).catch((e) => setError(e.message))
  }

  useEffect(refresh, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await api.createCustomer(name, email || undefined)
      setName('')
      setEmail('')
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
              <th></th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.billing_email ?? '-'}</td>
                <td>
                  <Link to={`/contracts?customer=${c.id}`}>View contracts</Link>
                </td>
              </tr>
            ))}
            {customers.length === 0 && (
              <tr>
                <td colSpan={3} className="muted">
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

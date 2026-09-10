import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type Contract, type Customer, type Ticket, type TicketPriority } from '../lib/api'

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [contracts, setContracts] = useState<Contract[]>([])

  const [customerId, setCustomerId] = useState('')
  const [contractId, setContractId] = useState('')
  const [subject, setSubject] = useState('')
  const [priority, setPriority] = useState<TicketPriority>('normal')
  const [error, setError] = useState<string | null>(null)

  function refresh() {
    api.listTickets().then(setTickets)
    api.listCustomers().then(setCustomers)
    api.listContracts().then(setContracts)
  }

  useEffect(refresh, [])

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name ?? id.slice(0, 8)
  const contractsForCustomer = contracts.filter((c) => c.customer_id === customerId)

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await api.createTicket({ customer_id: customerId, contract_id: contractId, subject, priority })
      setSubject('')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create ticket')
    }
  }

  return (
    <div>
      <h1>Helpdesk Tickets</h1>
      <p className="muted">Customer &rarr; Support Ticket &rarr; Assignment &rarr; Service Work</p>

      <div className="card" style={{ marginTop: 20 }}>
        <h2>New ticket</h2>
        <form onSubmit={onCreate}>
          <div className="form-row">
            <label>Customer</label>
            <select
              value={customerId}
              onChange={(e) => {
                setCustomerId(e.target.value)
                setContractId('')
              }}
              required
            >
              <option value="">Select...</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Contract</label>
            <select value={contractId} onChange={(e) => setContractId(e.target.value)} required>
              <option value="">Select...</option>
              {contractsForCustomer.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.status} -- {c.remaining_hours.toFixed(1)}h remaining
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Subject</label>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} required />
          </div>
          <div className="form-row">
            <label>Priority</label>
            <select value={priority} onChange={(e) => setPriority(e.target.value as TicketPriority)}>
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          {error && <div className="error-banner">{error}</div>}
          <button type="submit" disabled={!customerId || !contractId}>
            Create ticket
          </button>
        </form>
      </div>

      <div className="card">
        <h2>All tickets</h2>
        <table>
          <thead>
            <tr>
              <th>Subject</th>
              <th>Customer</th>
              <th>Priority</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((t) => (
              <tr key={t.id}>
                <td>{t.subject}</td>
                <td>{customerName(t.customer_id)}</td>
                <td>{t.priority}</td>
                <td>{t.status}</td>
                <td>
                  <Link to={`/tickets/${t.id}`}>Open</Link>
                </td>
              </tr>
            ))}
            {tickets.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No tickets yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

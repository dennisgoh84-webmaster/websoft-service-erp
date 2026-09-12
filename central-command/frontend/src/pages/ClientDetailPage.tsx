import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, type Client, type ConnectionTestResult } from '../lib/api'

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [client, setClient] = useState<Client | null>(null)
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null)
  const [testing, setTesting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (id) api.getClient(id).then(setClient)
  }, [id])

  async function onTest() {
    if (!id) return
    setTesting(true)
    setTestResult(null)
    setError('')
    try {
      const res = await api.testConnection(id)
      setTestResult(res)
      api.getClient(id).then(setClient) // refresh after test
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Test failed')
    } finally {
      setTesting(false)
    }
  }

  async function onDelete() {
    if (!id || !window.confirm('Delete this client? This cannot be undone.')) return
    await api.deleteClient(id)
    window.location.href = '/clients'
  }

  async function onSuspend() {
    if (!id) return
    await api.updateClient(id, { status: 'suspended' } as Partial<Client>)
    api.getClient(id).then(setClient)
  }

  async function onActivate() {
    if (!id) return
    await api.updateClient(id, { status: 'active' } as Partial<Client>)
    api.getClient(id).then(setClient)
  }

  if (!client) return <p>Loading...</p>

  const statusColor = client.status === 'active' ? '#27ae60' : client.status === 'suspended' ? '#e74c3c' : '#95a5a6'

  return (
    <div>
      <Link to="/clients" style={{ color: '#800020', fontSize: 13 }}>← Back to Clients</Link>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: 12 }}>
        <div>
          <h1 style={{ margin: '0 0 4px', fontSize: 22 }}>{client.name}</h1>
          <p style={{ margin: 0, color: '#888', fontSize: 13 }}>
            Code: <strong>{client.code}</strong>
            <span style={{ marginLeft: 12, display: 'inline-block', padding: '1px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600, color: '#fff', background: statusColor }}>
              {client.status}
            </span>
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {client.status === 'active' && (
            <button onClick={onSuspend} style={{ background: '#e74c3c', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>
              Suspend
            </button>
          )}
          {client.status === 'suspended' && (
            <button onClick={onActivate} style={{ background: '#27ae60', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>
              Activate
            </button>
          )}
          <button onClick={onDelete} style={{ background: '#ccc', color: '#333', border: 'none', padding: '6px 14px', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>
            Delete
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginTop: 24 }}>
        {/* Connection Details */}
        <div style={{ background: '#fff', borderRadius: 8, padding: 20, border: '1px solid #e0e0e0' }}>
          <h2 style={{ fontSize: 15, margin: '0 0 12px', color: '#800020' }}>Connection Details</h2>
          <table style={{ fontSize: 13 }}>
            <tbody>
              <tr><td style={{ color: '#888', paddingRight: 16, paddingBottom: 6 }}>Host</td><td style={{ paddingBottom: 6 }}>{client.db_host}</td></tr>
              <tr><td style={{ color: '#888', paddingRight: 16, paddingBottom: 6 }}>Port</td><td style={{ paddingBottom: 6 }}>{client.db_port}</td></tr>
              <tr><td style={{ color: '#888', paddingRight: 16, paddingBottom: 6 }}>Database</td><td style={{ paddingBottom: 6 }}>{client.db_name}</td></tr>
              <tr><td style={{ color: '#888', paddingRight: 16, paddingBottom: 6 }}>Username</td><td style={{ paddingBottom: 6 }}>{client.db_username}</td></tr>
              <tr><td style={{ color: '#888', paddingRight: 16, paddingBottom: 6 }}>TLS</td><td style={{ paddingBottom: 6 }}>{client.db_use_tls ? 'Yes' : 'No'}</td></tr>
            </tbody>
          </table>

          <button
            onClick={onTest}
            disabled={testing}
            style={{ marginTop: 12, background: '#3498db', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}
          >
            {testing ? 'Testing...' : 'Test Connection'}
          </button>

          {error && <p style={{ color: '#e74c3c', fontSize: 12, marginTop: 8 }}>{error}</p>}

          {testResult && (
            <div style={{ marginTop: 12, padding: 12, borderRadius: 6, background: testResult.success ? '#eafaf1' : '#fdecea', border: `1px solid ${testResult.success ? '#27ae60' : '#e74c3c'}`, fontSize: 12 }}>
              <strong>{testResult.success ? '✅ Connected' : '❌ Failed'}</strong>
              <p style={{ margin: '4px 0 0' }}>{testResult.message}</p>
              {testResult.alembic_head && <p style={{ margin: '2px 0 0' }}>Alembic head: <code>{testResult.alembic_head}</code></p>}
              {testResult.companies && (
                <div style={{ marginTop: 6 }}>
                  <strong>Companies ({testResult.companies.length}):</strong>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 16 }}>
                    {testResult.companies.map((c) => (
                      <li key={c.id}>{c.name} {c.registration_number && `(${c.registration_number})`}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Info */}
        <div style={{ background: '#fff', borderRadius: 8, padding: 20, border: '1px solid #e0e0e0' }}>
          <h2 style={{ fontSize: 15, margin: '0 0 12px', color: '#800020' }}>Information</h2>
          <table style={{ fontSize: 13 }}>
            <tbody>
              <tr><td style={{ color: '#888', paddingRight: 16, paddingBottom: 6 }}>Last Connected</td><td style={{ paddingBottom: 6 }}>{client.last_connected_at ? new Date(client.last_connected_at).toLocaleString() : '—'}</td></tr>
              <tr><td style={{ color: '#888', paddingRight: 16, paddingBottom: 6 }}>Alembic Head</td><td style={{ paddingBottom: 6, fontFamily: 'monospace', fontSize: 11 }}>{client.last_known_alembic_head ?? '—'}</td></tr>
              <tr><td style={{ color: '#888', paddingRight: 16, paddingBottom: 6 }}>Created</td><td style={{ paddingBottom: 6 }}>{new Date(client.created_at).toLocaleString()}</td></tr>
              <tr><td style={{ color: '#888', paddingRight: 16, paddingBottom: 6 }}>Updated</td><td style={{ paddingBottom: 6 }}>{new Date(client.updated_at).toLocaleString()}</td></tr>
            </tbody>
          </table>
          {client.notes && (
            <div style={{ marginTop: 12, padding: 10, background: '#f9f9f9', borderRadius: 4, fontSize: 12, color: '#555' }}>
              <strong>Notes:</strong> {client.notes}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

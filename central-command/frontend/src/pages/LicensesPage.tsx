import { useEffect, useState } from 'react'
import { api, type ClientSummary, type ClientModule } from '../lib/api'

export default function LicensesPage() {
  const [clients, setClients] = useState<ClientSummary[]>([])
  const [selectedClient, setSelectedClient] = useState<string>('')
  const [modules, setModules] = useState<ClientModule[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [toggling, setToggling] = useState<string | null>(null)

  useEffect(() => { api.listClients().then(setClients) }, [])

  async function loadModules(clientId: string) {
    setSelectedClient(clientId)
    setModules([])
    setError('')
    if (!clientId) return
    setLoading(true)
    try {
      const mods = await api.getClientModules(clientId)
      setModules(mods)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  async function toggleModule(m: ClientModule) {
    if (!selectedClient) return
    setToggling(m.module_key + m.company_id)
    setError('')
    try {
      await api.setModuleLicense(selectedClient, m.company_id, {
        module_key: m.module_key,
        enabled: !m.enabled,
      })
      // Refresh
      const mods = await api.getClientModules(selectedClient)
      setModules(mods)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setToggling(null)
    }
  }

  // Group by company
  const byCompany: Record<string, { name: string; modules: ClientModule[] }> = {}
  for (const m of modules) {
    if (!byCompany[m.company_id]) {
      byCompany[m.company_id] = { name: m.company_name, modules: [] }
    }
    byCompany[m.company_id].modules.push(m)
  }

  return (
    <div>
      <h1 style={{ margin: '0 0 16px', fontSize: 22 }}>License Management</h1>

      <div style={{ marginBottom: 20 }}>
        <label style={{ fontSize: 13, fontWeight: 600, marginRight: 8 }}>Select Client:</label>
        <select
          value={selectedClient}
          onChange={(e) => loadModules(e.target.value)}
          style={{ padding: '6px 12px', border: '1px solid #ccc', borderRadius: 4, fontSize: 13, minWidth: 200 }}
        >
          <option value="">— Choose —</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>{c.name} ({c.code})</option>
          ))}
        </select>
      </div>

      {error && <div style={{ background: '#fdecea', color: '#c0392b', padding: '6px 12px', borderRadius: 4, fontSize: 13, marginBottom: 12 }}>{error}</div>}

      {loading && <p style={{ color: '#888' }}>Loading modules from client database...</p>}

      {Object.entries(byCompany).map(([companyId, { name, modules: mods }]) => (
        <div key={companyId} style={{ background: '#fff', borderRadius: 8, border: '1px solid #e0e0e0', marginBottom: 20, overflow: 'hidden' }}>
          <div style={{ background: '#f9f9f9', padding: '10px 16px', borderBottom: '1px solid #e0e0e0' }}>
            <h2 style={{ margin: 0, fontSize: 14, color: '#333' }}>🏢 {name}</h2>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #eee' }}>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#888', fontWeight: 600, fontSize: 12 }}>Module</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#888', fontWeight: 600, fontSize: 12 }}>Key</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#888', fontWeight: 600, fontSize: 12 }}>Built</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#888', fontWeight: 600, fontSize: 12 }}>License</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#888', fontWeight: 600, fontSize: 12 }}>Status</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#888', fontWeight: 600, fontSize: 12 }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {mods.map((m) => (
                <tr key={m.module_key} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '8px 12px', fontWeight: 500 }}>{m.module_name}</td>
                  <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 11 }}>{m.module_key}</td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{ color: m.is_built ? '#27ae60' : '#888' }}>{m.is_built ? '✓' : '—'}</span>
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{ display: 'inline-block', padding: '1px 6px', borderRadius: 3, fontSize: 11, background: '#f0f0f0' }}>
                      {m.license_type}
                    </span>
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 10px',
                      borderRadius: 12,
                      fontSize: 11,
                      fontWeight: 600,
                      color: '#fff',
                      background: m.enabled ? '#27ae60' : '#e74c3c',
                    }}>
                      {m.enabled ? 'ENABLED' : 'DISABLED'}
                    </span>
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <button
                      onClick={() => toggleModule(m)}
                      disabled={toggling === m.module_key + m.company_id}
                      style={{
                        background: m.enabled ? '#e74c3c' : '#27ae60',
                        color: '#fff',
                        border: 'none',
                        padding: '3px 10px',
                        borderRadius: 3,
                        cursor: 'pointer',
                        fontSize: 11,
                      }}
                    >
                      {toggling === m.module_key + m.company_id
                        ? '...'
                        : m.enabled ? 'Disable' : 'Enable'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {selectedClient && !loading && modules.length === 0 && (
        <p style={{ color: '#888', fontSize: 13 }}>No modules found in client database.</p>
      )}
    </div>
  )
}

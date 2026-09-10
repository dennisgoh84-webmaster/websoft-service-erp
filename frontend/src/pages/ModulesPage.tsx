import { useEffect, useState } from 'react'
import { api, type ModuleInfo } from '../lib/api'
import { useAuth } from '../lib/AuthContext'

export default function ModulesPage() {
  const { user } = useAuth()
  const [modules, setModules] = useState<ModuleInfo[]>([])
  const [error, setError] = useState<string | null>(null)

  function refresh() {
    api.listModules().then(setModules).catch((e) => setError(e.message))
  }

  useEffect(refresh, [])

  async function onToggle(key: string, enabled: boolean) {
    setError(null)
    try {
      await api.toggleModule(key, enabled)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update module')
    }
  }

  const isOwner = user?.role === 'owner'

  return (
    <div>
      <h1>Module Control</h1>
      <p className="muted">
        Which business-area modules are enabled/licensed for this company. Set up together with
        multi-company support (CLAUDE.md) so each company can have a different module mix in future.
        {!isOwner && ' Only the owner (Dennis) can change these.'}
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Module</th>
              <th>Built?</th>
              <th>License</th>
              <th>Enabled</th>
            </tr>
          </thead>
          <tbody>
            {modules.map((m) => (
              <tr key={m.key}>
                <td>{m.name}</td>
                <td>{m.is_built ? 'Yes' : <span className="muted">Not yet built</span>}</td>
                <td>{m.license_type}</td>
                <td>
                  <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <input
                      type="checkbox"
                      checked={m.enabled}
                      disabled={!isOwner}
                      onChange={(e) => onToggle(m.key, e.target.checked)}
                    />
                    {m.enabled ? 'On' : 'Off'}
                  </label>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

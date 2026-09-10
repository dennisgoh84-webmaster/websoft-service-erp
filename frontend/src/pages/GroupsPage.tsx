import { useEffect, useState, type FormEvent } from 'react'
import { api, type AccessLevel, type Group, type ModuleInfo } from '../lib/api'

const ACCESS_LEVELS: AccessLevel[] = ['none', 'view', 'edit', 'full']

export default function GroupsPage() {
  const [groups, setGroups] = useState<Group[]>([])
  const [modules, setModules] = useState<ModuleInfo[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  function refresh(keepSelection = true) {
    api
      .listGroups()
      .then((gs) => {
        setGroups(gs)
        if (!keepSelection && gs.length > 0) setSelectedId(gs[0].id)
      })
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    refresh(false)
    api.listModules().then(setModules).catch((e) => setError(e.message))
  }, [])

  const selected = groups.find((g) => g.id === selectedId) ?? null

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const g = await api.createGroup(name, description || undefined)
      setName('')
      setDescription('')
      refresh()
      setSelectedId(g.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create group')
    }
  }

  async function onDelete(id: string) {
    setError(null)
    try {
      await api.deleteGroup(id)
      if (selectedId === id) setSelectedId(null)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete group')
    }
  }

  async function onLevelChange(moduleKey: string, level: AccessLevel) {
    if (!selected) return
    setSaving(true)
    setError(null)
    try {
      const nextAuthorities = modules.map((m) => {
        const current = selected.authorities.find((a) => a.module_key === m.key)
        return {
          module_key: m.key,
          access_level: m.key === moduleKey ? level : current?.access_level ?? 'none',
        }
      })
      const updated = await api.setGroupAuthorities(selected.id, nextAuthorities)
      setGroups((gs) => gs.map((g) => (g.id === updated.id ? updated : g)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update access level')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h1>Group Authority</h1>
      <p className="muted">
        Every staff member belongs to exactly one Group. A Group's access level on a module --
        None / View / Edit / Full -- controls what that staff member can see and do there. This is
        separate from the named-responsibility rules already confirmed for specific decisions
        (e.g. who decides excess usage on a contract).
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
        <div style={{ width: 320, flexShrink: 0 }}>
          <div className="card">
            <h2>Groups</h2>
            <table>
              <tbody>
                {groups.map((g) => (
                  <tr
                    key={g.id}
                    onClick={() => setSelectedId(g.id)}
                    style={{ cursor: 'pointer', background: g.id === selectedId ? 'var(--bg)' : undefined }}
                  >
                    <td>
                      <strong>{g.name}</strong>
                      <div className="muted">{g.member_count} staff</div>
                    </td>
                  </tr>
                ))}
                {groups.length === 0 && (
                  <tr>
                    <td className="muted">No groups yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h2>New group</h2>
            <form onSubmit={onCreate}>
              <div className="form-row">
                <label>Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="form-row">
                <label>Description (optional)</label>
                <input value={description} onChange={(e) => setDescription(e.target.value)} />
              </div>
              <button type="submit">Add group</button>
            </form>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          {selected ? (
            <div className="card">
              <h2>{selected.name}</h2>
              {selected.description && <p className="muted">{selected.description}</p>}
              <p className="muted">
                {selected.member_count} staff member{selected.member_count === 1 ? '' : 's'} in this
                group.
              </p>
              <table>
                <thead>
                  <tr>
                    <th>Module</th>
                    <th>Access level</th>
                  </tr>
                </thead>
                <tbody>
                  {modules.map((m) => {
                    const current =
                      selected.authorities.find((a) => a.module_key === m.key)?.access_level ??
                      'none'
                    return (
                      <tr key={m.key}>
                        <td>
                          {m.name}
                          {!m.is_built && <span className="muted"> (not yet built)</span>}
                        </td>
                        <td>
                          <select
                            value={current}
                            disabled={saving}
                            onChange={(e) => onLevelChange(m.key, e.target.value as AccessLevel)}
                          >
                            {ACCESS_LEVELS.map((lvl) => (
                              <option key={lvl} value={lvl}>
                                {lvl.charAt(0).toUpperCase() + lvl.slice(1)}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <button
                className="secondary"
                style={{ marginTop: 16 }}
                disabled={selected.member_count > 0}
                title={
                  selected.member_count > 0
                    ? 'Reassign staff out of this group before deleting it.'
                    : undefined
                }
                onClick={() => onDelete(selected.id)}
              >
                Delete group
              </button>
            </div>
          ) : (
            <div className="card muted">Select a group to edit its module access levels.</div>
          )}
        </div>
      </div>
    </div>
  )
}

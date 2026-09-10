import { useEffect, useState } from 'react'
import { api, type ExcessTreatment, type ExcessUsageRecord } from '../lib/api'

const TREATMENTS: { value: ExcessTreatment; label: string }[] = [
  { value: 'billable', label: 'Billable excess support (SRV-008: contract blended rate)' },
  { value: 'approved_non_billable', label: 'Approved non-billable' },
  { value: 'warranty_goodwill', label: 'Warranty / Goodwill' },
  { value: 'internal_write_off', label: 'Internal write-off' },
  { value: 'other', label: 'Other authorized treatment' },
]

export default function ExcessReviewPage() {
  const [pending, setPending] = useState<ExcessUsageRecord[]>([])
  const [decided, setDecided] = useState<ExcessUsageRecord[]>([])
  const [error, setError] = useState<string | null>(null)
  const [choices, setChoices] = useState<Record<string, { treatment: ExcessTreatment; reason: string }>>({})

  function refresh() {
    api.listExcessUsage(true).then(setPending)
    api.listExcessUsage(false).then((all) => setDecided(all.filter((r) => r.treatment)))
  }

  useEffect(refresh, [])

  function updateChoice(id: string, patch: Partial<{ treatment: ExcessTreatment; reason: string }>) {
    setChoices((prev) => ({
      ...prev,
      [id]: { treatment: prev[id]?.treatment ?? 'billable', reason: prev[id]?.reason ?? '', ...patch },
    }))
  }

  async function onDecide(id: string) {
    setError(null)
    const choice = choices[id]
    if (!choice?.reason?.trim()) {
      setError('A reason is required for every excess usage decision (SRV-004).')
      return
    }
    try {
      await api.decideExcessUsage(id, choice.treatment, choice.reason)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record decision')
    }
  }

  return (
    <div>
      <h1>Excess Usage Review</h1>
      <p className="muted">
        SRV-004: reviewed by Nico (Service &amp; Support), or Cherish as backup (SRV-011). Every decision
        and reason is recorded for audit.
      </p>

      <div className="card" style={{ marginTop: 20 }}>
        <h2>Awaiting review ({pending.length})</h2>
        {pending.map((r) => {
          const choice = choices[r.id] ?? { treatment: 'billable' as ExcessTreatment, reason: '' }
          return (
            <div key={r.id} className="card" style={{ background: 'var(--bg)' }}>
              <p>
                <strong>{r.excess_hours.toFixed(2)} hrs</strong> excess on contract {r.contract_id.slice(0, 8)}
              </p>
              <div className="form-row">
                <label>Treatment</label>
                <select
                  value={choice.treatment}
                  onChange={(e) => updateChoice(r.id, { treatment: e.target.value as ExcessTreatment })}
                >
                  {TREATMENTS.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-row">
                <label>Reason (required, auditable)</label>
                <textarea
                  rows={2}
                  value={choice.reason}
                  onChange={(e) => updateChoice(r.id, { reason: e.target.value })}
                />
              </div>
              <button onClick={() => onDecide(r.id)}>Record decision</button>
            </div>
          )
        })}
        {pending.length === 0 && <p className="muted">Nothing pending review.</p>}
        {error && <div className="error-banner">{error}</div>}
      </div>

      <div className="card">
        <h2>Decided</h2>
        <table>
          <thead>
            <tr>
              <th>Excess hours</th>
              <th>Treatment</th>
              <th>Reason</th>
              <th>Invoiced</th>
            </tr>
          </thead>
          <tbody>
            {decided.map((r) => (
              <tr key={r.id}>
                <td>{r.excess_hours.toFixed(2)}</td>
                <td>{r.treatment}</td>
                <td>{r.reason}</td>
                <td>{r.invoiced ? 'Yes' : 'No'}</td>
              </tr>
            ))}
            {decided.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  None yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

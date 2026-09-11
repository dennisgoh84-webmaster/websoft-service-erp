// Document Control -- view the document numbering counters behind
// every serially-numbered document (invoices, receipts, payment
// vouchers, JVs, POs, bills, quotations, contracts, job orders,
// service records) and, carefully, adjust one. The list itself is
// generic (driven by whatever doc_kind rows exist), so a future
// document type shows up here automatically once it's numbered.
// Editing last_number is the one genuinely dangerous action here: set
// it too low and the next document raised collides with one already
// issued -- so it's a deliberate, reasoned action, not a quick edit.
import { useEffect, useState } from 'react'
import { api, type DocumentSequence } from '../lib/api'

export default function DocumentControlPage() {
  const [sequences, setSequences] = useState<DocumentSequence[]>([])
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  function refresh() {
    api.listDocumentSequences().then(setSequences).catch((e) => setError(e.message))
  }

  useEffect(refresh, [])

  async function onAdjust(seq: DocumentSequence) {
    const input = window.prompt(
      `Current last number issued for ${seq.prefix}-${seq.year} is ${seq.last_number} ` +
        `(next document will be ${seq.prefix}-${seq.year}-${String(seq.last_number + 1).padStart(4, '0')}).\n\n` +
        'Enter the new last number. WARNING: setting this lower than a number already issued will ' +
        'cause the next document raised to collide with one that already exists.',
      String(seq.last_number),
    )
    if (input === null) return
    const lastNumber = Number(input)
    if (!Number.isInteger(lastNumber) || lastNumber < 0) {
      setError('Enter a whole number, 0 or higher.')
      return
    }
    const reason = window.prompt('Reason for this change (recorded in Event Logs):')
    if (!reason) return
    setError(null)
    setMessage(null)
    try {
      await api.updateDocumentSequence(seq.id, { last_number: lastNumber, reason })
      setMessage(`${seq.prefix}-${seq.year} updated.`)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update sequence')
    }
  }

  return (
    <div>
      <h1>Document Control</h1>
      <p className="muted">
        The numbering counter behind every serially-numbered document. Each row is the last number
        issued for a document kind in a given year -- the next one raised is one higher. Adjusting a
        counter is restricted and recorded to Event Logs since setting it wrong risks a duplicate
        document number.
      </p>
      {error && <div className="error-banner">{error}</div>}
      {message && (
        <p className="muted" style={{ marginBottom: 12 }}>
          {message}
        </p>
      )}

      <div className="card">
        <h2>Document Sequences ({sequences.length})</h2>
        <table>
          <thead>
            <tr>
              <th>Document kind</th>
              <th>Prefix</th>
              <th>Year</th>
              <th>Last number issued</th>
              <th>Next number</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sequences.map((s) => (
              <tr key={s.id}>
                <td>{s.doc_kind.replace(/_/g, ' ')}</td>
                <td>{s.prefix}</td>
                <td>{s.year}</td>
                <td>{s.last_number}</td>
                <td>
                  {s.prefix}-{s.year}-{String(s.last_number + 1).padStart(4, '0')}
                </td>
                <td>
                  <button className="secondary" onClick={() => onAdjust(s)}>
                    Adjust
                  </button>
                </td>
              </tr>
            ))}
            {sequences.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No documents have been numbered yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

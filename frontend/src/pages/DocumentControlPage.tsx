// Document Control -- view the document numbering counters behind
// every serially-numbered document (invoices, receipts, payment
// vouchers, JVs, POs, bills, quotations, contracts, job orders,
// service records) and, carefully, adjust one. The list itself is
// generic (driven by whatever doc_kind rows exist), so a future
// document type shows up here automatically once it's numbered.
// Editing last_number is the one genuinely dangerous action here: set
// it too low and the next document raised collides with one already
// issued -- so it's a deliberate, reasoned action, not a quick edit.
//
// Confirmed 2026-09-11: each document kind's number FORMAT (front
// prefix / "alphabet", digit padding, whether the year is included)
// is also customizable here, separately from the counter -- see the
// "Number Format" card below. A format change only affects numbers
// issued from that point on; every document already numbered keeps
// the text it was given.
import { useEffect, useState, type FormEvent } from 'react'
import { api, type DocumentNumberFormat, type DocumentSequence } from '../lib/api'

export default function DocumentControlPage() {
  const [sequences, setSequences] = useState<DocumentSequence[]>([])
  const [formats, setFormats] = useState<DocumentNumberFormat[]>([])
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const [editingKind, setEditingKind] = useState<string | null>(null)
  const [prefixInput, setPrefixInput] = useState('')
  const [lengthInput, setLengthInput] = useState('4')
  const [includeYearInput, setIncludeYearInput] = useState(true)
  const [saving, setSaving] = useState(false)

  function refresh() {
    api.listDocumentSequences().then(setSequences).catch((e) => setError(e.message))
    api.listDocumentNumberFormats().then(setFormats).catch((e) => setError(e.message))
  }

  useEffect(refresh, [])

  async function onAdjust(seq: DocumentSequence) {
    const input = window.prompt(
      `Current last number issued for ${seq.prefix}-${seq.year} is ${seq.last_number} ` +
        `(next document will be ${seq.next_number}).\n\n` +
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

  function onStartEditFormat(fmt: DocumentNumberFormat) {
    setEditingKind(fmt.doc_kind)
    setPrefixInput(fmt.prefix)
    setLengthInput(String(fmt.number_length))
    setIncludeYearInput(fmt.include_year)
    setMessage(null)
    setError(null)
  }

  async function onSaveFormat(e: FormEvent) {
    e.preventDefault()
    if (!editingKind) return
    const prefix = prefixInput.trim().toUpperCase()
    if (!/^[A-Z0-9]{1,10}$/.test(prefix)) {
      setError('Prefix must be 1-10 letters/digits, no spaces or symbols (e.g. "CON", "INV2").')
      return
    }
    const numberLength = parseInt(lengthInput, 10)
    if (!Number.isInteger(numberLength) || numberLength < 1 || numberLength > 10) {
      setError('Digits must be a whole number between 1 and 10.')
      return
    }
    const reason = window.prompt(
      `Change ${editingKind.replace(/_/g, ' ')}'s number format to "${prefix}"` +
        `${includeYearInput ? '-<year>' : ''}-${'0'.repeat(numberLength)}? ` +
        'This only affects numbers issued from now on. Reason (recorded in Event Logs):',
    )
    if (!reason) return
    setError(null)
    setMessage(null)
    setSaving(true)
    try {
      await api.updateDocumentNumberFormat(editingKind, {
        prefix,
        number_length: numberLength,
        include_year: includeYearInput,
        reason,
      })
      setMessage(`Number format for ${editingKind.replace(/_/g, ' ')} updated.`)
      setEditingKind(null)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update number format')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h1>Document Control</h1>
      <p className="muted">
        The running-number counter and number format behind every serially-numbered document.
        Adjusting a counter or a format is restricted and recorded to Event Logs.
      </p>
      {error && <div className="error-banner">{error}</div>}
      {message && (
        <p className="muted" style={{ marginBottom: 12 }}>
          {message}
        </p>
      )}

      <div className="card">
        <h2>Number Format by Document Kind</h2>
        <p className="muted">
          Customize the front prefix ("alphabet") and digit padding used when a new number is
          issued -- e.g. change Contract from "CON-2026-0001" to "SC-2026-00001". Only affects
          documents numbered from now on; nothing already issued is renamed.
        </p>
        <table>
          <thead>
            <tr>
              <th>Document kind</th>
              <th>Prefix</th>
              <th>Digits</th>
              <th>Includes year</th>
              <th>Example</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {formats.map((f) => (
              <tr key={f.doc_kind}>
                <td>
                  {f.doc_kind.replace(/_/g, ' ')}
                  {!f.is_custom && (
                    <span className="muted" style={{ marginLeft: 6 }}>
                      (default)
                    </span>
                  )}
                </td>
                <td>{f.prefix}</td>
                <td>{f.number_length}</td>
                <td>{f.include_year ? 'Yes' : 'No'}</td>
                <td className="muted">{f.example}</td>
                <td>
                  <button className="secondary" onClick={() => onStartEditFormat(f)}>
                    Customize
                  </button>
                </td>
              </tr>
            ))}
            {formats.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  Loading...
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {editingKind && (
          <form onSubmit={onSaveFormat} style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
            <h3 style={{ margin: '0 0 10px' }}>Customize: {editingKind.replace(/_/g, ' ')}</h3>
            <div className="form-row">
              <label>Prefix (front alphabet, letters/digits only)</label>
              <input
                value={prefixInput}
                onChange={(e) => setPrefixInput(e.target.value.toUpperCase())}
                maxLength={10}
                required
              />
            </div>
            <div className="form-row">
              <label>Digits (zero-padded length, e.g. 4 -&gt; 0001)</label>
              <input
                type="number"
                min={1}
                max={10}
                value={lengthInput}
                onChange={(e) => setLengthInput(e.target.value)}
                required
              />
            </div>
            <div className="form-row">
              <label>
                <input
                  type="checkbox"
                  checked={includeYearInput}
                  onChange={(e) => setIncludeYearInput(e.target.checked)}
                  style={{ width: 'auto', marginRight: 8 }}
                />
                Include the year (e.g. CON-2026-0001 vs CON-0001)
              </label>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" disabled={saving}>
                {saving ? 'Saving...' : 'Save format'}
              </button>
              <button type="button" className="secondary" onClick={() => setEditingKind(null)}>
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

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
                <td>{s.next_number}</td>
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

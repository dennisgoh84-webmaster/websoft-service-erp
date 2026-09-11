// Accounting Periods and Year-End Closing.
//
// Two pragmatic defaults (confirmed 2026-09-11, logged in
// docs/open-business-decisions.md): a period with no row defined at
// all is unrestricted (periods are opt-in protection, not a
// retroactive block), and "fiscal year" is whatever date range a
// period's own rows say -- there's no hardcoded calendar-year
// assumption baked into the backend, just a sensible default in this
// form's own inputs.
import { useEffect, useState, type FormEvent } from 'react'
import { api, type Account, type AccountingPeriod, type FiscalYearClosure } from '../lib/api'

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

function lastDayOfMonth(year: number, monthIndex: number) {
  return new Date(year, monthIndex + 1, 0).getDate()
}

export default function AccountingPeriodsPage() {
  const [periods, setPeriods] = useState<AccountingPeriod[]>([])
  const [closures, setClosures] = useState<FiscalYearClosure[]>([])
  const [equityAccounts, setEquityAccounts] = useState<Account[]>([])
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const now = new Date()
  const [fiscalYear, setFiscalYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth())
  const [creating, setCreating] = useState(false)

  const [closeYear, setCloseYear] = useState(now.getFullYear())
  const [retainedEarningsId, setRetainedEarningsId] = useState('')
  const [closingYear, setClosingYear] = useState(false)

  function refresh() {
    api.listAccountingPeriods().then(setPeriods).catch((e) => setError(e.message))
    api.listFiscalYearClosures().then(setClosures).catch(() => setClosures([]))
    api.listAccounts({ account_type: 'equity' }).then(setEquityAccounts).catch(() => setEquityAccounts([]))
  }

  useEffect(refresh, [])

  async function onCreatePeriod(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setCreating(true)
    try {
      const start = new Date(fiscalYear, month, 1).toISOString().slice(0, 10)
      const end = new Date(fiscalYear, month, lastDayOfMonth(fiscalYear, month)).toISOString().slice(0, 10)
      await api.createAccountingPeriod({
        fiscal_year: fiscalYear,
        name: `${MONTH_NAMES[month]} ${fiscalYear}`,
        period_start: start,
        period_end: end,
      })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create period')
    } finally {
      setCreating(false)
    }
  }

  async function onClose(period: AccountingPeriod) {
    setError(null)
    setMessage(null)
    try {
      await api.closeAccountingPeriod(period.id)
      setMessage(`${period.name} closed.`)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to close period')
    }
  }

  async function onReopen(period: AccountingPeriod) {
    setError(null)
    setMessage(null)
    try {
      await api.reopenAccountingPeriod(period.id)
      setMessage(`${period.name} reopened.`)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reopen period (owner only)')
    }
  }

  async function onCloseFiscalYear(e: FormEvent) {
    e.preventDefault()
    if (!retainedEarningsId) {
      setError('Choose which Equity account receives the closing balance.')
      return
    }
    if (
      !window.confirm(
        `Close fiscal year ${closeYear}? This posts one journal entry moving every Revenue/Expense ` +
          'account\'s balance for the year into the chosen Equity account. It can only be undone by ' +
          'reversing that journal entry afterwards.',
      )
    ) {
      return
    }
    setError(null)
    setMessage(null)
    setClosingYear(true)
    try {
      await api.closeFiscalYear({ fiscal_year: closeYear, retained_earnings_account_id: retainedEarningsId })
      setMessage(`Fiscal year ${closeYear} closed.`)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to close fiscal year')
    } finally {
      setClosingYear(false)
    }
  }

  const closedFiscalYears = new Set(closures.map((c) => c.fiscal_year))

  return (
    <div>
      <h1>Accounting Periods</h1>
      <p className="muted">
        Closing a period blocks new Journal Vouchers, invoices, bills, receipts and payments dated
        inside it. A date with no period defined at all is unrestricted -- periods are opt-in
        protection, not a retroactive block on existing data.
      </p>
      {error && <div className="error-banner">{error}</div>}
      {message && (
        <p className="muted" style={{ marginBottom: 12 }}>
          {message}
        </p>
      )}

      <div className="card">
        <h2>Periods ({periods.length})</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Fiscal year</th>
              <th>Start</th>
              <th>End</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {periods.map((p) => (
              <tr key={p.id}>
                <td>{p.name}</td>
                <td>{p.fiscal_year}</td>
                <td>{p.period_start}</td>
                <td>{p.period_end}</td>
                <td>
                  <span className={`badge ${p.status === 'open' ? 'active' : 'expired'}`}>{p.status}</span>
                </td>
                <td>
                  {p.status === 'open' ? (
                    <button className="secondary" onClick={() => onClose(p)}>
                      Close
                    </button>
                  ) : (
                    <button className="secondary" onClick={() => onReopen(p)}>
                      Reopen (owner)
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {periods.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No periods defined yet -- postings are unrestricted until one exists.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Add a period</h2>
        <form onSubmit={onCreatePeriod}>
          <div className="form-row">
            <label>Month</label>
            <select value={month} onChange={(e) => setMonth(Number(e.target.value))}>
              {MONTH_NAMES.map((m, i) => (
                <option key={m} value={i}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Fiscal year</label>
            <input
              type="number"
              value={fiscalYear}
              onChange={(e) => setFiscalYear(Number(e.target.value))}
              style={{ width: 120 }}
            />
          </div>
          <button type="submit" disabled={creating}>
            {creating ? 'Adding...' : 'Add period'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Year-End Closing</h2>
        <p className="muted">
          Owner only. Requires every period in the chosen fiscal year to already be closed. Posts one
          balanced journal entry moving each Revenue/Expense account's movement for the year into the
          Equity account you choose; reversible afterwards the same way any posted voucher is
          corrected (General Ledger &rarr; Reverse).
        </p>
        <form onSubmit={onCloseFiscalYear}>
          <div className="form-row">
            <label>Fiscal year</label>
            <input
              type="number"
              value={closeYear}
              onChange={(e) => setCloseYear(Number(e.target.value))}
              style={{ width: 120 }}
            />
          </div>
          <div className="form-row">
            <label>Retained Earnings account (Equity)</label>
            <select value={retainedEarningsId} onChange={(e) => setRetainedEarningsId(e.target.value)} required>
              <option value="">Select an Equity account</option>
              {equityAccounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.code} {a.name}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={closingYear || closedFiscalYears.has(closeYear)}>
            {closedFiscalYears.has(closeYear)
              ? `FY${closeYear} already closed`
              : closingYear
                ? 'Closing...'
                : `Close fiscal year ${closeYear}`}
          </button>
        </form>

        {closures.length > 0 && (
          <>
            <h3 style={{ marginTop: 20 }}>Closed fiscal years</h3>
            <table>
              <thead>
                <tr>
                  <th>Fiscal year</th>
                  <th>Closed at</th>
                </tr>
              </thead>
              <tbody>
                {closures.map((c) => (
                  <tr key={c.id}>
                    <td>{c.fiscal_year}</td>
                    <td>{new Date(c.closed_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  )
}

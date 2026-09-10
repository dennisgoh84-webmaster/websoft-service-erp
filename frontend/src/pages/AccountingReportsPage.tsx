// Accounting Reports -- AR Aging, AP Aging and the GL Trial Balance as
// formal, filterable, exportable reports (module_key
// "accounting_reports"). These are the same figures already shown
// inline on Invoices / Accounts Payable / General Ledger; this screen
// is the one-stop, printable/exportable version with an as-at date
// filter. Every export is written to Event Logs.
import { useEffect, useState } from 'react'
import ExportControl from '../components/ExportControl'
import { api, downloadBlob, type AgingReport, type APAgingReport, type TrialBalance } from '../lib/api'

type ReportType = 'ar-aging' | 'ap-aging' | 'trial-balance'

const money = (n: number) => n.toFixed(2)

export default function AccountingReportsPage() {
  const [reportType, setReportType] = useState<ReportType>('ar-aging')
  const [asAt, setAsAt] = useState('')
  const [error, setError] = useState<string | null>(null)

  const [arAging, setArAging] = useState<AgingReport | null>(null)
  const [apAging, setApAging] = useState<APAgingReport | null>(null)
  const [trialBalance, setTrialBalance] = useState<TrialBalance | null>(null)

  useEffect(() => {
    setError(null)
    const at = asAt || undefined
    if (reportType === 'ar-aging') {
      api.reportArAging(at).then(setArAging).catch((e) => setError(e.message))
    } else if (reportType === 'ap-aging') {
      api.reportApAging(at).then(setApAging).catch((e) => setError(e.message))
    } else {
      api.reportTrialBalance(at).then(setTrialBalance).catch((e) => setError(e.message))
    }
  }, [reportType, asAt])

  async function onExport(format: string) {
    setError(null)
    const at = asAt || undefined
    if (reportType === 'ar-aging') {
      const blob = format === 'csv' ? await api.exportArAgingReportCsv(at) : await api.exportArAgingReportExcel(at)
      downloadBlob(blob, `ar-aging-report.${format === 'csv' ? 'csv' : 'xlsx'}`)
    } else if (reportType === 'ap-aging') {
      const blob = format === 'csv' ? await api.exportApAgingReportCsv(at) : await api.exportApAgingReportExcel(at)
      downloadBlob(blob, `ap-aging-report.${format === 'csv' ? 'csv' : 'xlsx'}`)
    } else {
      const blob = format === 'csv' ? await api.exportTrialBalanceReportCsv(at) : await api.exportTrialBalanceReportExcel(at)
      downloadBlob(blob, `trial-balance-report.${format === 'csv' ? 'csv' : 'xlsx'}`)
    }
  }

  return (
    <div>
      <h1>Accounting Reports</h1>
      <p className="muted">
        AR/AP aging and the GL trial balance, as at a chosen date. Every export is recorded in Event
        Logs.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="filter-bar">
          <div className="form-row" style={{ margin: 0 }}>
            <label>Report</label>
            <select value={reportType} onChange={(e) => setReportType(e.target.value as ReportType)}>
              <option value="ar-aging">AR Aging</option>
              <option value="ap-aging">AP Aging</option>
              <option value="trial-balance">Trial Balance</option>
            </select>
          </div>
          <div className="form-row" style={{ margin: 0 }}>
            <label>As at</label>
            <input type="date" value={asAt} onChange={(e) => setAsAt(e.target.value)} />
          </div>
          <button type="button" className="secondary" onClick={() => setAsAt('')}>
            Reset to today
          </button>
          <ExportControl
            formats={[
              { value: 'csv', label: 'CSV' },
              { value: 'excel', label: 'Excel' },
            ]}
            onExport={onExport}
            onError={setError}
          />
        </div>

        {reportType === 'ar-aging' && arAging && (
          <>
            <h2>AR Aging as at {arAging.as_at}</h2>
            <div className="stat-grid">
              <div className="card stat-tile">
                <div className="stat-value">{money(arAging.current)}</div>
                <div className="stat-label">Current / not yet due</div>
              </div>
              <div className="card stat-tile">
                <div className="stat-value">{money(arAging.days_1_30)}</div>
                <div className="stat-label">1-30 days</div>
              </div>
              <div className="card stat-tile">
                <div className="stat-value">{money(arAging.days_31_60)}</div>
                <div className="stat-label">31-60 days</div>
              </div>
              <div className="card stat-tile">
                <div className="stat-value">{money(arAging.days_61_90)}</div>
                <div className="stat-label">61-90 days</div>
              </div>
              <div className="card stat-tile">
                <div className="stat-value">{money(arAging.over_90)}</div>
                <div className="stat-label">Over 90 days</div>
              </div>
              <div className="card stat-tile">
                <div className="stat-value">{money(arAging.total)}</div>
                <div className="stat-label">Total outstanding (SGD)</div>
              </div>
            </div>
            <div className="report-table-wrap" style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Customer</th>
                    <th>Current</th>
                    <th>1-30</th>
                    <th>31-60</th>
                    <th>61-90</th>
                    <th>90+</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {arAging.rows.map((r) => (
                    <tr key={r.customer_id}>
                      <td>{r.customer_name}</td>
                      <td>{money(r.current)}</td>
                      <td>{money(r.days_1_30)}</td>
                      <td>{money(r.days_31_60)}</td>
                      <td>{money(r.days_61_90)}</td>
                      <td>{money(r.over_90)}</td>
                      <td>
                        <strong>{money(r.total)}</strong>
                      </td>
                    </tr>
                  ))}
                  {arAging.rows.length === 0 && (
                    <tr>
                      <td colSpan={7} className="muted">
                        Nothing outstanding.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {reportType === 'ap-aging' && apAging && (
          <>
            <h2>AP Aging as at {apAging.as_at}</h2>
            <div className="report-table-wrap" style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Supplier</th>
                    <th>Current</th>
                    <th>1-30</th>
                    <th>31-60</th>
                    <th>61-90</th>
                    <th>90+</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {apAging.rows.map((r) => (
                    <tr key={r.supplier_id}>
                      <td>{r.supplier_name}</td>
                      <td>{money(r.current)}</td>
                      <td>{money(r.days_1_30)}</td>
                      <td>{money(r.days_31_60)}</td>
                      <td>{money(r.days_61_90)}</td>
                      <td>{money(r.over_90)}</td>
                      <td>
                        <strong>{money(r.total)}</strong>
                      </td>
                    </tr>
                  ))}
                  {apAging.rows.length === 0 && (
                    <tr>
                      <td colSpan={7} className="muted">
                        Nothing owed.
                      </td>
                    </tr>
                  )}
                </tbody>
                {apAging.rows.length > 0 && (
                  <tfoot>
                    <tr>
                      <td>
                        <strong>Total</strong>
                      </td>
                      <td colSpan={5}></td>
                      <td>
                        <strong>{money(apAging.total)}</strong>
                      </td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </>
        )}

        {reportType === 'trial-balance' && trialBalance && (
          <>
            <h2>
              Trial balance{' '}
              <span className={`badge ${trialBalance.is_balanced ? 'active' : 'exceeded'}`}>
                {trialBalance.is_balanced ? 'balanced' : 'OUT OF BALANCE'}
              </span>
            </h2>
            <div className="report-table-wrap" style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Account</th>
                    <th>Type</th>
                    <th>Debit</th>
                    <th>Credit</th>
                    <th>Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {trialBalance.rows.map((r) => (
                    <tr key={r.account_id}>
                      <td>{r.code}</td>
                      <td>{r.name}</td>
                      <td>{r.account_type}</td>
                      <td>{money(r.debit_sgd)}</td>
                      <td>{money(r.credit_sgd)}</td>
                      <td>{money(r.balance_sgd)}</td>
                    </tr>
                  ))}
                  {trialBalance.rows.length === 0 && (
                    <tr>
                      <td colSpan={6} className="muted">
                        No posted journal entries yet.
                      </td>
                    </tr>
                  )}
                </tbody>
                {trialBalance.rows.length > 0 && (
                  <tfoot>
                    <tr>
                      <td colSpan={3}>
                        <strong>Total</strong>
                      </td>
                      <td>
                        <strong>{money(trialBalance.total_debit)}</strong>
                      </td>
                      <td>
                        <strong>{money(trialBalance.total_credit)}</strong>
                      </td>
                      <td></td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

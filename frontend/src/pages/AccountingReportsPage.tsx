// Accounting Reports -- segmented into AR / AP / Bank / GL / Supporting
// / Analysis, per Dennis's 2026-09-11 ask. Most of these are the same
// figures already shown inline elsewhere (Invoices' aging widget,
// Accounts Payable's aging widget, General Ledger's trial balance,
// Chart of Accounts, Bank Master File, Tax Types); this screen is the
// one-stop, filterable/exportable version. GST Return is the one
// genuinely new calculation -- see app/services/reports.py
// gst_return_data for what it does and does not do (read-only, no
// filing, no GL posting). Every export is written to Event Logs.
import { useEffect, useState } from 'react'
import ExportControl from '../components/ExportControl'
import {
  api,
  downloadBlob,
  type Account,
  type AgingReport,
  type APAgingReport,
  type BankAccount,
  type GSTReturn,
  type TaxCode,
  type TrialBalance,
} from '../lib/api'

type ReportType =
  | 'ar-aging'
  | 'ap-aging'
  | 'bank-accounts'
  | 'trial-balance'
  | 'chart-of-accounts'
  | 'tax-types'
  | 'gst-return'

const REPORT_GROUPS: { label: string; options: { value: ReportType; label: string }[] }[] = [
  { label: 'AR', options: [{ value: 'ar-aging', label: 'AR Aging' }] },
  { label: 'AP', options: [{ value: 'ap-aging', label: 'AP Aging' }] },
  { label: 'Bank', options: [{ value: 'bank-accounts', label: 'Bank Accounts Listing' }] },
  { label: 'GL', options: [{ value: 'trial-balance', label: 'Trial Balance' }] },
  {
    label: 'Supporting',
    options: [
      { value: 'chart-of-accounts', label: 'Chart of Accounts Listing' },
      { value: 'tax-types', label: 'Tax Types Listing' },
    ],
  },
  { label: 'Analysis', options: [{ value: 'gst-return', label: 'GST Return' }] },
]

const money = (n: number) => n.toFixed(2)

function firstOfMonth(): string {
  const d = new Date()
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10)
}
function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export default function AccountingReportsPage() {
  const [reportType, setReportType] = useState<ReportType>('ar-aging')
  const [asAt, setAsAt] = useState('')
  const [periodStart, setPeriodStart] = useState(firstOfMonth())
  const [periodEnd, setPeriodEnd] = useState(today())
  const [error, setError] = useState<string | null>(null)

  const [arAging, setArAging] = useState<AgingReport | null>(null)
  const [apAging, setApAging] = useState<APAgingReport | null>(null)
  const [trialBalance, setTrialBalance] = useState<TrialBalance | null>(null)
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [taxCodes, setTaxCodes] = useState<TaxCode[]>([])
  const [gstReturn, setGstReturn] = useState<GSTReturn | null>(null)

  const usesDateRange = reportType === 'gst-return'

  useEffect(() => {
    setError(null)
    const at = asAt || undefined
    if (reportType === 'ar-aging') {
      api.reportArAging(at).then(setArAging).catch((e) => setError(e.message))
    } else if (reportType === 'ap-aging') {
      api.reportApAging(at).then(setApAging).catch((e) => setError(e.message))
    } else if (reportType === 'trial-balance') {
      api.reportTrialBalance(at).then(setTrialBalance).catch((e) => setError(e.message))
    } else if (reportType === 'bank-accounts') {
      api.listBankAccounts().then(setBankAccounts).catch((e) => setError(e.message))
    } else if (reportType === 'chart-of-accounts') {
      api.listAccounts().then(setAccounts).catch((e) => setError(e.message))
    } else if (reportType === 'tax-types') {
      api.listTaxCodes().then(setTaxCodes).catch((e) => setError(e.message))
    } else if (reportType === 'gst-return') {
      api.reportGstReturn(periodStart, periodEnd).then(setGstReturn).catch((e) => setError(e.message))
    }
  }, [reportType, asAt, periodStart, periodEnd])

  async function onExport(format: string) {
    setError(null)
    const at = asAt || undefined
    const ext = format === 'csv' ? 'csv' : 'xlsx'
    if (reportType === 'ar-aging') {
      downloadBlob(format === 'csv' ? await api.exportArAgingReportCsv(at) : await api.exportArAgingReportExcel(at), `ar-aging-report.${ext}`)
    } else if (reportType === 'ap-aging') {
      downloadBlob(format === 'csv' ? await api.exportApAgingReportCsv(at) : await api.exportApAgingReportExcel(at), `ap-aging-report.${ext}`)
    } else if (reportType === 'trial-balance') {
      downloadBlob(format === 'csv' ? await api.exportTrialBalanceReportCsv(at) : await api.exportTrialBalanceReportExcel(at), `trial-balance-report.${ext}`)
    } else if (reportType === 'bank-accounts') {
      downloadBlob(format === 'csv' ? await api.exportBankAccountsCsv() : await api.exportBankAccountsExcel(), `bank-accounts.${ext}`)
    } else if (reportType === 'chart-of-accounts') {
      downloadBlob(format === 'csv' ? await api.exportAccountsCsv() : await api.exportAccountsExcel(), `chart-of-accounts.${ext}`)
    } else if (reportType === 'tax-types') {
      downloadBlob(format === 'csv' ? await api.exportTaxCodesCsv() : await api.exportTaxCodesExcel(), `tax-types.${ext}`)
    } else if (reportType === 'gst-return') {
      downloadBlob(
        format === 'csv' ? await api.exportGstReturnCsv(periodStart, periodEnd) : await api.exportGstReturnExcel(periodStart, periodEnd),
        `gst-return.${ext}`,
      )
    }
  }

  return (
    <div>
      <h1>Accounting Reports</h1>
      <p className="muted">
        AR, AP, Bank, GL, Supporting and Analysis reports in one place. Every export is recorded in
        Event Logs.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="filter-bar">
          <div className="form-row" style={{ margin: 0 }}>
            <label>Report</label>
            <select value={reportType} onChange={(e) => setReportType(e.target.value as ReportType)}>
              {REPORT_GROUPS.map((group) => (
                <optgroup key={group.label} label={group.label}>
                  {group.options.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
          {usesDateRange ? (
            <>
              <div className="form-row" style={{ margin: 0 }}>
                <label>From</label>
                <input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
              </div>
              <div className="form-row" style={{ margin: 0 }}>
                <label>To</label>
                <input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
              </div>
            </>
          ) : (
            (reportType === 'ar-aging' || reportType === 'ap-aging' || reportType === 'trial-balance') && (
              <>
                <div className="form-row" style={{ margin: 0 }}>
                  <label>As at</label>
                  <input type="date" value={asAt} onChange={(e) => setAsAt(e.target.value)} />
                </div>
                <button type="button" className="secondary" onClick={() => setAsAt('')}>
                  Reset to today
                </button>
              </>
            )
          )}
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

        {reportType === 'bank-accounts' && (
          <>
            <h2>Bank Accounts ({bankAccounts.length})</h2>
            <div className="report-table-wrap" style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Bank</th>
                    <th>Account name</th>
                    <th>Account no.</th>
                    <th>Currency</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {bankAccounts.map((b) => (
                    <tr key={b.id}>
                      <td>{b.bank_name}</td>
                      <td>{b.account_name}</td>
                      <td>{b.account_number}</td>
                      <td>{b.currency_code}</td>
                      <td>
                        <span className={`badge ${b.is_active ? 'active' : 'draft'}`}>{b.is_active ? 'Active' : 'Inactive'}</span>
                      </td>
                    </tr>
                  ))}
                  {bankAccounts.length === 0 && (
                    <tr>
                      <td colSpan={5} className="muted">
                        No bank accounts set up yet -- see Bank Master File.
                      </td>
                    </tr>
                  )}
                </tbody>
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

        {reportType === 'chart-of-accounts' && (
          <>
            <h2>Chart of Accounts ({accounts.length})</h2>
            <div className="report-table-wrap" style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((a) => (
                    <tr key={a.id}>
                      <td>{a.code}</td>
                      <td>{a.name}</td>
                      <td>{a.account_type}</td>
                      <td>
                        <span className={`badge ${a.is_active ? 'active' : 'draft'}`}>{a.is_active ? 'Active' : 'Retired'}</span>
                      </td>
                    </tr>
                  ))}
                  {accounts.length === 0 && (
                    <tr>
                      <td colSpan={4} className="muted">
                        No accounts yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {reportType === 'tax-types' && (
          <>
            <h2>Tax Types ({taxCodes.length})</h2>
            <div className="report-table-wrap" style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Name</th>
                    <th>Rate %</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {taxCodes.map((t) => (
                    <tr key={t.id}>
                      <td>{t.code}</td>
                      <td>{t.name}</td>
                      <td>{t.rate_percent}%</td>
                      <td>
                        <span className={`badge ${t.is_active ? 'active' : 'draft'}`}>{t.is_active ? 'Active' : 'Retired'}</span>
                      </td>
                    </tr>
                  ))}
                  {taxCodes.length === 0 && (
                    <tr>
                      <td colSpan={4} className="muted">
                        No tax types yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {reportType === 'gst-return' && gstReturn && (
          <>
            <h2>
              GST Return: {gstReturn.period_start} to {gstReturn.period_end}
            </h2>
            <p className="muted">
              Tax point = invoice date, output vs input tax only -- this does not file a return or
              post to the GL. Bad-debt relief on written-off invoices is a separate IRAS scheme not
              covered here.
            </p>
            <div className="stat-grid">
              <div className="card stat-tile">
                <div className="stat-value">{money(gstReturn.total_output_tax_sgd)}</div>
                <div className="stat-label">Output tax (sales)</div>
              </div>
              <div className="card stat-tile">
                <div className="stat-value">{money(gstReturn.total_input_tax_sgd)}</div>
                <div className="stat-label">Input tax (purchases)</div>
              </div>
              <div className="card stat-tile">
                <div className="stat-value">{money(gstReturn.net_gst_payable_sgd)}</div>
                <div className="stat-label">{gstReturn.net_gst_payable_sgd >= 0 ? 'Net GST payable' : 'Net GST reclaimable'}</div>
              </div>
            </div>
            <div className="report-table-wrap" style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Direction</th>
                    <th>Tax code</th>
                    <th>Net (SGD)</th>
                    <th>Tax (SGD)</th>
                    <th>Documents</th>
                  </tr>
                </thead>
                <tbody>
                  {gstReturn.output_rows.map((r) => (
                    <tr key={`output-${r.tax_code}`}>
                      <td>Output</td>
                      <td>{r.tax_code}</td>
                      <td>{money(r.net_sgd)}</td>
                      <td>{money(r.tax_sgd)}</td>
                      <td>{r.document_count}</td>
                    </tr>
                  ))}
                  {gstReturn.input_rows.map((r) => (
                    <tr key={`input-${r.tax_code}`}>
                      <td>Input</td>
                      <td>{r.tax_code}</td>
                      <td>{money(r.net_sgd)}</td>
                      <td>{money(r.tax_sgd)}</td>
                      <td>{r.document_count}</td>
                    </tr>
                  ))}
                  {gstReturn.output_rows.length === 0 && gstReturn.input_rows.length === 0 && (
                    <tr>
                      <td colSpan={5} className="muted">
                        No invoices or bills in this date range.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

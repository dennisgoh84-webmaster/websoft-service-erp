// Thin API client for the Websoft Service ERP Solution backend.
// Talks to FastAPI via the Vite dev-server proxy (/api -> :8000).

import { getDeviceId } from './deviceId'

const TOKEN_KEY = 'websoft_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    'X-Device-Id': getDeviceId(),
  }
  const res = await fetch(`/api${path}`, { ...options, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== '')
  if (entries.length === 0) return ''
  return '?' + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()
}

async function requestBlob(path: string): Promise<Blob> {
  const token = getToken()
  const res = await fetch(`/api${path}`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      'X-Device-Id': getDeviceId(),
    },
  })
  if (!res.ok) throw new Error('Export failed')
  return res.blob()
}

/** Triggers a browser download for an already-fetched file (CSV/Excel/
 * Word/...) -- the shared second half of every "Export" button. */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username: email, password })
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Device-Id': getDeviceId() },
    body,
  })
  if (!res.ok) throw new Error('Invalid email or password')
  const data = await res.json()
  return data.access_token as string
}

// ---- Types (mirroring backend Pydantic schemas) ----
export type UserRole = 'owner' | 'service_lead' | 'sales_manager' | 'support_engineer' | 'finance'

export interface CurrentUser {
  id: string
  full_name: string
  email: string
  role: UserRole
  group_id: string | null
  company_id: string | null
}

// ---- Company Setup / multi-company ----
export interface Company {
  id: string
  name: string
  country: string
  currency: string
  timezone: string
  logo: string | null
  address: string | null
  gst_registration_no: string | null
  phone: string | null
  website: string | null
  uen: string | null
  /** Null means "always require owner approval" -- no threshold set yet. */
  write_off_approval_threshold_sgd: number | null
  credit_note_approval_threshold_sgd: number | null
  po_approval_threshold_sgd: number | null
  is_active: boolean
  created_at: string
}

// ---- Staff Master ----
export interface StaffUser {
  id: string
  full_name: string
  email: string
  role: UserRole
  group_id: string | null
  /** Data URI, e.g. "data:image/png;base64,..." -- shown on Staff Master and Support Monitoring. */
  photo: string | null
  is_active: boolean
  created_at: string
}

export interface AuditLogEntry {
  id: string
  entity_type: string
  entity_id: string
  action: string
  actor_user_id: string | null
  actor_name: string | null
  reason: string | null
  details: string | null
  old_value: string | null
  new_value: string | null
  ip_address: string | null
  user_agent: string | null
  device_id: string | null
  at: string
}

export interface EventLogFilters {
  entity_type?: string
  action?: string
  actor_user_id?: string
  date_from?: string
  date_to?: string
  q?: string
  [key: string]: string | number | undefined
}

/** One company a staff member may work in, and their Group there.
 * Group is per company -- see Company Setup / Group Authority. */
export interface UserCompanyAccess {
  company_id: string
  company_name: string
  group_id: string | null
  group_name: string | null
}

// ---- Group Authority ----
export type AccessLevel = 'none' | 'view' | 'edit' | 'full'

export interface GroupAuthority {
  module_key: string
  access_level: AccessLevel
}

export interface Group {
  id: string
  name: string
  description: string | null
  created_at: string
  authorities: GroupAuthority[]
  member_count: number
}

export type CustomerType = 'individual' | 'company'

export interface CustomerGroup {
  id: string
  name: string
  description: string | null
  is_active: boolean
  created_at: string
}

export interface Customer {
  id: string
  customer_type: CustomerType
  name: string
  /** Tag linking this customer to others in the same group of
   * companies -- each stays its own full account. */
  customer_group_id: string | null
  /** The customer's code from the Odoo system being replaced -- manual,
   * for matching during the eventual historical-data migration. */
  legacy_customer_code: string | null
  contact_person: string | null
  uen: string | null
  gst_registration_no: string | null
  billing_email: string | null
  phone: string | null
  mobile: string | null
  website: string | null
  address_line1: string | null
  address_line2: string | null
  address_city: string | null
  address_state: string | null
  address_postal_code: string | null
  address_country: string | null
  tags: string | null
  /** Setup Lists code (list_type=industry) -- optional, for grouping/
   * filtering customers by industry. */
  industry_code: string | null
  /** Reserved -- nothing reads this yet, no automated emailing exists. */
  exclude_auto_sent: boolean
  terms_and_conditions: string | null
  /** Internal-only note, never shown on any customer-facing document. */
  memo: string | null
  /** Billing/AR-specific note (e.g. "requires PO number on invoice"). */
  billing_notes: string | null
  /** Days from invoice date. Terms vary per customer; null = not agreed yet. */
  payment_terms_days: number | null
  is_active: boolean
  created_at: string
}

export interface Contact {
  id: string
  customer_id: string
  name: string
  email: string | null
  phone: string | null
  /** Direct dial line, distinct from the general phone (mobile/shared). */
  direct_line: string | null
  is_active: boolean
}

export interface Branch {
  id: string
  customer_id: string
  branch_name: string
  branch_code: string | null
  address_line1: string | null
  address_line2: string | null
  address_city: string | null
  address_state: string | null
  address_postal_code: string | null
  address_country: string | null
  phone: string | null
  is_active: boolean
}

export interface CustomerRelationship {
  id: string
  from_customer_id: string
  to_customer_id: string | null
  to_customer_name: string | null
  to_customer_type: CustomerType | null
  to_contact_id: string | null
  to_contact_name: string | null
  to_contact_customer_id: string | null
  to_contact_customer_name: string | null
  relationship_type: string
  note: string | null
  is_active: boolean
  created_at: string
}

export type CustomerFields = Partial<{
  customer_type: CustomerType
  name: string
  customer_group_id: string | null
  legacy_customer_code: string | null
  contact_person: string | null
  uen: string | null
  gst_registration_no: string | null
  billing_email: string | null
  phone: string | null
  mobile: string | null
  website: string | null
  address_line1: string | null
  address_line2: string | null
  address_city: string | null
  address_state: string | null
  address_postal_code: string | null
  address_country: string | null
  tags: string | null
  industry_code: string | null
  exclude_auto_sent: boolean
  terms_and_conditions: string | null
  memo: string | null
  billing_notes: string | null
  payment_terms_days: number | null
}>

export type ContractStatus = 'draft' | 'active' | 'exceeded' | 'expired' | 'renewed'

/** The contract type decides its "offset method": service_support
 * deducts hours, annual is time-coverage only (no hours), ad_hoc has
 * neither -- work is billed off the contract's reference hourly_rate_sgd. */
export type ContractKind = 'service_support' | 'annual' | 'ad_hoc'

export interface ContractProductCoverage {
  product_id: string
  product_name: string
}

export interface Contract {
  id: string
  contract_number: string
  customer_id: string
  status: ContractStatus
  contract_kind: ContractKind
  contracted_hours: number
  consumed_hours: number
  remaining_hours: number
  contract_value_sgd: number
  /** Reference rate for ad_hoc contracts only; null otherwise. */
  hourly_rate_sgd: number | null
  sales_staff_id: string | null
  start_date: string
  end_date: string
  renewed_from_contract_id: string | null
  products: ContractProductCoverage[]
}

export type JobOrderPriority = 'low' | 'normal' | 'high' | 'critical'
/** No manual "Resolved" step any more -- a Job Order auto-closes when
 * its most recent Service Record is Approved and marked Completed
 * ('C'). VOID is a manual dead-end for a job that should never have
 * been raised (duplicate, raised in error). */
export type JobOrderStatus = 'open' | 'assigned' | 'closed' | 'void'

export interface JobOrder {
  id: string
  job_order_number: string
  customer_id: string
  contract_id: string | null
  subject: string
  priority: JobOrderPriority
  status: JobOrderStatus
  /** "Tick as Urgent" -- suggests a x1.5 deduction-minutes multiplier on approval. */
  is_urgent: boolean
  assigned_to_user_id: string | null
  /** Manual, optional -- set by Sales/Coordinator after discussion with Support. */
  due_date: string | null
  void_reason: string | null
  created_at: string
  closed_at: string | null
}

// ---- Operations/Accounting Reports filters ----
export interface ContractReportFilters {
  status?: ContractStatus
  contract_kind?: ContractKind
  customer_id?: string
  expiring_within_days?: number
  start_date?: string
  end_date?: string
  [key: string]: string | number | boolean | undefined
}

export interface JobOrderReportFilters {
  status?: JobOrderStatus
  customer_id?: string
  assigned_to_user_id?: string
  overdue_only?: boolean
  start_date?: string
  end_date?: string
  [key: string]: string | number | boolean | undefined
}

export interface ServiceRecordReportFilters {
  status?: ServiceRecordStatus
  outcome?: ServiceRecordOutcome
  customer_id?: string
  employee_user_id?: string
  start_date?: string
  end_date?: string
  [key: string]: string | number | boolean | undefined
}

/** Confirmed 2026-09-11: "check customer using which product" --
 * visibility only, one row per (customer, product) currently covered
 * under a contract's Product Coverage. */
export interface CustomerProductUsageFilters {
  customer_id?: string
  product_id?: string
  industry_code?: string
  [key: string]: string | number | boolean | undefined
}

export interface CustomerProductUsageRow {
  customer_id: string
  customer_name: string
  industry_code: string | null
  industry_name: string
  product_id: string
  product_name: string
  contract_id: string
  contract_number: string
  contract_kind: ContractKind
  contract_status: ContractStatus
  start_date: string
  end_date: string
}

// ---- Support Monitoring ----
export interface StaffMonitoring {
  user_id: string
  full_name: string
  photo: string | null
  open_job_orders: number
  overdue_job_orders: number
  due_soon_job_orders: number
  pending_service_records: number
  untested_software_tasks: number
  cm_svc_records_month: number
  cm_svc_records_today: number
  cm_svc_hours_month: number
  cm_svc_hours_today: number
  avg_daily_contract_hours: number
}

export interface MonitoringSummary {
  total_job_orders: number
  total_open_job_orders: number
  total_overdue_job_orders: number
  unassigned_job_orders: number
  total_pending_service_records: number
  total_untested_software_tasks: number
}

export interface SupportMonitoring {
  as_at: string
  summary: MonitoringSummary
  staff: StaffMonitoring[]
  unassigned: StaffMonitoring
}

// ---- Software Task ----
export interface SoftwareTask {
  id: string
  title: string
  description: string | null
  modules_affected: string | null
  assigned_programmer_id: string | null
  programming_finish_date: string | null
  programming_hours: number | null
  tester_user_id: string | null
  is_tested: boolean
  tested_at: string | null
  created_at: string
}

export type ServiceRecordStatus = 'submitted' | 'approved'
export type ServiceRecordOutcome = 'pending' | 'contract_deduction' | 'excess_usage' | 'not_hour_metered'
/** 'C' = Completed (this visit finished the job), 'U' = Uncompleted
 * (another visit is needed) -- set by the submitter, drives Job Order
 * auto-close. */
export type ServiceRecordCompletion = 'C' | 'U'

export interface ServiceRecord {
  id: string
  service_record_number: string
  job_order_id: string
  employee_user_id: string
  work_date: string
  raw_minutes: number
  rounded_minutes: number
  /** Set by the approver at approval time; null until then. */
  deducted_minutes: number | null
  status: ServiceRecordStatus
  outcome: ServiceRecordOutcome
  completion_status: ServiceRecordCompletion
  is_after_hours: boolean
  is_late: boolean
}

/** One row on the Service Record Approval page -- a Submitted record
 * enriched with what the approver needs (job order, urgency, a
 * suggested deduction) without looking each thing up separately. */
export interface PendingServiceRecord {
  id: string
  service_record_number: string
  job_order_id: string
  job_order_number: string
  job_order_subject: string
  is_urgent: boolean
  employee_user_id: string
  employee_name: string
  work_date: string
  raw_minutes: number
  rounded_minutes: number
  completion_status: ServiceRecordCompletion
  is_after_hours: boolean
  suggested_deducted_minutes: number
  contract_remaining_minutes: number | null
  is_late: boolean
}

export type ExcessTreatment =
  | 'billable'
  | 'approved_non_billable'
  | 'warranty_goodwill'
  | 'internal_write_off'
  | 'other'

export interface ExcessUsageRecord {
  id: string
  contract_id: string
  service_record_id: string
  excess_hours: number
  treatment: ExcessTreatment | null
  reason: string | null
  decided_by_user_id: string | null
  invoiced: boolean
}

export type InvoiceStatus = 'outstanding' | 'partially_paid' | 'paid' | 'written_off'

export interface Invoice {
  id: string
  invoice_number: string
  customer_id: string
  contract_id: string | null
  invoice_type: string
  description: string
  /** Net of GST -- the revenue figure. */
  amount_sgd: number
  tax_code: string
  gst_rate: number
  gst_amount_sgd: number
  total_amount_sgd: number
  amount_paid_sgd: number
  outstanding_sgd: number
  due_date: string | null
  status: InvoiceStatus
  is_disputed: boolean
  dispute_note: string | null
  issued_at: string
}

// ---- Accounts Receivable ----
export interface PaymentAllocation {
  id: string
  invoice_id: string
  invoice_number: string | null
  amount_sgd: number
}

export interface Payment {
  id: string
  voucher_number: string
  customer_id: string
  payment_date: string
  amount_sgd: number
  allocated_sgd: number
  unallocated_sgd: number
  method: string
  reference: string | null
  notes: string | null
  allocations: PaymentAllocation[]
}

export interface AgingRow {
  customer_id: string
  customer_name: string
  current: number
  days_1_30: number
  days_31_60: number
  days_61_90: number
  over_90: number
  total: number
}

export interface AgingReport {
  as_at: string
  rows: AgingRow[]
  current: number
  days_1_30: number
  days_31_60: number
  days_61_90: number
  over_90: number
  total: number
}

export interface StatementLine {
  invoice_id: string
  invoice_number: string
  description: string
  issued_on: string
  due_date: string | null
  total_amount_sgd: number
  amount_paid_sgd: number
  outstanding_sgd: number
  status: InvoiceStatus
  is_disputed: boolean
  days_overdue: number
}

export interface CustomerStatement {
  customer_id: string
  customer_name: string
  as_at: string
  payment_terms_days: number | null
  lines: StatementLine[]
  total_outstanding_sgd: number
  unallocated_credit_sgd: number
}

// ---- Chart of Accounts ----
export type AccountType = 'asset' | 'liability' | 'equity' | 'revenue' | 'expense'

export interface Account {
  id: string
  code: string
  name: string
  account_type: AccountType
  description: string | null
  is_active: boolean
}

// ---- GL Types ----
export interface GLType {
  id: string
  code: string
  name: string
  account_type: AccountType
  is_active: boolean
}

// ---- Setup Lists (Nationality / Country / State / Area Code / Currency / Industry) ----
export type SetupListType = 'nationality' | 'country' | 'state' | 'area_code' | 'currency' | 'industry'

export interface SetupListItem {
  id: string
  list_type: SetupListType
  code: string
  name: string
  parent_code: string | null
  sort_order: number
  is_active: boolean
}

// ---- Currency Rate Table ----
export interface CurrencyRate {
  id: string
  currency_code: string
  rate_to_base: number
  effective_date: string
  is_active: boolean
}

// ---- Bank Master File ----
export interface BankAccount {
  id: string
  bank_name: string
  account_name: string
  account_number: string
  branch: string | null
  swift_code: string | null
  currency_code: string
  gl_account_id: string | null
  is_active: boolean
}

// ---- Tax Type (Tax Code maintenance) ----
export interface TaxCode {
  id: string
  code: string
  name: string
  rate_percent: number
  is_active: boolean
}

// ---- Document Control ----
export interface DocumentSequence {
  id: string
  doc_kind: string
  prefix: string
  year: number
  last_number: number
  next_number: string
}

/** Confirmed 2026-09-11: "customization of the running number
 * formatting and front alphabet." A doc_kind with is_custom=false is
 * showing the built-in default, not an explicit override. */
export interface DocumentNumberFormat {
  doc_kind: string
  prefix: string
  number_length: number
  include_year: boolean
  is_custom: boolean
  example: string
}

// ---- Accounting Periods / Year-End Closing ----
export type PeriodStatus = 'open' | 'closed'

export interface AccountingPeriod {
  id: string
  fiscal_year: number
  name: string
  period_start: string
  period_end: string
  status: PeriodStatus
  closed_at: string | null
}

export interface FiscalYearClosure {
  id: string
  fiscal_year: number
  retained_earnings_account_id: string
  closing_journal_entry_id: string
  closed_at: string
}

// ---- GST Return ----
export interface GSTReturnRow {
  tax_code: string
  net_sgd: number
  tax_sgd: number
  document_count: number
}

export interface GSTReturn {
  period_start: string
  period_end: string
  output_rows: GSTReturnRow[]
  input_rows: GSTReturnRow[]
  total_output_tax_sgd: number
  total_input_tax_sgd: number
  net_gst_payable_sgd: number
}

// ---- Ops Dashboard (personal task tracker, confirmed 2026-09-11) ----
export type OpsTaskStatus = 'not_started' | 'in_progress' | 'watch' | 'blocked' | 'done'

export interface OpsTaskCategory {
  id: string
  owner_user_id: string
  name: string
  cadence_label: string | null
  sort_order: number
}

export interface OpsTask {
  id: string
  category_id: string
  owner_user_id: string
  title: string
  status: OpsTaskStatus
  next_action: string | null
  owner_label: string | null
  due_label: string | null
  follow_up_staff_id: string | null
  follow_up_staff_name: string | null
  follow_up_date: string | null
  is_sample: boolean
}

export interface OpsDashboardCategory {
  category: OpsTaskCategory
  tasks: OpsTask[]
}

export interface OpsRollupJobOrder {
  id: string
  job_order_number: string
  subject: string
  status: string
  due_date: string | null
}

export interface OpsRollupSoftwareTask {
  id: string
  title: string
  role: string
  is_tested: boolean
}

export interface OpsDashboard {
  staff_id: string
  staff_name: string
  can_view_others: boolean
  categories: OpsDashboardCategory[]
  total_tasks: number
  open_count: number
  in_progress_count: number
  blocked_count: number
  done_count: number
  my_job_orders: OpsRollupJobOrder[]
  my_software_tasks: OpsRollupSoftwareTask[]
}

// ---- General Ledger / vouchers ----
export type VoucherType = 'journal' | 'receipt' | 'payment' | 'sales_invoice' | 'purchase_invoice'
export type JournalStatus = 'draft' | 'posted' | 'reversed'

export interface JournalLine {
  id: string
  account_id: string
  account_code: string | null
  account_name: string | null
  debit_sgd: number
  credit_sgd: number
  description: string | null
}

export interface JournalEntry {
  id: string
  voucher_number: string
  voucher_type: VoucherType
  entry_date: string
  narration: string
  status: JournalStatus
  total_debit: number
  total_credit: number
  is_balanced: boolean
  reverses_entry_id: string | null
  lines: JournalLine[]
}

export interface TrialBalanceRow {
  account_id: string
  code: string
  name: string
  account_type: AccountType
  debit_sgd: number
  credit_sgd: number
  balance_sgd: number
}

export interface TrialBalance {
  as_at: string | null
  rows: TrialBalanceRow[]
  total_debit: number
  total_credit: number
  is_balanced: boolean
}

// ---- Accounts Payable ----
export type PurchaseOrderStatus = 'draft' | 'pending_approval' | 'approved' | 'cancelled'
export type BillMatchStatus = 'not_matched' | 'matched' | 'exception'
export type BillStatus = 'awaiting_match' | 'exception' | 'approved' | 'partially_paid' | 'paid'

export interface Supplier {
  id: string
  name: string
  email: string | null
  phone: string | null
  address: string | null
  gst_registration_no: string | null
  payment_terms_days: number | null
  is_active: boolean
}

export interface PurchaseOrder {
  id: string
  po_number: string
  supplier_id: string
  order_date: string
  description: string
  amount_sgd: number
  gst_amount_sgd: number
  total_amount_sgd: number
  status: PurchaseOrderStatus
  imported_bill_id: string | null
  imported_bill_number: string | null
}

export interface SupplierInvoice {
  id: string
  bill_number: string
  supplier_invoice_no: string | null
  supplier_id: string
  purchase_order_id: string | null
  invoice_date: string
  due_date: string | null
  description: string
  amount_sgd: number
  gst_amount_sgd: number
  total_amount_sgd: number
  amount_paid_sgd: number
  outstanding_sgd: number
  match_status: BillMatchStatus
  match_note: string | null
  status: BillStatus
}

export interface SupplierPaymentAllocation {
  id: string
  supplier_invoice_id: string
  bill_number: string | null
  amount_sgd: number
}

export interface SupplierPayment {
  id: string
  voucher_number: string
  supplier_id: string
  payment_date: string
  amount_sgd: number
  allocated_sgd: number
  unallocated_sgd: number
  method: string
  reference: string | null
  allocations: SupplierPaymentAllocation[]
}

export interface APAgingRow {
  supplier_id: string
  supplier_name: string
  current: number
  days_1_30: number
  days_31_60: number
  days_61_90: number
  over_90: number
  total: number
}

export interface APAgingReport {
  as_at: string
  rows: APAgingRow[]
  total: number
}

export type LicenseType = 'included' | 'add_on' | 'trial'

export interface ModuleInfo {
  key: string
  name: string
  description: string | null
  is_built: boolean
  enabled: boolean
  license_type: LicenseType
}

export interface DashboardSummary {
  active_contracts: number
  contracts_expiring_soon: number
  total_contracted_hours: number
  total_consumed_hours: number
  total_remaining_hours: number
  excess_awaiting_review: number
  open_job_orders: number
  missing_service_records: number
  invoices_total_sgd: number
  invoices_count: number
  ar_outstanding_sgd: number
  ar_overdue_sgd: number
  ap_outstanding_sgd: number
  ap_overdue_sgd: number
  gl_is_balanced: boolean
}

// ---- Product / Service Catalog ----
export type ProductType = 'service' | 'product'

export interface Product {
  id: string
  product_type: ProductType
  name: string
  internal_reference: string | null
  product_category: string | null
  tags: string | null
  sales_price_sgd: number
  cost_sgd: number | null
  unit_of_measure: string | null
  tax_code: string
  is_active: boolean
  created_at: string
}

// ---- Sales Quotation ----
export type QuotationStatus = 'draft' | 'sent' | 'accepted' | 'rejected' | 'expired'

export interface QuotationLine {
  id: string
  product_id: string | null
  description: string
  unit_of_measure: string | null
  quantity: number
  unit_price_sgd: number
  line_total_sgd: number
}

export interface Quotation {
  id: string
  quotation_number: string
  customer_id: string
  quotation_date: string
  valid_until: string | null
  status: QuotationStatus
  notes: string | null
  amount_sgd: number
  tax_code: string
  gst_rate: number
  gst_amount_sgd: number
  total_amount_sgd: number
  converted_contract_id: string | null
  converted_annual_contract_id: string | null
  created_at: string
  lines: QuotationLine[]
}

export const api = {
  me: () => request<CurrentUser>('/auth/me'),
  listUsers: () => request<CurrentUser[]>('/users'),

  // Company Setup / multi-company
  listMyCompanies: () => request<Company[]>('/companies'),
  createCompany: (payload: {
    name: string
    country?: string
    currency?: string
    timezone?: string
    logo?: string | null
  }) => request<Company>('/companies', { method: 'POST', body: JSON.stringify(payload) }),
  updateCompany: (
    id: string,
    payload: {
      name?: string
      country?: string
      currency?: string
      timezone?: string
      logo?: string | null
      address?: string | null
      gst_registration_no?: string | null
      phone?: string | null
      website?: string | null
      uen?: string | null
      write_off_approval_threshold_sgd?: number | null
      credit_note_approval_threshold_sgd?: number | null
      po_approval_threshold_sgd?: number | null
      is_active?: boolean
    },
  ) => request<Company>(`/companies/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  switchCompany: (id: string) => request<Company>(`/companies/${id}/switch`, { method: 'POST' }),

  // Staff Master (full CRUD; distinct from the plain listUsers directory above)
  listStaff: (includeInactive = false) =>
    request<StaffUser[]>(`/users${includeInactive ? '?include_inactive=true' : ''}`),
  exportStaffCsv: (includeInactive = false) =>
    requestBlob(`/users/export.csv${includeInactive ? '?include_inactive=true' : ''}`),
  exportStaffExcel: (includeInactive = false) =>
    requestBlob(`/users/export.xlsx${includeInactive ? '?include_inactive=true' : ''}`),
  getStaff: (id: string) => request<StaffUser>(`/users/${id}`),
  createStaff: (payload: {
    full_name: string
    email: string
    password: string
    role: UserRole
    group_id?: string | null
  }) => request<StaffUser>('/users', { method: 'POST', body: JSON.stringify(payload) }),
  updateStaff: (
    id: string,
    payload: { full_name?: string; role?: UserRole; group_id?: string | null; photo?: string | null },
  ) => request<StaffUser>(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deactivateStaff: (id: string) => request<StaffUser>(`/users/${id}/deactivate`, { method: 'POST' }),
  reactivateStaff: (id: string) => request<StaffUser>(`/users/${id}/reactivate`, { method: 'POST' }),
  resetStaffPassword: (id: string, new_password: string) =>
    request<StaffUser>(`/users/${id}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ new_password }),
    }),
  getStaffAuditLog: (id: string) => request<AuditLogEntry[]>(`/users/${id}/audit-log`),
  getStaffCompanyAccess: (id: string) =>
    request<UserCompanyAccess[]>(`/users/${id}/company-access`),
  setStaffCompanyAccess: (
    id: string,
    access: { company_id: string; group_id: string | null }[],
  ) =>
    request<UserCompanyAccess[]>(`/users/${id}/company-access`, {
      method: 'PUT',
      body: JSON.stringify({ access }),
    }),

  // Group Authority
  listGroups: (companyId?: string) =>
    request<Group[]>(`/groups${companyId ? `?company_id=${companyId}` : ''}`),
  exportGroupsCsv: (companyId?: string) =>
    requestBlob(`/groups/export.csv${companyId ? `?company_id=${companyId}` : ''}`),
  exportGroupsExcel: (companyId?: string) =>
    requestBlob(`/groups/export.xlsx${companyId ? `?company_id=${companyId}` : ''}`),
  createGroup: (name: string, description?: string) =>
    request<Group>('/groups', { method: 'POST', body: JSON.stringify({ name, description }) }),
  updateGroup: (id: string, payload: { name?: string; description?: string }) =>
    request<Group>(`/groups/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteGroup: (id: string) => request<void>(`/groups/${id}`, { method: 'DELETE' }),
  setGroupAuthorities: (id: string, authorities: GroupAuthority[]) =>
    request<Group>(`/groups/${id}/authorities`, {
      method: 'PUT',
      body: JSON.stringify({ authorities }),
    }),

  dashboardSummary: () => request<DashboardSummary>('/dashboard/summary'),

  listModules: () => request<ModuleInfo[]>('/modules'),
  toggleModule: (key: string, enabled: boolean) =>
    request<ModuleInfo>(`/modules/${key}/toggle`, { method: 'POST', body: JSON.stringify({ enabled }) }),
  /** module_key -> can the current user reach it right now (Group Authority AND
   * Module Control both say yes)? Drives which nav links show at all. */
  myModuleAccess: () => request<Record<string, boolean>>('/modules/my-access'),

  // Dynamic filter: free-text `q` matches name/email/phone/mobile/UEN/
  // legacy code/tags; customer_group_id pulls up a whole group of
  // companies together; industry_code narrows to one industry
  // (confirmed 2026-09-11: customer grouping by industry); includeInactive
  // reveals deactivated customers.
  listCustomers: (
    filters: { q?: string; customer_group_id?: string; industry_code?: string; include_inactive?: boolean } = {},
  ) =>
    request<Customer[]>(
      `/customers${qs({
        q: filters.q,
        customer_group_id: filters.customer_group_id,
        industry_code: filters.industry_code,
        include_inactive: filters.include_inactive ? 'true' : undefined,
      })}`,
    ),
  exportCustomersCsv: (
    filters: { q?: string; customer_group_id?: string; industry_code?: string; include_inactive?: boolean } = {},
  ) =>
    requestBlob(
      `/customers/export.csv${qs({
        q: filters.q,
        customer_group_id: filters.customer_group_id,
        industry_code: filters.industry_code,
        include_inactive: filters.include_inactive ? 'true' : undefined,
      })}`,
    ),
  exportCustomersExcel: (
    filters: { q?: string; customer_group_id?: string; industry_code?: string; include_inactive?: boolean } = {},
  ) =>
    requestBlob(
      `/customers/export.xlsx${qs({
        q: filters.q,
        customer_group_id: filters.customer_group_id,
        industry_code: filters.industry_code,
        include_inactive: filters.include_inactive ? 'true' : undefined,
      })}`,
    ),
  getCustomer: (id: string) => request<Customer>(`/customers/${id}`),
  createCustomer: (payload: CustomerFields & { name: string }) =>
    request<Customer>('/customers', { method: 'POST', body: JSON.stringify(payload) }),
  updateCustomer: (id: string, payload: CustomerFields) =>
    request<Customer>(`/customers/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deactivateCustomer: (id: string) => request<Customer>(`/customers/${id}/deactivate`, { method: 'POST' }),
  reactivateCustomer: (id: string) => request<Customer>(`/customers/${id}/reactivate`, { method: 'POST' }),
  getCustomerAuditLog: (id: string) => request<AuditLogEntry[]>(`/customers/${id}/audit-log`),

  // Customer Groups (tag linking separate companies in one group)
  listCustomerGroups: (includeInactive = false) =>
    request<CustomerGroup[]>(`/customer-groups${includeInactive ? '?include_inactive=true' : ''}`),
  createCustomerGroup: (payload: { name: string; description?: string }) =>
    request<CustomerGroup>('/customer-groups', { method: 'POST', body: JSON.stringify(payload) }),
  updateCustomerGroup: (id: string, payload: { name?: string; description?: string; is_active?: boolean }) =>
    request<CustomerGroup>(`/customer-groups/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

  listContacts: (customerId: string, includeInactive = false) =>
    request<Contact[]>(`/customers/${customerId}/contacts${includeInactive ? '?include_inactive=true' : ''}`),
  createContact: (
    customerId: string,
    payload: { name: string; email?: string; phone?: string; direct_line?: string },
  ) => request<Contact>(`/customers/${customerId}/contacts`, { method: 'POST', body: JSON.stringify(payload) }),
  updateContact: (
    customerId: string,
    contactId: string,
    payload: { name?: string; email?: string | null; phone?: string | null; direct_line?: string | null },
  ) =>
    request<Contact>(`/customers/${customerId}/contacts/${contactId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deactivateContact: (customerId: string, contactId: string) =>
    request<Contact>(`/customers/${customerId}/contacts/${contactId}/deactivate`, { method: 'POST' }),
  reactivateContact: (customerId: string, contactId: string) =>
    request<Contact>(`/customers/${customerId}/contacts/${contactId}/reactivate`, { method: 'POST' }),

  listBranches: (customerId: string, includeInactive = false) =>
    request<Branch[]>(`/customers/${customerId}/branches${includeInactive ? '?include_inactive=true' : ''}`),
  createBranch: (
    customerId: string,
    payload: {
      branch_name: string
      branch_code?: string
      address_line1?: string
      address_line2?: string
      address_city?: string
      address_state?: string
      address_postal_code?: string
      address_country?: string
      phone?: string
    },
  ) => request<Branch>(`/customers/${customerId}/branches`, { method: 'POST', body: JSON.stringify(payload) }),
  updateBranch: (
    customerId: string,
    branchId: string,
    payload: Partial<{
      branch_name: string
      branch_code: string | null
      address_line1: string | null
      address_line2: string | null
      address_city: string | null
      address_state: string | null
      address_postal_code: string | null
      address_country: string | null
      phone: string | null
    }>,
  ) =>
    request<Branch>(`/customers/${customerId}/branches/${branchId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deactivateBranch: (customerId: string, branchId: string) =>
    request<Branch>(`/customers/${customerId}/branches/${branchId}/deactivate`, { method: 'POST' }),
  reactivateBranch: (customerId: string, branchId: string) =>
    request<Branch>(`/customers/${customerId}/branches/${branchId}/reactivate`, { method: 'POST' }),

  listCustomerRelationships: (customerId: string) =>
    request<CustomerRelationship[]>(`/customers/${customerId}/relationships`),
  createCustomerRelationship: (
    customerId: string,
    payload: { to_customer_id?: string; to_contact_id?: string; relationship_type: string; note?: string },
  ) =>
    request<CustomerRelationship>(`/customers/${customerId}/relationships`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  deactivateCustomerRelationship: (customerId: string, relationshipId: string) =>
    request<CustomerRelationship>(`/customers/${customerId}/relationships/${relationshipId}/deactivate`, {
      method: 'POST',
    }),

  listContracts: (
    filters: {
      status?: string
      customer_id?: string
      contract_kind?: ContractKind
      sales_staff_id?: string
      product_id?: string
      coverage_start?: string
      coverage_end?: string
    } = {},
  ) => request<Contract[]>(`/contracts${qs(filters)}`),
  exportContractsCsv: (filters: Record<string, string | undefined> = {}) =>
    requestBlob(`/contracts/export.csv${qs(filters)}`),
  exportContractsExcel: (filters: Record<string, string | undefined> = {}) =>
    requestBlob(`/contracts/export.xlsx${qs(filters)}`),
  getContract: (id: string) => request<Contract>(`/contracts/${id}`),
  createContract: (payload: {
    customer_id: string
    contract_kind?: ContractKind
    contracted_hours: number
    contract_value_sgd: number
    start_date: string
    hourly_rate_sgd?: number | null
    sales_staff_id?: string | null
    product_ids?: string[]
  }) => request<Contract>('/contracts', { method: 'POST', body: JSON.stringify(payload) }),
  updateContract: (id: string, payload: { sales_staff_id?: string | null; product_ids?: string[] }) =>
    request<Contract>(`/contracts/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  activateContract: (id: string) => request<Contract>(`/contracts/${id}/activate`, { method: 'POST' }),
  renewContract: (
    id: string,
    payload: {
      contracted_hours: number
      contract_value_sgd: number
      force_start_date?: string
      hourly_rate_sgd?: number | null
    },
  ) => request<Contract>(`/contracts/${id}/renew`, { method: 'POST', body: JSON.stringify(payload) }),
  listContractExcessUsage: (id: string) =>
    request<ExcessUsageRecord[]>(`/contracts/${id}/excess-usage`),

  listJobOrders: (
    filters: { status?: string; priority?: string; customer_id?: string; contract_id?: string } = {},
  ) => request<JobOrder[]>(`/job-orders${qs(filters)}`),
  exportJobOrdersCsv: (
    filters: { status?: string; priority?: string; customer_id?: string; contract_id?: string } = {},
  ) => requestBlob(`/job-orders/export.csv${qs(filters)}`),
  exportJobOrdersExcel: (
    filters: { status?: string; priority?: string; customer_id?: string; contract_id?: string } = {},
  ) => requestBlob(`/job-orders/export.xlsx${qs(filters)}`),
  getJobOrder: (id: string) => request<JobOrder>(`/job-orders/${id}`),
  createJobOrder: (payload: {
    customer_id: string
    contract_id: string
    subject: string
    priority?: JobOrderPriority
    due_date?: string | null
    is_urgent?: boolean
  }) => request<JobOrder>('/job-orders', { method: 'POST', body: JSON.stringify(payload) }),
  assignJobOrder: (id: string, assigned_to_user_id: string) =>
    request<JobOrder>(`/job-orders/${id}/assign`, { method: 'POST', body: JSON.stringify({ assigned_to_user_id }) }),
  setJobOrderDueDate: (id: string, due_date: string | null) =>
    request<JobOrder>(`/job-orders/${id}/due-date`, { method: 'POST', body: JSON.stringify({ due_date }) }),
  setJobOrderUrgent: (id: string, is_urgent: boolean) =>
    request<JobOrder>(`/job-orders/${id}/urgent`, { method: 'POST', body: JSON.stringify({ is_urgent }) }),
  voidJobOrder: (id: string, reason: string) =>
    request<JobOrder>(`/job-orders/${id}/void`, { method: 'POST', body: JSON.stringify({ reason }) }),
  reopenJobOrder: (id: string) => request<JobOrder>(`/job-orders/${id}/reopen`, { method: 'POST' }),

  supportMonitoring: () => request<SupportMonitoring>('/monitoring/support'),

  // Software Task
  listSoftwareTasks: (
    filters: { assigned_programmer_id?: string; tester_user_id?: string; untested_only?: boolean } = {},
  ) =>
    request<SoftwareTask[]>(
      `/software-tasks${qs({
        assigned_programmer_id: filters.assigned_programmer_id,
        tester_user_id: filters.tester_user_id,
        untested_only: filters.untested_only ? 'true' : undefined,
      })}`,
    ),
  exportSoftwareTasksCsv: (
    filters: { assigned_programmer_id?: string; tester_user_id?: string; untested_only?: boolean } = {},
  ) =>
    requestBlob(
      `/software-tasks/export.csv${qs({
        assigned_programmer_id: filters.assigned_programmer_id,
        tester_user_id: filters.tester_user_id,
        untested_only: filters.untested_only ? 'true' : undefined,
      })}`,
    ),
  exportSoftwareTasksExcel: (
    filters: { assigned_programmer_id?: string; tester_user_id?: string; untested_only?: boolean } = {},
  ) =>
    requestBlob(
      `/software-tasks/export.xlsx${qs({
        assigned_programmer_id: filters.assigned_programmer_id,
        tester_user_id: filters.tester_user_id,
        untested_only: filters.untested_only ? 'true' : undefined,
      })}`,
    ),
  createSoftwareTask: (payload: {
    title: string
    description?: string
    modules_affected?: string
    assigned_programmer_id?: string
    programming_finish_date?: string
    programming_hours?: number
    tester_user_id?: string
  }) => request<SoftwareTask>('/software-tasks', { method: 'POST', body: JSON.stringify(payload) }),
  updateSoftwareTask: (
    id: string,
    payload: Partial<{
      title: string
      description: string | null
      modules_affected: string | null
      assigned_programmer_id: string | null
      programming_finish_date: string | null
      programming_hours: number | null
      tester_user_id: string | null
    }>,
  ) => request<SoftwareTask>(`/software-tasks/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  markSoftwareTaskTested: (id: string) =>
    request<SoftwareTask>(`/software-tasks/${id}/mark-tested`, { method: 'POST' }),
  reopenSoftwareTaskTesting: (id: string) =>
    request<SoftwareTask>(`/software-tasks/${id}/reopen-testing`, { method: 'POST' }),

  listServiceRecords: (filters: { job_order_id?: string; employee_user_id?: string; status?: string } = {}) =>
    request<ServiceRecord[]>(`/service-records${qs(filters)}`),
  exportServiceRecordsCsv: (filters: { job_order_id?: string; employee_user_id?: string; status?: string } = {}) =>
    requestBlob(`/service-records/export.csv${qs(filters)}`),
  exportServiceRecordsExcel: (filters: { job_order_id?: string; employee_user_id?: string; status?: string } = {}) =>
    requestBlob(`/service-records/export.xlsx${qs(filters)}`),
  submitServiceRecord: (payload: {
    job_order_id: string
    employee_user_id: string
    work_date: string
    raw_minutes: number
    completion_status?: ServiceRecordCompletion
    is_after_hours?: boolean
  }) => request<ServiceRecord>('/service-records', { method: 'POST', body: JSON.stringify(payload) }),
  listPendingServiceRecordApprovals: () => request<PendingServiceRecord[]>('/service-records/pending-approval'),
  approveServiceRecord: (id: string, deducted_minutes: number) =>
    request<ServiceRecord>(`/service-records/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ deducted_minutes }),
    }),

  listExcessUsage: (pendingOnly = false) =>
    request<ExcessUsageRecord[]>(`/excess-usage${pendingOnly ? '?pending_only=true' : ''}`),
  exportExcessUsageCsv: (pendingOnly = false) =>
    requestBlob(`/excess-usage/export.csv${pendingOnly ? '?pending_only=true' : ''}`),
  exportExcessUsageExcel: (pendingOnly = false) =>
    requestBlob(`/excess-usage/export.xlsx${pendingOnly ? '?pending_only=true' : ''}`),
  decideExcessUsage: (id: string, treatment: ExcessTreatment, reason: string) =>
    request<ExcessUsageRecord>(`/excess-usage/${id}/decide`, {
      method: 'POST',
      body: JSON.stringify({ treatment, reason }),
    }),

  listInvoices: (filters: { customer_id?: string; contract_id?: string } = {}) =>
    request<Invoice[]>(`/invoices${qs(filters)}`),
  getInvoice: (id: string) => request<Invoice>(`/invoices/${id}`),
  exportInvoicesCsv: (filters: { customer_id?: string; contract_id?: string } = {}) =>
    requestBlob(`/invoices/export.csv${qs(filters)}`),
  exportInvoicesExcel: (filters: { customer_id?: string; contract_id?: string } = {}) =>
    requestBlob(`/invoices/export.xlsx${qs(filters)}`),
  exportInvoiceDocx: (id: string) => requestBlob(`/invoices/${id}/export.docx`),

  // Accounts Receivable
  listPayments: (filters: { customer_id?: string; unallocated_only?: boolean } = {}) =>
    request<Payment[]>(
      `/accounts-receivable/payments${qs({
        customer_id: filters.customer_id,
        unallocated_only: filters.unallocated_only ? 'true' : undefined,
      })}`,
    ),
  recordPayment: (payload: {
    customer_id: string
    payment_date: string
    amount_sgd: number
    method?: string
    reference?: string
    notes?: string
    allocations?: { invoice_id: string; amount_sgd: number }[]
  }) =>
    request<Payment>('/accounts-receivable/payments', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  exportPaymentsCsv: (filters: { customer_id?: string; unallocated_only?: boolean } = {}) =>
    requestBlob(
      `/accounts-receivable/payments/export.csv${qs({
        customer_id: filters.customer_id,
        unallocated_only: filters.unallocated_only ? 'true' : undefined,
      })}`,
    ),
  exportPaymentsExcel: (filters: { customer_id?: string; unallocated_only?: boolean } = {}) =>
    requestBlob(
      `/accounts-receivable/payments/export.xlsx${qs({
        customer_id: filters.customer_id,
        unallocated_only: filters.unallocated_only ? 'true' : undefined,
      })}`,
    ),
  getPayment: (id: string) => request<Payment>(`/accounts-receivable/payments/${id}`),
  exportPaymentDocx: (id: string) => requestBlob(`/accounts-receivable/payments/${id}/export.docx`),
  allocatePayment: (id: string, allocations: { invoice_id: string; amount_sgd: number }[]) =>
    request<Payment>(`/accounts-receivable/payments/${id}/allocate`, {
      method: 'POST',
      body: JSON.stringify({ allocations }),
    }),
  // General Ledger
  listVouchers: (filters: { voucher_type?: string; status?: string } = {}) =>
    request<JournalEntry[]>(`/ledger/vouchers${qs(filters)}`),
  exportVouchersCsv: (filters: { voucher_type?: string; status?: string } = {}) =>
    requestBlob(`/ledger/vouchers/export.csv${qs(filters)}`),
  exportVouchersExcel: (filters: { voucher_type?: string; status?: string } = {}) =>
    requestBlob(`/ledger/vouchers/export.xlsx${qs(filters)}`),
  getVoucher: (id: string) => request<JournalEntry>(`/ledger/vouchers/${id}`),
  createJournalVoucher: (payload: {
    entry_date: string
    narration: string
    post?: boolean
    lines: { account_id: string; debit_sgd?: number; credit_sgd?: number; description?: string }[]
  }) => request<JournalEntry>('/ledger/vouchers', { method: 'POST', body: JSON.stringify(payload) }),
  postVoucher: (id: string) => request<JournalEntry>(`/ledger/vouchers/${id}/post`, { method: 'POST' }),
  reverseVoucher: (id: string, reason: string) =>
    request<JournalEntry>(`/ledger/vouchers/${id}/reverse`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  trialBalance: (as_at?: string) => request<TrialBalance>(`/ledger/trial-balance${qs({ as_at })}`),
  exportTrialBalanceCsv: (as_at?: string) => requestBlob(`/ledger/trial-balance/export.csv${qs({ as_at })}`),
  exportTrialBalanceExcel: (as_at?: string) => requestBlob(`/ledger/trial-balance/export.xlsx${qs({ as_at })}`),

  // Accounts Payable
  listSuppliers: (includeInactive = false) =>
    request<Supplier[]>(`/accounts-payable/suppliers${qs({ include_inactive: includeInactive ? 'true' : undefined })}`),
  exportSuppliersCsv: (includeInactive = false) =>
    requestBlob(`/accounts-payable/suppliers/export.csv${qs({ include_inactive: includeInactive ? 'true' : undefined })}`),
  exportSuppliersExcel: (includeInactive = false) =>
    requestBlob(`/accounts-payable/suppliers/export.xlsx${qs({ include_inactive: includeInactive ? 'true' : undefined })}`),
  createSupplier: (payload: {
    name: string
    email?: string
    phone?: string
    address?: string
    gst_registration_no?: string
    payment_terms_days?: number | null
  }) => request<Supplier>('/accounts-payable/suppliers', { method: 'POST', body: JSON.stringify(payload) }),
  updateSupplier: (
    id: string,
    payload: Partial<{
      name: string
      email: string | null
      phone: string | null
      address: string | null
      gst_registration_no: string | null
      payment_terms_days: number | null
      is_active: boolean
    }>,
  ) => request<Supplier>(`/accounts-payable/suppliers/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

  listPurchaseOrders: (filters: { supplier_id?: string; status?: string } = {}) =>
    request<PurchaseOrder[]>(`/accounts-payable/purchase-orders${qs(filters)}`),
  getPurchaseOrder: (id: string) => request<PurchaseOrder>(`/accounts-payable/purchase-orders/${id}`),
  exportPurchaseOrdersCsv: (filters: { supplier_id?: string; status?: string } = {}) =>
    requestBlob(`/accounts-payable/purchase-orders/export.csv${qs(filters)}`),
  exportPurchaseOrdersExcel: (filters: { supplier_id?: string; status?: string } = {}) =>
    requestBlob(`/accounts-payable/purchase-orders/export.xlsx${qs(filters)}`),
  exportPurchaseOrderDocx: (id: string) => requestBlob(`/accounts-payable/purchase-orders/${id}/export.docx`),
  createPurchaseOrder: (payload: {
    supplier_id: string
    order_date: string
    description: string
    amount_sgd: number
  }) => request<PurchaseOrder>('/accounts-payable/purchase-orders', { method: 'POST', body: JSON.stringify(payload) }),
  approvePurchaseOrder: (id: string) =>
    request<PurchaseOrder>(`/accounts-payable/purchase-orders/${id}/approve`, { method: 'POST' }),
  importPurchaseOrderToAP: (id: string) =>
    request<SupplierInvoice>(`/accounts-payable/purchase-orders/${id}/import-to-ap`, { method: 'POST' }),
  emailPurchaseOrder: (id: string) =>
    request<{ sent: boolean; to: string }>(`/accounts-payable/purchase-orders/${id}/email`, { method: 'POST' }),

  listBills: (filters: { supplier_id?: string; status?: string } = {}) =>
    request<SupplierInvoice[]>(`/accounts-payable/bills${qs(filters)}`),
  exportBillsCsv: (filters: { supplier_id?: string; status?: string } = {}) =>
    requestBlob(`/accounts-payable/bills/export.csv${qs(filters)}`),
  exportBillsExcel: (filters: { supplier_id?: string; status?: string } = {}) =>
    requestBlob(`/accounts-payable/bills/export.xlsx${qs(filters)}`),
  createBill: (payload: {
    supplier_id: string
    purchase_order_id?: string | null
    supplier_invoice_no?: string
    invoice_date: string
    description: string
    amount_sgd: number
    gst_amount_sgd?: number
  }) => request<SupplierInvoice>('/accounts-payable/bills', { method: 'POST', body: JSON.stringify(payload) }),

  listSupplierPayments: (supplierId?: string) =>
    request<SupplierPayment[]>(`/accounts-payable/payments${qs({ supplier_id: supplierId })}`),
  exportSupplierPaymentsCsv: (supplierId?: string) =>
    requestBlob(`/accounts-payable/payments/export.csv${qs({ supplier_id: supplierId })}`),
  exportSupplierPaymentsExcel: (supplierId?: string) =>
    requestBlob(`/accounts-payable/payments/export.xlsx${qs({ supplier_id: supplierId })}`),
  getSupplierPayment: (id: string) => request<SupplierPayment>(`/accounts-payable/payments/${id}`),
  exportSupplierPaymentDocx: (id: string) => requestBlob(`/accounts-payable/payments/${id}/export.docx`),
  recordSupplierPayment: (payload: {
    supplier_id: string
    payment_date: string
    amount_sgd: number
    method?: string
    reference?: string
    notes?: string
    allocations?: { supplier_invoice_id: string; amount_sgd: number }[]
  }) => request<SupplierPayment>('/accounts-payable/payments', { method: 'POST', body: JSON.stringify(payload) }),
  allocateSupplierPayment: (id: string, allocations: { supplier_invoice_id: string; amount_sgd: number }[]) =>
    request<SupplierPayment>(`/accounts-payable/payments/${id}/allocate`, {
      method: 'POST',
      body: JSON.stringify({ allocations }),
    }),
  apAging: () => request<APAgingReport>('/accounts-payable/aging'),
  exportApAgingCsv: (as_at?: string) => requestBlob(`/accounts-payable/aging/export.csv${qs({ as_at })}`),
  exportApAgingExcel: (as_at?: string) => requestBlob(`/accounts-payable/aging/export.xlsx${qs({ as_at })}`),

  listAccounts: (filters: { include_inactive?: boolean; account_type?: string } = {}) =>
    request<Account[]>(
      `/accounts${qs({
        include_inactive: filters.include_inactive ? 'true' : undefined,
        account_type: filters.account_type,
      })}`,
    ),
  exportAccountsCsv: (filters: { include_inactive?: boolean; account_type?: string } = {}) =>
    requestBlob(
      `/accounts/export.csv${qs({
        include_inactive: filters.include_inactive ? 'true' : undefined,
        account_type: filters.account_type,
      })}`,
    ),
  exportAccountsExcel: (filters: { include_inactive?: boolean; account_type?: string } = {}) =>
    requestBlob(
      `/accounts/export.xlsx${qs({
        include_inactive: filters.include_inactive ? 'true' : undefined,
        account_type: filters.account_type,
      })}`,
    ),
  createAccount: (payload: { code: string; name: string; account_type: AccountType }) =>
    request<Account>('/accounts', { method: 'POST', body: JSON.stringify(payload) }),
  updateAccount: (
    id: string,
    payload: { code?: string; name?: string; account_type?: AccountType; is_active?: boolean },
  ) => request<Account>(`/accounts/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

  arAging: () => request<AgingReport>('/accounts-receivable/aging'),
  exportArAgingCsv: (as_at?: string) => requestBlob(`/accounts-receivable/aging/export.csv${qs({ as_at })}`),
  exportArAgingExcel: (as_at?: string) => requestBlob(`/accounts-receivable/aging/export.xlsx${qs({ as_at })}`),
  customerStatement: (customerId: string) =>
    request<CustomerStatement>(`/accounts-receivable/statement/${customerId}`),
  writeOffInvoice: (invoiceId: string, reason: string) =>
    request<Invoice>(`/accounts-receivable/invoices/${invoiceId}/write-off`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  flagInvoiceDispute: (invoiceId: string, is_disputed: boolean, note?: string) =>
    request<Invoice>(`/accounts-receivable/invoices/${invoiceId}/dispute`, {
      method: 'POST',
      body: JSON.stringify({ is_disputed, note }),
    }),

  // Event Logs
  listEventLogs: (filters: EventLogFilters & { limit?: number; offset?: number } = {}) =>
    request<AuditLogEntry[]>(`/event-logs${qs(filters)}`),
  exportEventLogsCsv: (filters: EventLogFilters = {}) => requestBlob(`/event-logs/export.csv${qs(filters)}`),
  exportEventLogsExcel: (filters: EventLogFilters = {}) => requestBlob(`/event-logs/export.xlsx${qs(filters)}`),

  // Product / Service Catalog
  listCatalog: (includeInactive = false) =>
    request<Product[]>(`/catalog${includeInactive ? '?include_inactive=true' : ''}`),
  exportCatalogCsv: (includeInactive = false) =>
    requestBlob(`/catalog/export.csv${includeInactive ? '?include_inactive=true' : ''}`),
  exportCatalogExcel: (includeInactive = false) =>
    requestBlob(`/catalog/export.xlsx${includeInactive ? '?include_inactive=true' : ''}`),
  createCatalogItem: (payload: {
    product_type: ProductType
    name: string
    internal_reference?: string
    product_category?: string
    tags?: string
    sales_price_sgd: number
    cost_sgd?: number
    unit_of_measure?: string
    tax_code?: string
  }) => request<Product>('/catalog', { method: 'POST', body: JSON.stringify(payload) }),
  updateCatalogItem: (
    id: string,
    payload: Partial<{
      product_type: ProductType
      name: string
      internal_reference: string | null
      product_category: string | null
      tags: string | null
      sales_price_sgd: number
      cost_sgd: number | null
      unit_of_measure: string | null
      tax_code: string
      is_active: boolean
    }>,
  ) => request<Product>(`/catalog/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

  // Sales Quotation
  listQuotations: (filters: { customer_id?: string; status?: string } = {}) =>
    request<Quotation[]>(`/quotations${qs(filters)}`),
  exportQuotationsCsv: (filters: { customer_id?: string; status?: string } = {}) =>
    requestBlob(`/quotations/export.csv${qs(filters)}`),
  exportQuotationsExcel: (filters: { customer_id?: string; status?: string } = {}) =>
    requestBlob(`/quotations/export.xlsx${qs(filters)}`),
  getQuotation: (id: string) => request<Quotation>(`/quotations/${id}`),
  exportQuotationDocx: (id: string) => requestBlob(`/quotations/${id}/export.docx`),
  createQuotation: (payload: {
    customer_id: string
    quotation_date: string
    valid_until?: string
    notes?: string
    lines: {
      product_id?: string | null
      description: string
      unit_of_measure?: string
      quantity: number
      unit_price_sgd: number
    }[]
  }) => request<Quotation>('/quotations', { method: 'POST', body: JSON.stringify(payload) }),
  sendQuotation: (id: string) => request<Quotation>(`/quotations/${id}/send`, { method: 'POST' }),
  acceptQuotation: (id: string) =>
    request<{ quotation: Quotation; message: string }>(`/quotations/${id}/accept`, { method: 'POST' }),
  rejectQuotation: (id: string) => request<Quotation>(`/quotations/${id}/reject`, { method: 'POST' }),

  // ---- Operations Reports ----
  reportContracts: (filters: ContractReportFilters = {}) =>
    request<Contract[]>(`/reports/operations/contracts${qs(filters)}`),
  exportContractsReportCsv: (filters: ContractReportFilters = {}) =>
    requestBlob(`/reports/operations/contracts/export.csv${qs(filters)}`),
  exportContractsReportExcel: (filters: ContractReportFilters = {}) =>
    requestBlob(`/reports/operations/contracts/export.xlsx${qs(filters)}`),

  reportJobOrders: (filters: JobOrderReportFilters = {}) =>
    request<JobOrder[]>(`/reports/operations/job-orders${qs(filters)}`),
  exportJobOrdersReportCsv: (filters: JobOrderReportFilters = {}) =>
    requestBlob(`/reports/operations/job-orders/export.csv${qs(filters)}`),
  exportJobOrdersReportExcel: (filters: JobOrderReportFilters = {}) =>
    requestBlob(`/reports/operations/job-orders/export.xlsx${qs(filters)}`),

  reportServiceRecords: (filters: ServiceRecordReportFilters = {}) =>
    request<ServiceRecord[]>(`/reports/operations/service-records${qs(filters)}`),
  exportServiceRecordsReportCsv: (filters: ServiceRecordReportFilters = {}) =>
    requestBlob(`/reports/operations/service-records/export.csv${qs(filters)}`),
  exportServiceRecordsReportExcel: (filters: ServiceRecordReportFilters = {}) =>
    requestBlob(`/reports/operations/service-records/export.xlsx${qs(filters)}`),

  reportCustomerProductUsage: (filters: CustomerProductUsageFilters = {}) =>
    request<CustomerProductUsageRow[]>(`/reports/operations/customer-product-usage${qs(filters)}`),
  exportCustomerProductUsageCsv: (filters: CustomerProductUsageFilters = {}) =>
    requestBlob(`/reports/operations/customer-product-usage/export.csv${qs(filters)}`),
  exportCustomerProductUsageExcel: (filters: CustomerProductUsageFilters = {}) =>
    requestBlob(`/reports/operations/customer-product-usage/export.xlsx${qs(filters)}`),

  // ---- Accounting Reports ----
  reportArAging: (as_at?: string) => request<AgingReport>(`/reports/accounting/ar-aging${qs({ as_at })}`),
  exportArAgingReportCsv: (as_at?: string) => requestBlob(`/reports/accounting/ar-aging/export.csv${qs({ as_at })}`),
  exportArAgingReportExcel: (as_at?: string) =>
    requestBlob(`/reports/accounting/ar-aging/export.xlsx${qs({ as_at })}`),

  reportApAging: (as_at?: string) => request<APAgingReport>(`/reports/accounting/ap-aging${qs({ as_at })}`),
  exportApAgingReportCsv: (as_at?: string) => requestBlob(`/reports/accounting/ap-aging/export.csv${qs({ as_at })}`),
  exportApAgingReportExcel: (as_at?: string) =>
    requestBlob(`/reports/accounting/ap-aging/export.xlsx${qs({ as_at })}`),

  reportTrialBalance: (as_at?: string) =>
    request<TrialBalance>(`/reports/accounting/trial-balance${qs({ as_at })}`),
  exportTrialBalanceReportCsv: (as_at?: string) =>
    requestBlob(`/reports/accounting/trial-balance/export.csv${qs({ as_at })}`),
  exportTrialBalanceReportExcel: (as_at?: string) =>
    requestBlob(`/reports/accounting/trial-balance/export.xlsx${qs({ as_at })}`),

  reportGstReturn: (period_start: string, period_end: string) =>
    request<GSTReturn>(`/reports/accounting/gst-return${qs({ period_start, period_end })}`),
  exportGstReturnCsv: (period_start: string, period_end: string) =>
    requestBlob(`/reports/accounting/gst-return/export.csv${qs({ period_start, period_end })}`),
  exportGstReturnExcel: (period_start: string, period_end: string) =>
    requestBlob(`/reports/accounting/gst-return/export.xlsx${qs({ period_start, period_end })}`),

  // ---- GL Types ----
  listGLTypes: (includeInactive = false) =>
    request<GLType[]>(`/gl-types${includeInactive ? '?include_inactive=true' : ''}`),
  createGLType: (payload: { code: string; name: string; account_type: AccountType }) =>
    request<GLType>('/gl-types', { method: 'POST', body: JSON.stringify(payload) }),
  updateGLType: (id: string, payload: Partial<{ code: string; name: string; account_type: AccountType; is_active: boolean }>) =>
    request<GLType>(`/gl-types/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

  // ---- Setup Lists ----
  listSetupItems: (filters: { list_type?: SetupListType; include_inactive?: boolean } = {}) =>
    request<SetupListItem[]>(`/setup-lists${qs(filters)}`),
  createSetupItem: (payload: {
    list_type: SetupListType
    code: string
    name: string
    parent_code?: string | null
    sort_order?: number
  }) => request<SetupListItem>('/setup-lists', { method: 'POST', body: JSON.stringify(payload) }),
  updateSetupItem: (
    id: string,
    payload: Partial<{ code: string; name: string; parent_code: string | null; sort_order: number; is_active: boolean }>,
  ) => request<SetupListItem>(`/setup-lists/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  exportSetupItemsCsv: (filters: { list_type?: SetupListType; include_inactive?: boolean } = {}) =>
    requestBlob(`/setup-lists/export.csv${qs(filters)}`),
  exportSetupItemsExcel: (filters: { list_type?: SetupListType; include_inactive?: boolean } = {}) =>
    requestBlob(`/setup-lists/export.xlsx${qs(filters)}`),

  // ---- Currency Rate Table ----
  listCurrencyRates: (currency_code?: string) =>
    request<CurrencyRate[]>(`/currency-rates${qs({ currency_code })}`),
  createCurrencyRate: (payload: { currency_code: string; rate_to_base: number; effective_date: string }) =>
    request<CurrencyRate>('/currency-rates', { method: 'POST', body: JSON.stringify(payload) }),
  updateCurrencyRate: (id: string, payload: Partial<{ rate_to_base: number; is_active: boolean }>) =>
    request<CurrencyRate>(`/currency-rates/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

  // ---- Bank Master File ----
  listBankAccounts: (includeInactive = false) =>
    request<BankAccount[]>(`/bank-accounts${includeInactive ? '?include_inactive=true' : ''}`),
  createBankAccount: (payload: {
    bank_name: string
    account_name: string
    account_number: string
    branch?: string
    swift_code?: string
    currency_code?: string
    gl_account_id?: string | null
  }) => request<BankAccount>('/bank-accounts', { method: 'POST', body: JSON.stringify(payload) }),
  updateBankAccount: (
    id: string,
    payload: Partial<{
      bank_name: string
      account_name: string
      account_number: string
      branch: string | null
      swift_code: string | null
      currency_code: string
      gl_account_id: string | null
      is_active: boolean
    }>,
  ) => request<BankAccount>(`/bank-accounts/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  exportBankAccountsCsv: (includeInactive = false) =>
    requestBlob(`/bank-accounts/export.csv${includeInactive ? '?include_inactive=true' : ''}`),
  exportBankAccountsExcel: (includeInactive = false) =>
    requestBlob(`/bank-accounts/export.xlsx${includeInactive ? '?include_inactive=true' : ''}`),

  // ---- Tax Type (Tax Code maintenance) ----
  listTaxCodes: (includeInactive = false) =>
    request<TaxCode[]>(`/tax-codes${includeInactive ? '?include_inactive=true' : ''}`),
  createTaxCode: (payload: { code: string; name: string; rate_percent: number }) =>
    request<TaxCode>('/tax-codes', { method: 'POST', body: JSON.stringify(payload) }),
  updateTaxCode: (id: string, payload: Partial<{ code: string; name: string; rate_percent: number; is_active: boolean }>) =>
    request<TaxCode>(`/tax-codes/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  exportTaxCodesCsv: (includeInactive = false) =>
    requestBlob(`/tax-codes/export.csv${includeInactive ? '?include_inactive=true' : ''}`),
  exportTaxCodesExcel: (includeInactive = false) =>
    requestBlob(`/tax-codes/export.xlsx${includeInactive ? '?include_inactive=true' : ''}`),

  // ---- Document Control ----
  listDocumentSequences: () => request<DocumentSequence[]>('/document-control'),
  updateDocumentSequence: (id: string, payload: { last_number: number; reason: string }) =>
    request<DocumentSequence>(`/document-control/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  listDocumentNumberFormats: () => request<DocumentNumberFormat[]>('/document-control/formats'),
  updateDocumentNumberFormat: (
    docKind: string,
    payload: { prefix: string; number_length: number; include_year: boolean; reason: string },
  ) =>
    request<DocumentNumberFormat>(`/document-control/formats/${docKind}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  // ---- Accounting Periods / Year-End Closing ----
  listAccountingPeriods: (fiscal_year?: number) =>
    request<AccountingPeriod[]>(`/accounting-periods${qs({ fiscal_year })}`),
  createAccountingPeriod: (payload: { fiscal_year: number; name: string; period_start: string; period_end: string }) =>
    request<AccountingPeriod>('/accounting-periods', { method: 'POST', body: JSON.stringify(payload) }),
  closeAccountingPeriod: (id: string) =>
    request<AccountingPeriod>(`/accounting-periods/${id}/close`, { method: 'POST' }),
  reopenAccountingPeriod: (id: string) =>
    request<AccountingPeriod>(`/accounting-periods/${id}/reopen`, { method: 'POST' }),
  listFiscalYearClosures: () => request<FiscalYearClosure[]>('/accounting-periods/closures'),
  closeFiscalYear: (payload: { fiscal_year: number; retained_earnings_account_id: string }) =>
    request<FiscalYearClosure>('/accounting-periods/close-fiscal-year', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // ---- Ops Dashboard ----
  getOpsDashboard: (staffId?: string) => request<OpsDashboard>(`/ops-dashboard${qs({ staff_id: staffId })}`),
  createOpsTaskCategory: (payload: { name: string; cadence_label?: string; owner_user_id?: string }) =>
    request<OpsTaskCategory>('/ops-dashboard/categories', { method: 'POST', body: JSON.stringify(payload) }),
  createOpsTask: (payload: {
    category_id: string
    title: string
    status?: OpsTaskStatus
    next_action?: string
    owner_label?: string
    due_label?: string
    follow_up_staff_id?: string
    follow_up_date?: string
  }) => request<OpsTask>('/ops-dashboard/tasks', { method: 'POST', body: JSON.stringify(payload) }),
  updateOpsTask: (
    id: string,
    payload: Partial<{
      title: string
      status: OpsTaskStatus
      next_action: string
      owner_label: string
      due_label: string
      follow_up_staff_id: string
      follow_up_date: string
      clear_follow_up_staff: boolean
      clear_follow_up_date: boolean
    }>,
  ) => request<OpsTask>(`/ops-dashboard/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  archiveOpsTask: (id: string) => request<OpsTask>(`/ops-dashboard/tasks/${id}/archive`, { method: 'POST' }),
}

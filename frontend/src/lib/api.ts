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

function qs(params: Record<string, string | number | undefined>): string {
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
  exclude_auto_sent: boolean
  terms_and_conditions: string | null
  memo: string | null
  billing_notes: string | null
  payment_terms_days: number | null
}>

export type ContractStatus = 'draft' | 'active' | 'exceeded' | 'expired' | 'renewed'

export type ContractKind = 'service_support' | 'annual'

export interface Contract {
  id: string
  customer_id: string
  status: ContractStatus
  /** service_support: hours-based, 10-hr minimum. annual: term-only, no hours. */
  contract_kind: ContractKind
  contracted_hours: number
  consumed_hours: number
  remaining_hours: number
  contract_value_sgd: number
  start_date: string
  end_date: string
  renewed_from_contract_id: string | null
}

export type JobOrderPriority = 'low' | 'normal' | 'high' | 'critical'
export type JobOrderStatus = 'open' | 'assigned' | 'resolved' | 'closed'

export interface JobOrder {
  id: string
  customer_id: string
  contract_id: string | null
  subject: string
  priority: JobOrderPriority
  status: JobOrderStatus
  assigned_to_user_id: string | null
  /** Manual, optional -- set by Sales/Coordinator after discussion with Support. */
  due_date: string | null
  created_at: string
}

// ---- Support Monitoring ----
export interface StaffMonitoring {
  user_id: string
  full_name: string
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
export type ServiceRecordOutcome = 'pending' | 'contract_deduction' | 'excess_usage'

export interface ServiceRecord {
  id: string
  job_order_id: string
  employee_user_id: string
  work_date: string
  raw_minutes: number
  rounded_minutes: number
  status: ServiceRecordStatus
  outcome: ServiceRecordOutcome
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
    payload: { full_name?: string; role?: UserRole; group_id?: string | null },
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

  // Dynamic filter: free-text `q` matches name/email/phone/mobile/UEN/
  // legacy code/tags; customer_group_id pulls up a whole group of
  // companies together; includeInactive reveals deactivated customers.
  listCustomers: (filters: { q?: string; customer_group_id?: string; include_inactive?: boolean } = {}) =>
    request<Customer[]>(
      `/customers${qs({
        q: filters.q,
        customer_group_id: filters.customer_group_id,
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

  listContracts: (filters: { status?: string; customer_id?: string } = {}) =>
    request<Contract[]>(`/contracts${qs(filters)}`),
  getContract: (id: string) => request<Contract>(`/contracts/${id}`),
  createContract: (payload: {
    customer_id: string
    contract_kind?: ContractKind
    contracted_hours: number
    contract_value_sgd: number
    start_date: string
  }) => request<Contract>('/contracts', { method: 'POST', body: JSON.stringify(payload) }),
  activateContract: (id: string) => request<Contract>(`/contracts/${id}/activate`, { method: 'POST' }),
  renewContract: (
    id: string,
    payload: { contracted_hours: number; contract_value_sgd: number; force_start_date?: string },
  ) => request<Contract>(`/contracts/${id}/renew`, { method: 'POST', body: JSON.stringify(payload) }),
  listContractExcessUsage: (id: string) =>
    request<ExcessUsageRecord[]>(`/contracts/${id}/excess-usage`),

  listJobOrders: (
    filters: { status?: string; priority?: string; customer_id?: string; contract_id?: string } = {},
  ) => request<JobOrder[]>(`/job-orders${qs(filters)}`),
  getJobOrder: (id: string) => request<JobOrder>(`/job-orders/${id}`),
  createJobOrder: (payload: {
    customer_id: string
    contract_id: string
    subject: string
    priority?: JobOrderPriority
    due_date?: string | null
  }) => request<JobOrder>('/job-orders', { method: 'POST', body: JSON.stringify(payload) }),
  assignJobOrder: (id: string, assigned_to_user_id: string) =>
    request<JobOrder>(`/job-orders/${id}/assign`, { method: 'POST', body: JSON.stringify({ assigned_to_user_id }) }),
  setJobOrderDueDate: (id: string, due_date: string | null) =>
    request<JobOrder>(`/job-orders/${id}/due-date`, { method: 'POST', body: JSON.stringify({ due_date }) }),

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
  submitServiceRecord: (payload: {
    job_order_id: string
    employee_user_id: string
    work_date: string
    raw_minutes: number
  }) => request<ServiceRecord>('/service-records', { method: 'POST', body: JSON.stringify(payload) }),
  approveServiceRecord: (id: string) => request<ServiceRecord>(`/service-records/${id}/approve`, { method: 'POST' }),

  listExcessUsage: (pendingOnly = false) =>
    request<ExcessUsageRecord[]>(`/excess-usage${pendingOnly ? '?pending_only=true' : ''}`),
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
  allocatePayment: (id: string, allocations: { invoice_id: string; amount_sgd: number }[]) =>
    request<Payment>(`/accounts-receivable/payments/${id}/allocate`, {
      method: 'POST',
      body: JSON.stringify({ allocations }),
    }),
  // General Ledger
  listVouchers: (filters: { voucher_type?: string; status?: string } = {}) =>
    request<JournalEntry[]>(`/ledger/vouchers${qs(filters)}`),
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

  // Accounts Payable
  listSuppliers: (includeInactive = false) =>
    request<Supplier[]>(`/accounts-payable/suppliers${qs({ include_inactive: includeInactive ? 'true' : undefined })}`),
  createSupplier: (payload: {
    name: string
    email?: string
    address?: string
    gst_registration_no?: string
    payment_terms_days?: number | null
  }) => request<Supplier>('/accounts-payable/suppliers', { method: 'POST', body: JSON.stringify(payload) }),
  updateSupplier: (
    id: string,
    payload: Partial<{
      name: string
      email: string | null
      address: string | null
      gst_registration_no: string | null
      payment_terms_days: number | null
      is_active: boolean
    }>,
  ) => request<Supplier>(`/accounts-payable/suppliers/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

  listPurchaseOrders: (filters: { supplier_id?: string; status?: string } = {}) =>
    request<PurchaseOrder[]>(`/accounts-payable/purchase-orders${qs(filters)}`),
  createPurchaseOrder: (payload: {
    supplier_id: string
    order_date: string
    description: string
    amount_sgd: number
  }) => request<PurchaseOrder>('/accounts-payable/purchase-orders', { method: 'POST', body: JSON.stringify(payload) }),
  approvePurchaseOrder: (id: string) =>
    request<PurchaseOrder>(`/accounts-payable/purchase-orders/${id}/approve`, { method: 'POST' }),

  listBills: (filters: { supplier_id?: string; status?: string } = {}) =>
    request<SupplierInvoice[]>(`/accounts-payable/bills${qs(filters)}`),
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

  listAccounts: (filters: { include_inactive?: boolean; account_type?: string } = {}) =>
    request<Account[]>(
      `/accounts${qs({
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
  exportEventLogsCsv: async (filters: EventLogFilters = {}): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`/api/event-logs/export${qs(filters)}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        'X-Device-Id': getDeviceId(),
      },
    })
    if (!res.ok) throw new Error('Failed to export event logs')
    return res.blob()
  },

  // Product / Service Catalog
  listCatalog: (includeInactive = false) =>
    request<Product[]>(`/catalog${includeInactive ? '?include_inactive=true' : ''}`),
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
  getQuotation: (id: string) => request<Quotation>(`/quotations/${id}`),
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
}

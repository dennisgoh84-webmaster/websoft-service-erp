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

export interface Customer {
  id: string
  name: string
  billing_email: string | null
  billing_address: string | null
  /** Days from invoice date. Terms vary per customer; null = not agreed yet. */
  payment_terms_days: number | null
  is_active: boolean
}

export type ContractStatus = 'draft' | 'active' | 'exceeded' | 'expired' | 'renewed'

export interface Contract {
  id: string
  customer_id: string
  status: ContractStatus
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

  listCustomers: () => request<Customer[]>('/customers'),
  createCustomer: (payload: {
    name: string
    billing_email?: string
    billing_address?: string
    payment_terms_days?: number | null
  }) => request<Customer>('/customers', { method: 'POST', body: JSON.stringify(payload) }),
  updateCustomer: (
    id: string,
    payload: {
      name?: string
      billing_email?: string | null
      billing_address?: string | null
      payment_terms_days?: number | null
    },
  ) => request<Customer>(`/customers/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

  listContracts: (filters: { status?: string; customer_id?: string } = {}) =>
    request<Contract[]>(`/contracts${qs(filters)}`),
  getContract: (id: string) => request<Contract>(`/contracts/${id}`),
  createContract: (payload: {
    customer_id: string
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
  }) => request<JobOrder>('/job-orders', { method: 'POST', body: JSON.stringify(payload) }),
  assignJobOrder: (id: string, assigned_to_user_id: string) =>
    request<JobOrder>(`/job-orders/${id}/assign`, { method: 'POST', body: JSON.stringify({ assigned_to_user_id }) }),

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
}

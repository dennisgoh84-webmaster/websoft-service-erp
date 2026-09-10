// Thin API client for the Websoft Service ERP Solution backend.
// Talks to FastAPI via the Vite dev-server proxy (/api -> :8000).

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

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username: email, password })
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
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
}

export interface Customer {
  id: string
  name: string
  billing_email: string | null
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

export type TicketPriority = 'low' | 'normal' | 'high' | 'critical'
export type TicketStatus = 'open' | 'assigned' | 'resolved' | 'closed'

export interface Ticket {
  id: string
  customer_id: string
  contract_id: string | null
  subject: string
  priority: TicketPriority
  status: TicketStatus
  assigned_to_user_id: string | null
  created_at: string
}

export type TimesheetStatus = 'submitted' | 'approved'
export type TimesheetOutcome = 'pending' | 'contract_deduction' | 'excess_usage'

export interface TimesheetEntry {
  id: string
  ticket_id: string
  employee_user_id: string
  work_date: string
  raw_minutes: number
  rounded_minutes: number
  status: TimesheetStatus
  outcome: TimesheetOutcome
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
  timesheet_entry_id: string
  excess_hours: number
  treatment: ExcessTreatment | null
  reason: string | null
  decided_by_user_id: string | null
  invoiced: boolean
}

export interface Invoice {
  id: string
  customer_id: string
  contract_id: string | null
  invoice_type: string
  description: string
  amount_sgd: number
  issued_at: string
}

export const api = {
  me: () => request<CurrentUser>('/auth/me'),
  listUsers: () => request<CurrentUser[]>('/users'),

  listCustomers: () => request<Customer[]>('/customers'),
  createCustomer: (name: string, billing_email?: string) =>
    request<Customer>('/customers', { method: 'POST', body: JSON.stringify({ name, billing_email }) }),

  listContracts: () => request<Contract[]>('/contracts'),
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

  listTickets: () => request<Ticket[]>('/tickets'),
  getTicket: (id: string) => request<Ticket>(`/tickets/${id}`),
  createTicket: (payload: { customer_id: string; contract_id: string; subject: string; priority?: TicketPriority }) =>
    request<Ticket>('/tickets', { method: 'POST', body: JSON.stringify(payload) }),
  assignTicket: (id: string, assigned_to_user_id: string) =>
    request<Ticket>(`/tickets/${id}/assign`, { method: 'POST', body: JSON.stringify({ assigned_to_user_id }) }),

  listTimesheets: (ticket_id?: string) =>
    request<TimesheetEntry[]>(`/timesheets${ticket_id ? `?ticket_id=${ticket_id}` : ''}`),
  submitTimesheet: (payload: { ticket_id: string; employee_user_id: string; work_date: string; raw_minutes: number }) =>
    request<TimesheetEntry>('/timesheets', { method: 'POST', body: JSON.stringify(payload) }),
  approveTimesheet: (id: string) => request<TimesheetEntry>(`/timesheets/${id}/approve`, { method: 'POST' }),

  listExcessUsage: (pendingOnly = false) =>
    request<ExcessUsageRecord[]>(`/excess-usage${pendingOnly ? '?pending_only=true' : ''}`),
  decideExcessUsage: (id: string, treatment: ExcessTreatment, reason: string) =>
    request<ExcessUsageRecord>(`/excess-usage/${id}/decide`, {
      method: 'POST',
      body: JSON.stringify({ treatment, reason }),
    }),

  listInvoices: (contract_id?: string) =>
    request<Invoice[]>(`/invoices${contract_id ? `?contract_id=${contract_id}` : ''}`),
}

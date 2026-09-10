import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, type AuditLogEntry, type Contact, type Customer, type CustomerType } from '../lib/api'

const ACTION_LABELS: Record<string, string> = {
  created: 'Created',
  updated: 'Details updated',
  deactivated: 'Deactivated',
  reactivated: 'Reactivated',
}

function emptyForm() {
  return {
    customer_type: 'company' as CustomerType,
    name: '',
    legacy_customer_code: '',
    contact_person: '',
    uen: '',
    gst_registration_no: '',
    billing_email: '',
    phone: '',
    mobile: '',
    website: '',
    address_line1: '',
    address_line2: '',
    address_city: '',
    address_state: '',
    address_postal_code: '',
    address_country: '',
    tags: '',
    terms_and_conditions: '',
    payment_terms_days: '',
  }
}

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [customer, setCustomer] = useState<Customer | null>(null)
  const [contacts, setContacts] = useState<Contact[]>([])
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [saving, setSaving] = useState(false)

  const [form, setForm] = useState(emptyForm())
  const [excludeAutoSent, setExcludeAutoSent] = useState(false)

  // New-contact form
  const [contactName, setContactName] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [contactPhone, setContactPhone] = useState('')

  function refresh() {
    if (!id) return
    api
      .getCustomer(id)
      .then((c) => {
        setCustomer(c)
        setForm({
          customer_type: c.customer_type,
          name: c.name,
          legacy_customer_code: c.legacy_customer_code ?? '',
          contact_person: c.contact_person ?? '',
          uen: c.uen ?? '',
          gst_registration_no: c.gst_registration_no ?? '',
          billing_email: c.billing_email ?? '',
          phone: c.phone ?? '',
          mobile: c.mobile ?? '',
          website: c.website ?? '',
          address_line1: c.address_line1 ?? '',
          address_line2: c.address_line2 ?? '',
          address_city: c.address_city ?? '',
          address_state: c.address_state ?? '',
          address_postal_code: c.address_postal_code ?? '',
          address_country: c.address_country ?? '',
          tags: c.tags ?? '',
          terms_and_conditions: c.terms_and_conditions ?? '',
          payment_terms_days: c.payment_terms_days === null ? '' : String(c.payment_terms_days),
        })
        setExcludeAutoSent(c.exclude_auto_sent)
      })
      .catch(() => setNotFound(true))
    api.listContacts(id, true).then(setContacts).catch((e) => setError(e.message))
    api.getCustomerAuditLog(id).then(setAuditLog).catch((e) => setError(e.message))
  }

  useEffect(refresh, [id])

  async function onSave(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setError(null)
    setSaving(true)
    try {
      await api.updateCustomer(id, {
        customer_type: form.customer_type,
        name: form.name,
        legacy_customer_code: form.legacy_customer_code || null,
        contact_person: form.contact_person || null,
        uen: form.uen || null,
        gst_registration_no: form.gst_registration_no || null,
        billing_email: form.billing_email || null,
        phone: form.phone || null,
        mobile: form.mobile || null,
        website: form.website || null,
        address_line1: form.address_line1 || null,
        address_line2: form.address_line2 || null,
        address_city: form.address_city || null,
        address_state: form.address_state || null,
        address_postal_code: form.address_postal_code || null,
        address_country: form.address_country || null,
        tags: form.tags || null,
        exclude_auto_sent: excludeAutoSent,
        terms_and_conditions: form.terms_and_conditions || null,
        payment_terms_days: form.payment_terms_days === '' ? null : parseInt(form.payment_terms_days, 10),
      })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  async function onToggleActive() {
    if (!id || !customer) return
    setError(null)
    try {
      if (customer.is_active) await api.deactivateCustomer(id)
      else await api.reactivateCustomer(id)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update customer status')
    }
  }

  async function onAddContact(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setError(null)
    try {
      await api.createContact(id, {
        name: contactName,
        email: contactEmail || undefined,
        phone: contactPhone || undefined,
      })
      setContactName('')
      setContactEmail('')
      setContactPhone('')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add contact')
    }
  }

  async function onToggleContact(contact: Contact) {
    if (!id) return
    setError(null)
    try {
      if (contact.is_active) await api.deactivateContact(id, contact.id)
      else await api.reactivateContact(id, contact.id)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update contact')
    }
  }

  if (notFound) return <p>Customer not found. <Link to="/customers">Back to Customers</Link></p>
  if (!customer) return <p>Loading...</p>

  function field(key: keyof ReturnType<typeof emptyForm>) {
    return {
      value: form[key],
      onChange: (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
        setForm((prev) => ({ ...prev, [key]: e.target.value })),
    }
  }

  return (
    <div>
      <p>
        <Link to="/customers">&larr; Customers</Link>
      </p>
      <h1>{customer.name}</h1>
      <p>
        <span className={`badge ${customer.is_active ? 'active' : 'draft'}`}>
          {customer.is_active ? 'Active' : 'Inactive'}
        </span>{' '}
        <span className="muted">
          {customer.customer_type === 'individual' ? 'Individual' : 'Company'} &middot; added{' '}
          {new Date(customer.created_at).toLocaleDateString()}
          {customer.legacy_customer_code && <> &middot; Odoo ID {customer.legacy_customer_code}</>}
        </span>
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <h2>Profile</h2>
        <form onSubmit={onSave}>
          <div className="form-row">
            <label>Type</label>
            <select
              value={form.customer_type}
              onChange={(e) => setForm((p) => ({ ...p, customer_type: e.target.value as CustomerType }))}
            >
              <option value="company">Company</option>
              <option value="individual">Individual</option>
            </select>
          </div>
          <div className="form-row">
            <label>Name</label>
            <input {...field('name')} required />
          </div>
          <div className="form-row">
            <label>Contact person</label>
            <input {...field('contact_person')} placeholder="Quick reference, e.g. Mr Tan Wei Ming" />
          </div>
          <div className="form-row">
            <label>Odoo Customer ID</label>
            <input {...field('legacy_customer_code')} placeholder="Legacy code, for migration matching" />
          </div>
          <div className="form-row">
            <label>UEN</label>
            <input {...field('uen')} />
          </div>
          <div className="form-row">
            <label>GST registration no.</label>
            <input {...field('gst_registration_no')} />
          </div>
          <div className="form-row">
            <label>Email</label>
            <input {...field('billing_email')} type="email" />
          </div>
          <div className="form-row">
            <label>Phone</label>
            <input {...field('phone')} />
          </div>
          <div className="form-row">
            <label>Mobile</label>
            <input {...field('mobile')} />
          </div>
          <div className="form-row">
            <label>Website</label>
            <input {...field('website')} />
          </div>
          <div className="form-row">
            <label>Address line 1</label>
            <input {...field('address_line1')} />
          </div>
          <div className="form-row">
            <label>Address line 2</label>
            <input {...field('address_line2')} />
          </div>
          <div className="form-row">
            <label>City</label>
            <input {...field('address_city')} />
          </div>
          <div className="form-row">
            <label>State</label>
            <input {...field('address_state')} />
          </div>
          <div className="form-row">
            <label>Postal code</label>
            <input {...field('address_postal_code')} />
          </div>
          <div className="form-row">
            <label>Country</label>
            <input {...field('address_country')} placeholder="e.g. Singapore" />
          </div>
          <div className="form-row">
            <label>Tags</label>
            <input {...field('tags')} placeholder="e.g. B2B, VIP" />
          </div>
          <div className="form-row">
            <label>Payment terms (days from invoice date)</label>
            <input
              type="number"
              min={0}
              value={form.payment_terms_days}
              onChange={(e) => setForm((p) => ({ ...p, payment_terms_days: e.target.value }))}
              placeholder="Leave blank if not yet agreed"
            />
          </div>
          <div className="form-row">
            <label>Terms &amp; conditions (shown on orders)</label>
            <textarea {...field('terms_and_conditions')} rows={3} />
          </div>
          <div className="form-row">
            <label>
              <input
                type="checkbox"
                checked={excludeAutoSent}
                onChange={(e) => setExcludeAutoSent(e.target.checked)}
                style={{ width: 'auto', marginRight: 8 }}
              />
              Exclude from automated sending
            </label>
          </div>
          <p className="muted">
            Reserved for later -- there is no automated invoice/reminder emailing built yet, so this
            checkbox has no effect today.
          </p>
          <button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save changes'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Contact people</h2>
        <p className="muted">Individual contacts at this customer -- separate from the quick "Contact person" field above.</p>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {contacts.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.email ?? '-'}</td>
                <td>{c.phone ?? '-'}</td>
                <td>
                  <span className={`badge ${c.is_active ? 'active' : 'draft'}`}>
                    {c.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>
                  <button className="secondary" onClick={() => onToggleContact(c)}>
                    {c.is_active ? 'Deactivate' : 'Reactivate'}
                  </button>
                </td>
              </tr>
            ))}
            {contacts.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No contact people recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>

        <form onSubmit={onAddContact} style={{ marginTop: 14 }}>
          <div className="form-row">
            <label>Name</label>
            <input value={contactName} onChange={(e) => setContactName(e.target.value)} required />
          </div>
          <div className="form-row">
            <label>Email (optional)</label>
            <input value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} type="email" />
          </div>
          <div className="form-row">
            <label>Phone (optional)</label>
            <input value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} />
          </div>
          <button type="submit">Add contact person</button>
        </form>
      </div>

      <div className="card">
        <h2>Customer status</h2>
        <p className="muted">
          Deactivating a customer keeps their history intact -- contracts, job orders and invoices stay
          exactly as they are (per CLAUDE.md: never permanently delete business records).
        </p>
        <button className="secondary" onClick={onToggleActive}>
          {customer.is_active ? 'Deactivate customer' : 'Reactivate customer'}
        </button>
      </div>

      <div className="card">
        <h2>Recent activity</h2>
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Action</th>
              <th>By</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {auditLog.map((entry) => (
              <tr key={entry.id}>
                <td>{new Date(entry.at).toLocaleString()}</td>
                <td>{ACTION_LABELS[entry.action] ?? entry.action}</td>
                <td>{entry.actor_name ?? 'System'}</td>
                <td className="muted">{entry.details ?? entry.reason ?? '-'}</td>
              </tr>
            ))}
            {auditLog.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  No activity recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <button className="secondary" onClick={() => navigate('/customers')}>
        Back to Customers
      </button>
    </div>
  )
}

import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/AuthContext'
import { changePassword, verifyOtp } from '../lib/api'
import type { LoginResult } from '../lib/api'

// Promotions panel (2026-09-12: "empty place to publish promotions --
// add-on features, new updates, latest news"). Sample content for now,
// hardcoded here -- ask if this should instead be editable from Company
// Setup (or its own small admin screen) once the look is confirmed.
const PROMO_ITEMS = [
  {
    tag: 'New',
    text: 'Reference Monitor: break one Chart of Accounts code into named sub-codes for Sales Quotation lines.',
  },
  {
    tag: 'Add-on',
    text: 'Print/Email/WhatsApp actions are now icon buttons across every document list.',
  },
  {
    tag: 'Update',
    text: 'Company/Individual replaces the old "Customer" naming throughout the app.',
  },
]

// Login sequence (2026-09-12: password complexity, forced first-login
// password change, email OTP second factor -- see backend
// app/routers/auth.py's module docstring for the full sequence this
// page walks through step by step).
type Step = 'credentials' | 'otp' | 'change_password'

export default function Login() {
  const { login, completeLogin } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('credentials')

  const [email, setEmail] = useState('dennis@websoft.local')
  const [password, setPassword] = useState('demo1234')

  const [otpToken, setOtpToken] = useState('')
  const [otpCode, setOtpCode] = useState('')

  const [changeToken, setChangeToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  /** Common tail of every step: "ok" signs the user in, otherwise move
   * to whichever step the backend says is next. */
  async function advance(result: LoginResult) {
    if (result.status === 'ok' && result.access_token) {
      await completeLogin(result.access_token)
      navigate('/')
    } else if (result.status === 'otp_required' && result.otp_token) {
      setOtpToken(result.otp_token)
      setOtpCode('')
      setStep('otp')
    } else if (result.status === 'must_change_password' && result.change_token) {
      setChangeToken(result.change_token)
      setNewPassword('')
      setConfirmPassword('')
      setStep('change_password')
    }
  }

  async function onSubmitCredentials(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await advance(await login(email, password))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setSubmitting(false)
    }
  }

  async function onSubmitOtp(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await advance(await verifyOtp(otpToken, otpCode))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Incorrect code')
    } finally {
      setSubmitting(false)
    }
  }

  async function onSubmitChangePassword(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await advance(await changePassword(changeToken, newPassword))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not change password')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-shell">
      <div className="login-layout">
        <div className="card login-card">
          <h1>Websoft Service ERP</h1>
          <p className="muted" style={{ marginBottom: 18 }}>
            Service Operations core -- demo build
          </p>

          {step === 'credentials' && (
            <form onSubmit={onSubmitCredentials}>
              <div className="form-row">
                <label>Email</label>
                <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
              </div>
              <div className="form-row">
                <label>Password</label>
                <input
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  type="password"
                  required
                />
              </div>
              {error && <div className="error-banner">{error}</div>}
              <button type="submit" disabled={submitting} style={{ width: '100%' }}>
                {submitting ? 'Signing in...' : 'Sign in'}
              </button>
            </form>
          )}

          {step === 'otp' && (
            <form onSubmit={onSubmitOtp}>
              <p className="muted" style={{ marginBottom: 18 }}>
                We emailed a 6-digit code to {email}. Enter it below to finish signing in.
              </p>
              <div className="form-row">
                <label>One-time code</label>
                <input
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  autoFocus
                  required
                />
              </div>
              {error && <div className="error-banner">{error}</div>}
              <button type="submit" disabled={submitting || otpCode.length !== 6} style={{ width: '100%' }}>
                {submitting ? 'Verifying...' : 'Verify code'}
              </button>
            </form>
          )}

          {step === 'change_password' && (
            <form onSubmit={onSubmitChangePassword}>
              <p className="muted" style={{ marginBottom: 18 }}>
                This is your first sign-in -- please set your own password to continue. At
                least 8 characters, with at least one letter and one number.
              </p>
              <div className="form-row">
                <label>New password</label>
                <input
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  type="password"
                  minLength={8}
                  autoFocus
                  required
                />
              </div>
              <div className="form-row">
                <label>Confirm password</label>
                <input
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  type="password"
                  minLength={8}
                  required
                />
              </div>
              {error && <div className="error-banner">{error}</div>}
              <button type="submit" disabled={submitting} style={{ width: '100%' }}>
                {submitting ? 'Saving...' : 'Set password and sign in'}
              </button>
            </form>
          )}
        </div>

        <div className="login-promo">
          <h2>What's New</h2>
          {PROMO_ITEMS.map((item, i) => (
            <div className="login-promo-item" key={i}>
              <span className="tag">{item.tag}</span>
              <p>{item.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

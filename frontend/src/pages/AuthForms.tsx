import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const MIN_PASSWORD_LENGTH = 8

function formValues(e: FormEvent<HTMLFormElement>) {
  return Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>
}

function ErrorMessage({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <p className="notice error" role="alert">
      {message}
    </p>
  )
}

export function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const { email, password } = formValues(e)
    setError(null)
    setBusy(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="container section auth">
      <form className="auth-card" onSubmit={onSubmit} noValidate>
        <h1>Log in</h1>
        <p className="muted">Welcome back, Bulldog.</p>
        <ErrorMessage message={error} />
        <label>
          Email
          <input type="email" name="email" autoComplete="email" required />
        </label>
        <label>
          Password
          <input type="password" name="password" autoComplete="current-password" required />
        </label>
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? 'Logging in…' : 'Log in'}
        </button>
        <p className="muted">
          New here? <Link to="/signup">Create an account</Link>
        </p>
      </form>
    </section>
  )
}

export function Signup() {
  const { user, signup } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const v = formValues(e)

    // Quick checks here for instant feedback; the backend repeats all of them.
    if (!v.first_name.trim() || !v.last_name.trim() || !v.email.trim()) {
      return setError('Please fill in your name and email.')
    }
    if (v.password.length < MIN_PASSWORD_LENGTH) {
      return setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
    }
    if (v.password !== v.confirm_password) {
      return setError("Passwords don't match.")
    }

    setError(null)
    setBusy(true)
    try {
      await signup({
        first_name: v.first_name,
        last_name: v.last_name,
        email: v.email,
        password: v.password,
        confirm_password: v.confirm_password,
      })
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="container section auth">
      <form className="auth-card" onSubmit={onSubmit} noValidate>
        <h1>Create account</h1>
        <p className="muted">Save your chats and pick up where you left off.</p>
        <ErrorMessage message={error} />
        <div className="row">
          <label>
            First name
            <input name="first_name" autoComplete="given-name" required />
          </label>
          <label>
            Last name
            <input name="last_name" autoComplete="family-name" required />
          </label>
        </div>
        <label>
          Email
          <input type="email" name="email" autoComplete="email" required />
        </label>
        <label>
          Password
          <input type="password" name="password" autoComplete="new-password" required />
          <small className="muted">At least {MIN_PASSWORD_LENGTH} characters.</small>
        </label>
        <label>
          Confirm password
          <input type="password" name="confirm_password" autoComplete="new-password" required />
        </label>
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
        <p className="muted">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </section>
  )
}

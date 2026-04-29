import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Cadastro() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm]   = useState({ email: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handle = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  async function submit(e) {
    e.preventDefault()
    setError('')

    if (form.password.length < 6)
      return setError('A senha deve ter pelo menos 6 caracteres.')
    if (form.password !== form.confirm)
      return setError('As senhas não coincidem.')

    setLoading(true)
    try {
      await register(form.email, form.password)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao criar conta.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <span className="auth-icon">🍽️</span>
          <h1 className="auth-title">RestaurantePro</h1>
          <p className="auth-subtitle">Crie sua conta gratuita</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={submit}>
          <div className="form-group">
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              name="email"
              type="email"
              value={form.email}
              onChange={handle}
              placeholder="seu@email.com"
              autoFocus
              required
            />
          </div>

          <div className="form-group" style={{ marginTop: '.85rem' }}>
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              name="password"
              type="password"
              value={form.password}
              onChange={handle}
              placeholder="Mínimo 6 caracteres"
              required
            />
          </div>

          <div className="form-group" style={{ marginTop: '.85rem' }}>
            <label htmlFor="confirm">Confirmar senha</label>
            <input
              id="confirm"
              name="confirm"
              type="password"
              value={form.confirm}
              onChange={handle}
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary auth-btn"
            disabled={loading}
          >
            {loading ? 'Criando conta...' : 'Criar conta'}
          </button>
        </form>

        <p className="auth-switch">
          Já tem conta?{' '}
          <Link to="/login">Fazer login</Link>
        </p>
      </div>
    </div>
  )
}

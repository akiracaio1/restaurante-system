import { useState, useEffect } from 'react'
import { usuariosAPI } from '../api'
import { useAuth } from '../context/AuthContext'

const ROLE_LABEL = { master: 'Master', operacao: 'Operação' }

export default function UsuariosLista() {
  const { email: myEmail } = useAuth()
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState('')
  const [saving, setSaving]   = useState(false)
  const [form, setForm]       = useState({ email: '', password: '', role: 'operacao' })

  async function load() {
    try {
      setLoading(true)
      const { data } = await usuariosAPI.listar()
      setItems(data)
    } catch {
      setError('Erro ao carregar usuários.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function flash(setter, msg) {
    setter(msg)
    setTimeout(() => setter(''), 4000)
  }

  const handle = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  async function create(e) {
    e.preventDefault()
    setError('')
    if (!form.email.trim()) return setError('Informe o e-mail.')
    if (form.password.length < 6) return setError('A senha deve ter pelo menos 6 caracteres.')
    try {
      setSaving(true)
      await usuariosAPI.criar({ email: form.email.trim(), password: form.password, role: form.role })
      setForm({ email: '', password: '', role: 'operacao' })
      flash(setSuccess, 'Usuário criado.')
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao criar usuário.')
    } finally {
      setSaving(false)
    }
  }

  async function update(user, patch, okMsg) {
    setError('')
    try {
      await usuariosAPI.atualizar(user.id, patch)
      flash(setSuccess, okMsg)
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao atualizar usuário.')
    }
  }

  function changeRole(user, role) {
    if (role === user.role) return
    const label = ROLE_LABEL[role]
    if (!window.confirm(`Alterar o perfil de ${user.email} para ${label}?`)) return
    update(user, { role }, `Perfil de ${user.email} alterado para ${label}.`)
  }

  function toggleActive(user) {
    const verb = user.is_active ? 'Desativar' : 'Reativar'
    if (!window.confirm(`${verb} ${user.email}?`)) return
    update(user, { is_active: !user.is_active }, `${user.email} ${user.is_active ? 'desativado' : 'reativado'}.`)
  }

  function resetPassword(user) {
    const pwd = window.prompt(`Nova senha para ${user.email} (mínimo 6 caracteres):`)
    if (pwd == null) return
    if (pwd.length < 6) return setError('A senha deve ter pelo menos 6 caracteres.')
    update(user, { password: pwd }, `Senha de ${user.email} redefinida.`)
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">👥 Usuários</h1>
          <p className="page-subtitle">
            Master tem acesso completo. Operação consulta receitas e usa a calculadora, sem ver valores financeiros.
          </p>
        </div>
      </div>

      {error   && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="form-card" style={{ maxWidth: '860px', marginBottom: '1.5rem' }}>
        <p className="section-title">Novo usuário</p>
        <form onSubmit={create}>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="email">E-mail *</label>
              <input id="email" name="email" type="email" value={form.email} onChange={handle} placeholder="funcionaria@email.com" />
            </div>
            <div className="form-group">
              <label htmlFor="password">Senha inicial *</label>
              <input id="password" name="password" type="text" value={form.password} onChange={handle} placeholder="mínimo 6 caracteres" autoComplete="off" />
            </div>
            <div className="form-group">
              <label htmlFor="role">Perfil *</label>
              <select id="role" name="role" value={form.role} onChange={handle}>
                <option value="operacao">Operação (sem valores financeiros)</option>
                <option value="master">Master (acesso completo)</option>
              </select>
            </div>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? '⏳ Salvando…' : '+ Criar usuário'}
            </button>
          </div>
        </form>
      </div>

      {loading ? (
        <div className="loading">Carregando usuários…</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'auto' }}>
          <table className="ing-table" style={{ margin: 0 }}>
            <thead>
              <tr>
                <th>E-mail</th>
                <th>Perfil</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map(u => {
                const isMe = u.email === myEmail
                return (
                  <tr key={u.id} style={u.is_active ? undefined : { opacity: .55 }}>
                    <td style={{ fontWeight: 600 }}>{u.email}{isMe ? ' (você)' : ''}</td>
                    <td>
                      <select
                        value={u.role}
                        disabled={isMe}
                        onChange={e => changeRole(u, e.target.value)}
                      >
                        <option value="master">Master</option>
                        <option value="operacao">Operação</option>
                      </select>
                    </td>
                    <td>{u.is_active ? 'Ativo' : 'Desativado'}</td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <button type="button" className="btn btn-sm btn-outline" onClick={() => resetPassword(u)}>
                        Redefinir senha
                      </button>{' '}
                      {!isMe && (
                        <button type="button" className="btn btn-sm btn-danger" onClick={() => toggleActive(u)}>
                          {u.is_active ? 'Desativar' : 'Reativar'}
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

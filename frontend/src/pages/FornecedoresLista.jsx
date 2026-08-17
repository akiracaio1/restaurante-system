import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { fornecedoresAPI } from '../api'

const EMPTY = { name: '', cnpj: '', phone: '', email: '', contact_name: '', address: '', notes: '' }
const fmt = (v) => `R$ ${Number(v).toFixed(2).replace('.', ',')}`

export default function FornecedoresLista() {
  const [items, setItems]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [success, setSuccess]   = useState('')
  const [form, setForm]         = useState(EMPTY)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving]     = useState(false)
  const [expanded, setExpanded] = useState(false)

  async function load() {
    try {
      setLoading(true)
      const { data } = await fornecedoresAPI.listar()
      setItems(data)
    } catch {
      setError('Erro ao carregar fornecedores.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handle = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  function startEdit(supplier) {
    setEditingId(supplier.id)
    setForm({
      name: supplier.name,
      cnpj: supplier.cnpj || '',
      phone: supplier.phone || '',
      email: supplier.email || '',
      contact_name: supplier.contact_name || '',
      address: supplier.address || '',
      notes: supplier.notes || '',
    })
    setExpanded(true)
  }

  function cancelEdit() {
    setEditingId(null)
    setForm(EMPTY)
    setExpanded(false)
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!form.name.trim()) return setError('Nome do fornecedor é obrigatório.')

    const payload = {
      name: form.name.trim(),
      cnpj: form.cnpj.trim() || null,
      phone: form.phone.trim() || null,
      email: form.email.trim() || null,
      contact_name: form.contact_name.trim() || null,
      address: form.address.trim() || null,
      notes: form.notes.trim() || null,
    }

    try {
      setSaving(true)
      if (editingId) {
        const { data } = await fornecedoresAPI.atualizar(editingId, payload)
        setItems(prev => prev.map(s => s.id === editingId ? { ...s, ...data } : s).sort((a, b) => a.name.localeCompare(b.name)))
        setSuccess(`"${data.name}" atualizado com sucesso.`)
      } else {
        const { data } = await fornecedoresAPI.criar(payload)
        setItems(prev => [...prev, { ...data, purchase_count: 0, total_spent: 0 }].sort((a, b) => a.name.localeCompare(b.name)))
        setSuccess(`"${data.name}" cadastrado com sucesso.`)
      }
      setTimeout(() => setSuccess(''), 3500)
      cancelEdit()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar fornecedor.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id, name) {
    if (!window.confirm(`Excluir "${name}"? As compras já registradas com esse fornecedor não serão apagadas.`)) return
    try {
      await fornecedoresAPI.excluir(id)
      setItems(prev => prev.filter(s => s.id !== id))
      setSuccess(`"${name}" excluído com sucesso.`)
      setTimeout(() => setSuccess(''), 3500)
      if (editingId === id) cancelEdit()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao excluir fornecedor.')
      setTimeout(() => setError(''), 4000)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🚚 Fornecedores</h1>
          <p className="page-subtitle">
            {items.length === 1 ? '1 fornecedor cadastrado' : `${items.length} fornecedores cadastrados`}
          </p>
        </div>
        <Link to="/compras" className="btn btn-outline">🛒 Compras</Link>
      </div>

      {error   && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="form-card" style={{ maxWidth: '720px', marginBottom: '1.5rem' }}>
        {!expanded && !editingId ? (
          <button type="button" className="btn btn-primary" onClick={() => setExpanded(true)}>
            + Novo Fornecedor
          </button>
        ) : (
          <>
            <p className="section-title" style={{ marginTop: 0 }}>
              {editingId ? 'Editar Fornecedor' : 'Novo Fornecedor'}
            </p>
            <form onSubmit={submit}>
              <div className="form-grid">
                <div className="form-group full">
                  <label htmlFor="name">Nome *</label>
                  <input
                    id="name" name="name" value={form.name} onChange={handle}
                    placeholder="Ex: Distribuidora Central"
                    className={form.name.trim() ? 'valid' : ''}
                    autoFocus
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="cnpj">CNPJ</label>
                  <input id="cnpj" name="cnpj" value={form.cnpj} onChange={handle} placeholder="00.000.000/0000-00" />
                </div>
                <div className="form-group">
                  <label htmlFor="phone">Telefone</label>
                  <input id="phone" name="phone" value={form.phone} onChange={handle} placeholder="(00) 00000-0000" />
                </div>
                <div className="form-group">
                  <label htmlFor="email">E-mail</label>
                  <input id="email" name="email" type="email" value={form.email} onChange={handle} placeholder="contato@fornecedor.com" />
                </div>
                <div className="form-group">
                  <label htmlFor="contact_name">Pessoa de Contato</label>
                  <input id="contact_name" name="contact_name" value={form.contact_name} onChange={handle} placeholder="Nome do vendedor/contato" />
                </div>
                <div className="form-group full">
                  <label htmlFor="address">Endereço</label>
                  <input id="address" name="address" value={form.address} onChange={handle} placeholder="Endereço opcional" />
                </div>
                <div className="form-group full">
                  <label htmlFor="notes">Observações</label>
                  <textarea id="notes" name="notes" value={form.notes} onChange={handle} rows={2} placeholder="Observações opcionais…" />
                </div>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? '⏳ Salvando…' : editingId ? '✓ Salvar Alterações' : '+ Adicionar Fornecedor'}
                </button>
                <button type="button" className="btn btn-ghost" onClick={cancelEdit}>Cancelar</button>
              </div>
            </form>
          </>
        )}
      </div>

      {loading ? (
        <div className="loading">Carregando fornecedores…</div>
      ) : items.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">🚚</span>
            <p className="empty-text">Nenhum fornecedor cadastrado</p>
            <p className="empty-sub">Cadastre acima seus fornecedores para vincular às compras e ver o histórico por fornecedor.</p>
          </div>
        </div>
      ) : (
        <div className="cards-grid">
          {items.map(s => (
            <div key={s.id} className="ing-card">
              <div className="ing-card-header">
                <span className="ing-card-name">{s.name}</span>
                {s.cnpj && <span className="badge badge-unit">{s.cnpj}</span>}
              </div>
              <div className="ing-card-body">
                <div className="ing-card-row">
                  <span className="ing-card-label">Compras registradas</span>
                  <span className="ing-card-value">{s.purchase_count}</span>
                </div>
                <div className="ing-card-row">
                  <span className="ing-card-label">Total gasto</span>
                  <span className="ing-card-value highlight">{fmt(s.total_spent)}</span>
                </div>
                {s.phone && (
                  <div className="ing-card-row">
                    <span className="ing-card-label">Telefone</span>
                    <span className="ing-card-value">{s.phone}</span>
                  </div>
                )}
                {s.contact_name && (
                  <div className="ing-card-row">
                    <span className="ing-card-label">Contato</span>
                    <span className="ing-card-value">{s.contact_name}</span>
                  </div>
                )}
              </div>
              <div className="ing-card-actions">
                <Link to={`/fornecedores/${s.id}`} className="btn btn-sm btn-outline">
                  📋 Ver Compras
                </Link>
                <button className="btn btn-sm btn-outline" onClick={() => startEdit(s)}>
                  Editar
                </button>
                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(s.id, s.name)}>
                  Excluir
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { canaisAPI } from '../api'

const EMPTY = { name: '', fee_percent: '', fixed_cost: '' }
const fmt = (v) => `R$ ${Number(v).toFixed(2).replace('.', ',')}`

export default function CanaisLista() {
  const [items, setItems]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [success, setSuccess]   = useState('')
  const [form, setForm]         = useState(EMPTY)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving]     = useState(false)

  async function load() {
    try {
      setLoading(true)
      const { data } = await canaisAPI.listar()
      setItems(data)
    } catch {
      setError('Erro ao carregar canais de venda.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handle = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  function startEdit(channel) {
    setEditingId(channel.id)
    setForm({
      name: channel.name,
      fee_percent: channel.fee_percent != null ? String(channel.fee_percent) : '',
      fixed_cost: channel.fixed_cost != null ? String(channel.fixed_cost) : '',
    })
  }

  function cancelEdit() {
    setEditingId(null)
    setForm(EMPTY)
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!form.name.trim()) return setError('Nome do canal é obrigatório.')

    const payload = {
      name: form.name.trim(),
      fee_percent: form.fee_percent === '' ? null : Number(form.fee_percent),
      fixed_cost: form.fixed_cost === '' ? null : Number(form.fixed_cost),
    }

    try {
      setSaving(true)
      if (editingId) {
        const { data } = await canaisAPI.atualizar(editingId, payload)
        setItems(prev => prev.map(c => c.id === editingId ? data : c))
        setSuccess(`"${data.name}" atualizado com sucesso.`)
      } else {
        const { data } = await canaisAPI.criar(payload)
        setItems(prev => [...prev, data].sort((a, b) => a.name.localeCompare(b.name)))
        setSuccess(`"${data.name}" cadastrado com sucesso.`)
      }
      setTimeout(() => setSuccess(''), 3500)
      cancelEdit()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar canal de venda.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id, name) {
    if (!window.confirm(`Excluir "${name}"? Isso também remove os preços dessa modalidade em todas as receitas.`)) return
    try {
      await canaisAPI.excluir(id)
      setItems(prev => prev.filter(c => c.id !== id))
      setSuccess(`"${name}" excluído com sucesso.`)
      setTimeout(() => setSuccess(''), 3500)
      if (editingId === id) cancelEdit()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao excluir canal de venda.')
      setTimeout(() => setError(''), 4000)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">⚙️ Canais de Venda</h1>
          <p className="page-subtitle">
            {items.length === 1 ? '1 canal cadastrado' : `${items.length} canais cadastrados`}
          </p>
        </div>
        <Link to="/receitas" className="btn btn-outline">🍳 Receitas</Link>
      </div>

      {error   && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="form-card" style={{ maxWidth: '720px', marginBottom: '1.5rem' }}>
        <p className="section-title" style={{ marginTop: 0 }}>
          {editingId ? 'Editar Canal de Venda' : 'Novo Canal de Venda'}
        </p>
        <form onSubmit={submit}>
          <div className="form-grid">
            <div className="form-group full">
              <label htmlFor="name">Nome *</label>
              <input
                id="name" name="name" value={form.name} onChange={handle}
                placeholder="Ex: iFood com motoboy próprio"
                className={form.name.trim() ? 'valid' : ''}
              />
            </div>
            <div className="form-group">
              <label htmlFor="fee_percent">Taxa da plataforma (%)</label>
              <input
                id="fee_percent" name="fee_percent" type="number" step="0.01" min="0"
                value={form.fee_percent} onChange={handle} placeholder="Ex: 27"
              />
            </div>
            <div className="form-group">
              <label htmlFor="fixed_cost">Custo fixo por venda (R$)</label>
              <input
                id="fixed_cost" name="fixed_cost" type="number" step="0.01" min="0"
                value={form.fixed_cost} onChange={handle} placeholder="Ex: motoboy — 8,00"
              />
            </div>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? '⏳ Salvando…' : editingId ? '✓ Salvar Alterações' : '+ Adicionar Canal'}
            </button>
            {editingId && (
              <button type="button" className="btn btn-ghost" onClick={cancelEdit}>Cancelar</button>
            )}
          </div>
        </form>
      </div>

      {loading ? (
        <div className="loading">Carregando canais…</div>
      ) : items.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">⚙️</span>
            <p className="empty-text">Nenhum canal de venda cadastrado</p>
            <p className="empty-sub">Cadastre acima os canais que você usa (iFood, 99Food, Cardápio Digital, Revenda...).</p>
          </div>
        </div>
      ) : (
        <table className="ing-table">
          <thead>
            <tr>
              <th>Canal</th>
              <th>Taxa da plataforma</th>
              <th>Custo fixo</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map(c => (
              <tr key={c.id}>
                <td style={{ fontWeight: 600 }}>{c.name}</td>
                <td>{c.fee_percent != null ? `${c.fee_percent}%` : '—'}</td>
                <td>{c.fixed_cost != null ? fmt(c.fixed_cost) : '—'}</td>
                <td style={{ display: 'flex', gap: '.4rem' }}>
                  <button type="button" className="btn btn-sm btn-outline" onClick={() => startEdit(c)}>
                    Editar
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-danger"
                    onClick={() => handleDelete(c.id, c.name)}
                  >
                    Excluir
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

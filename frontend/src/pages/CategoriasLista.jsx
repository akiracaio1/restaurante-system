import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { categoriasAPI } from '../api'

export default function CategoriasLista() {
  const [items, setItems]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [success, setSuccess]   = useState('')
  const [name, setName]         = useState('')
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving]     = useState(false)

  async function load() {
    try {
      setLoading(true)
      const { data } = await categoriasAPI.listar()
      setItems(data)
    } catch {
      setError('Erro ao carregar categorias.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function startEdit(cat) {
    setEditingId(cat.id)
    setName(cat.name)
  }

  function cancelEdit() {
    setEditingId(null)
    setName('')
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!name.trim()) return setError('Nome da categoria é obrigatório.')

    try {
      setSaving(true)
      if (editingId) {
        const { data } = await categoriasAPI.atualizar(editingId, { name: name.trim() })
        setItems(prev => prev.map(c => c.id === editingId ? data : c).sort((a, b) => a.name.localeCompare(b.name)))
        setSuccess(`"${data.name}" atualizada com sucesso. Receitas com a categoria antiga foram atualizadas.`)
      } else {
        const { data } = await categoriasAPI.criar({ name: name.trim() })
        setItems(prev => [...prev, data].sort((a, b) => a.name.localeCompare(b.name)))
        setSuccess(`"${data.name}" criada com sucesso.`)
      }
      setTimeout(() => setSuccess(''), 4000)
      cancelEdit()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar categoria.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id, catName) {
    if (!window.confirm(`Excluir "${catName}"? As receitas que já usam essa categoria não serão alteradas.`)) return
    try {
      await categoriasAPI.excluir(id)
      setItems(prev => prev.filter(c => c.id !== id))
      setSuccess(`"${catName}" excluída com sucesso.`)
      setTimeout(() => setSuccess(''), 3500)
      if (editingId === id) cancelEdit()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao excluir categoria.')
      setTimeout(() => setError(''), 4000)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🏷️ Categorias</h1>
          <p className="page-subtitle">
            {items.length === 1 ? '1 categoria cadastrada' : `${items.length} categorias cadastradas`}
          </p>
        </div>
        <Link to="/receitas" className="btn btn-outline">🍳 Receitas</Link>
      </div>

      {error   && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="form-card" style={{ maxWidth: '520px', marginBottom: '1.5rem' }}>
        <p className="section-title" style={{ marginTop: 0 }}>
          {editingId ? 'Editar Categoria' : 'Nova Categoria'}
        </p>
        <form onSubmit={submit}>
          <div className="form-grid">
            <div className="form-group full">
              <label htmlFor="name">Nome *</label>
              <input
                id="name" value={name} onChange={e => setName(e.target.value)}
                placeholder="Ex: Onigiris"
                className={name.trim() ? 'valid' : ''}
                autoFocus
              />
            </div>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? '⏳ Salvando…' : editingId ? '✓ Salvar Alterações' : '+ Adicionar Categoria'}
            </button>
            {editingId && (
              <button type="button" className="btn btn-ghost" onClick={cancelEdit}>Cancelar</button>
            )}
          </div>
        </form>
      </div>

      {loading ? (
        <div className="loading">Carregando categorias…</div>
      ) : items.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">🏷️</span>
            <p className="empty-text">Nenhuma categoria cadastrada</p>
            <p className="empty-sub">Crie categorias acima (ex: Onigiris, Sushis, Bebidas) para organizar suas receitas.</p>
          </div>
        </div>
      ) : (
        <table className="ing-table">
          <thead>
            <tr>
              <th>Categoria</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map(c => (
              <tr key={c.id}>
                <td style={{ fontWeight: 600 }}>{c.name}</td>
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

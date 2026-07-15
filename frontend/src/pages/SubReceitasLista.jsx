import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { receitasAPI } from '../api'
import RecipeCard, { CATEGORIES } from '../components/RecipeCard'

export default function SubReceitasLista() {
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState('')
  const [search, setSearch]   = useState('')
  const [catFilter, setCat]   = useState('todas')
  const [sortBy, setSortBy]   = useState('nome')

  async function load() {
    try {
      setLoading(true)
      const { data } = await receitasAPI.listar()
      setItems(data)
    } catch {
      setError('Erro ao carregar receitas.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id, name) {
    if (!window.confirm(`Excluir "${name}"? Esta ação não pode ser desfeita.`)) return
    try {
      await receitasAPI.excluir(id)
      setItems(prev => prev.filter(i => i.id !== id))
      setSuccess(`"${name}" excluída com sucesso.`)
      setTimeout(() => setSuccess(''), 3500)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao excluir receita.')
      setTimeout(() => setError(''), 4000)
    }
  }

  const subItems = useMemo(() => {
    const subRecipeIds = new Set()
    for (const r of items) {
      for (const sr of r.sub_recipes || []) subRecipeIds.add(sr.sub_recipe_id)
    }
    return items.filter(r => subRecipeIds.has(r.id))
  }, [items])

  const filtered = useMemo(() => {
    let list = subItems.filter(r =>
      r.name.toLowerCase().includes(search.toLowerCase()) &&
      (catFilter === 'todas' || r.category === catFilter)
    )
    if (sortBy === 'cmv-asc')    list = [...list].sort((a, b) => a.cmv_percent - b.cmv_percent)
    if (sortBy === 'cmv-desc')   list = [...list].sort((a, b) => b.cmv_percent - a.cmv_percent)
    if (sortBy === 'preco-asc')  list = [...list].sort((a, b) => a.sale_price - b.sale_price)
    if (sortBy === 'preco-desc') list = [...list].sort((a, b) => b.sale_price - a.sale_price)
    if (sortBy === 'nome')       list = [...list].sort((a, b) => a.name.localeCompare(b.name))
    return list
  }, [subItems, search, catFilter, sortBy])

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🔗 Sub-Receitas</h1>
          <p className="page-subtitle">
            {subItems.length} sub-receita{subItems.length !== 1 ? 's' : ''} — usadas como ingrediente em outras receitas
          </p>
        </div>
        <div style={{ display: 'flex', gap: '.6rem' }}>
          <Link to="/receitas" className="btn btn-outline">🍳 Receitas</Link>
          <Link to="/receitas/nova" className="btn btn-primary">+ Nova Receita</Link>
        </div>
      </div>

      {error   && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {!loading && subItems.length > 0 && (
        <div className="toolbar">
          <div className="search-wrapper">
            <span className="search-icon">🔍</span>
            <input
              className="search-input"
              type="search"
              placeholder="Buscar sub-receita..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <select className="filter-select" value={catFilter} onChange={e => setCat(e.target.value)}>
            {CATEGORIES.map(c => (
              <option key={c} value={c}>{c === 'todas' ? 'Todas as categorias' : c}</option>
            ))}
          </select>
          <select className="filter-select" value={sortBy} onChange={e => setSortBy(e.target.value)}>
            <option value="nome">Ordenar: Nome</option>
            <option value="cmv-asc">CMV: menor primeiro</option>
            <option value="cmv-desc">CMV: maior primeiro</option>
            <option value="preco-asc">Preço: menor primeiro</option>
            <option value="preco-desc">Preço: maior primeiro</option>
          </select>
          {(search || catFilter !== 'todas') && (
            <span style={{ fontSize: '.84rem', color: 'var(--muted)', whiteSpace: 'nowrap' }}>
              {filtered.length} resultado{filtered.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}

      {loading ? (
        <div className="loading">Carregando sub-receitas…</div>
      ) : subItems.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">🔗</span>
            <p className="empty-text">Nenhuma sub-receita ainda</p>
            <p className="empty-sub">
              Uma receita vira sub-receita quando é usada como ingrediente dentro de outra receita.
            </p>
          </div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">🔍</span>
            <p className="empty-text">Nenhum resultado</p>
            <p className="empty-sub">Tente mudar os filtros.</p>
          </div>
        </div>
      ) : (
        <div className="cards-grid">
          {filtered.map(item => (
            <RecipeCard
              key={item.id}
              item={item}
              editHref={`/receitas/${item.id}/editar`}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}

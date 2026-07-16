import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { receitasAPI } from '../api'
import RecipeCard, { CAT_ICON } from '../components/RecipeCard'

export default function ReceitasLista() {
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

  const subRecipeIds = useMemo(() => {
    const ids = new Set()
    for (const r of items) {
      for (const sr of r.sub_recipes || []) ids.add(sr.sub_recipe_id)
    }
    return ids
  }, [items])

  const mainItems = useMemo(
    () => items.filter(r => !subRecipeIds.has(r.id)),
    [items, subRecipeIds]
  )

  const categoryList = useMemo(() => {
    const cats = new Set(mainItems.map(r => r.category).filter(Boolean))
    return [...cats].sort((a, b) => a.localeCompare(b))
  }, [mainItems])

  useEffect(() => {
    if (catFilter !== 'todas' && !categoryList.includes(catFilter)) setCat('todas')
  }, [categoryList, catFilter])

  const filtered = useMemo(() => {
    let list = mainItems.filter(r =>
      r.name.toLowerCase().includes(search.toLowerCase()) &&
      (catFilter === 'todas' || r.category === catFilter)
    )
    if (sortBy === 'cmv-asc')    list = [...list].sort((a, b) => a.cmv_percent - b.cmv_percent)
    if (sortBy === 'cmv-desc')   list = [...list].sort((a, b) => b.cmv_percent - a.cmv_percent)
    if (sortBy === 'preco-asc')  list = [...list].sort((a, b) => a.sale_price - b.sale_price)
    if (sortBy === 'preco-desc') list = [...list].sort((a, b) => b.sale_price - a.sale_price)
    if (sortBy === 'nome')       list = [...list].sort((a, b) => a.name.localeCompare(b.name))
    return list
  }, [mainItems, search, catFilter, sortBy])

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🍳 Receitas</h1>
          <p className="page-subtitle">
            {mainItems.length} receita{mainItems.length !== 1 ? 's' : ''} cadastrada{mainItems.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '.6rem' }}>
          <Link to="/categorias" className="btn btn-outline">🏷️ Categorias</Link>
          <Link to="/canais" className="btn btn-outline">⚙️ Canais de Venda</Link>
          <Link to="/receitas/sub-receitas" className="btn btn-outline">🔗 Sub-Receitas</Link>
          <Link to="/receitas/nova" className="btn btn-primary">+ Nova Receita</Link>
        </div>
      </div>

      {error   && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {!loading && mainItems.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.5rem', marginBottom: '1rem' }}>
          <button
            type="button"
            className={`btn btn-sm ${catFilter === 'todas' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setCat('todas')}
          >
            Todas ({mainItems.length})
          </button>
          {categoryList.map(c => (
            <button
              key={c}
              type="button"
              className={`btn btn-sm ${catFilter === c ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setCat(c)}
            >
              {CAT_ICON[c] || '📦'} {c} ({mainItems.filter(r => r.category === c).length})
            </button>
          ))}
        </div>
      )}

      {!loading && mainItems.length > 0 && (
        <div className="toolbar">
          <div className="search-wrapper">
            <span className="search-icon">🔍</span>
            <input
              className="search-input"
              type="search"
              placeholder="Buscar receita..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
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
        <div className="loading">Carregando receitas…</div>
      ) : mainItems.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">📋</span>
            <p className="empty-text">Nenhuma receita cadastrada</p>
            <p className="empty-sub">
              <Link to="/receitas/nova" style={{ color: 'var(--orange)', fontWeight: 700 }}>
                Crie sua primeira receita
              </Link>
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

import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { receitasAPI } from '../api'

const fmt    = (v) => `R$ ${Number(v).toFixed(2).replace('.', ',')}`
const fmtPct = (v) => `${Number(v).toFixed(1)}%`

const CAT_ICON = {
  'prato principal': '🍽️',
  'sobremesa':       '🍰',
  'bebida':          '🥤',
  'entrada':         '🥗',
  'petisco':         '🍟',
  'outro':           '📦',
}

const CAT_CLASS = {
  'prato principal': 'cat-prato-principal',
  'sobremesa':       'cat-sobremesa',
  'bebida':          'cat-bebida',
  'entrada':         'cat-entrada',
  'petisco':         'cat-petisco',
  'outro':           'cat-outro',
}

const CATEGORIES = ['todas', 'prato principal', 'sobremesa', 'bebida', 'entrada', 'petisco', 'outro']

function cmvBadgeClass(v) {
  if (v <= 30) return 'badge-green'
  if (v <= 35) return 'badge-orange'
  if (v <= 40) return 'badge-warning'
  return 'badge-red'
}

function cmvTextClass(v) {
  if (v <= 30) return 'cmv-good-text'
  if (v <= 35) return 'cmv-ok-text'
  if (v <= 40) return 'cmv-warn-text'
  return 'cmv-bad-text'
}

function cmvLabel(v) {
  if (v <= 30) return 'Excelente'
  if (v <= 35) return 'Aceitável'
  if (v <= 40) return 'Atenção'
  return 'Alto'
}

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

  const filtered = useMemo(() => {
    let list = items.filter(r =>
      r.name.toLowerCase().includes(search.toLowerCase()) &&
      (catFilter === 'todas' || r.category === catFilter)
    )
    if (sortBy === 'cmv-asc')    list = [...list].sort((a, b) => a.cmv_percent - b.cmv_percent)
    if (sortBy === 'cmv-desc')   list = [...list].sort((a, b) => b.cmv_percent - a.cmv_percent)
    if (sortBy === 'preco-asc')  list = [...list].sort((a, b) => a.sale_price - b.sale_price)
    if (sortBy === 'preco-desc') list = [...list].sort((a, b) => b.sale_price - a.sale_price)
    if (sortBy === 'nome')       list = [...list].sort((a, b) => a.name.localeCompare(b.name))
    return list
  }, [items, search, catFilter, sortBy])

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🍳 Receitas</h1>
          <p className="page-subtitle">
            {items.length} receita{items.length !== 1 ? 's' : ''} cadastrada{items.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Link to="/receitas/nova" className="btn btn-primary">+ Nova Receita</Link>
      </div>

      {error   && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {!loading && items.length > 0 && (
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
        <div className="loading">Carregando receitas…</div>
      ) : items.length === 0 ? (
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
            <div key={item.id} className="recipe-card">
              <div className="recipe-card-header">
                <span className={`cat-badge ${CAT_CLASS[item.category] || 'cat-outro'}`}>
                  {CAT_ICON[item.category] || '📦'} {item.category}
                </span>
                <div className="recipe-card-name">{item.name}</div>
                {item.description && (
                  <div className="recipe-card-desc">{item.description}</div>
                )}
              </div>

              <div className={`recipe-card-cmv ${cmvTextClass(item.cmv_percent)}`}>
                <div className="recipe-card-cmv-value">{fmtPct(item.cmv_percent)}</div>
                <div className="recipe-card-cmv-label">CMV — {cmvLabel(item.cmv_percent)}</div>
                <span className={`badge ${cmvBadgeClass(item.cmv_percent)}`} style={{ marginTop: '.2rem' }}>
                  {item.cmv_percent <= 30 ? '🟢' : item.cmv_percent <= 35 ? '🟡' : item.cmv_percent <= 40 ? '🟠' : '🔴'}
                  &nbsp;{cmvLabel(item.cmv_percent)}
                </span>
              </div>

              <div className="recipe-card-body">
                <div className="recipe-card-row">
                  <span className="recipe-card-label">Preço de venda</span>
                  <span className="recipe-card-value recipe-card-price">{fmt(item.sale_price)}</span>
                </div>
                <div className="recipe-card-row">
                  <span className="recipe-card-label">Custo total</span>
                  <span className="recipe-card-value">{fmt(item.total_cost)}</span>
                </div>
                <div className="recipe-card-row">
                  <span className="recipe-card-label">Rendimento</span>
                  <span className="recipe-card-value">
                    {item.yield_portions} {item.yield_portions === 1 ? 'porção' : 'porções'}
                  </span>
                </div>
                <div className="recipe-card-row">
                  <span className="recipe-card-label">Custo/porção</span>
                  <span className="recipe-card-value">{fmt(item.total_cost / item.yield_portions)}</span>
                </div>
              </div>

              <div className="recipe-card-actions">
                <Link to={`/receitas/${item.id}/editar`} className="btn btn-sm btn-outline">
                  Editar
                </Link>
                <button
                  className="btn btn-sm btn-danger"
                  onClick={() => handleDelete(item.id, item.name)}
                >
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

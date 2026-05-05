import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { comprasAPI } from '../api'

const fmt = (v) => `R$ ${Number(v).toFixed(2).replace('.', ',')}`

function fmtDate(d) {
  if (!d) return ''
  const [y, m, day] = d.split('-')
  return `${day}/${m}/${y}`
}

export default function ComprasLista() {
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState('')
  const [search, setSearch]   = useState('')

  async function load() {
    try {
      setLoading(true)
      const { data } = await comprasAPI.listar()
      setItems(data)
    } catch {
      setError('Erro ao carregar compras.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id) {
    if (!window.confirm('Excluir esta nota de compra? Essa ação não reverte custos nem estoque.')) return
    try {
      await comprasAPI.excluir(id)
      setItems(prev => prev.filter(i => i.id !== id))
      setSuccess('Compra excluída.')
      setTimeout(() => setSuccess(''), 3500)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao excluir compra.')
      setTimeout(() => setError(''), 4000)
    }
  }

  const filtered = useMemo(() =>
    items.filter(i =>
      !search || (i.supplier || '').toLowerCase().includes(search.toLowerCase())
    ),
    [items, search]
  )

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🛒 Compras</h1>
          <p className="page-subtitle">
            {items.length} nota{items.length !== 1 ? 's' : ''} de compra registrada{items.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Link to="/compras/nova" className="btn btn-primary">+ Nova Compra</Link>
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
              placeholder="Buscar por fornecedor..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          {search && (
            <span style={{ fontSize: '.84rem', color: 'var(--muted)', whiteSpace: 'nowrap' }}>
              {filtered.length} resultado{filtered.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}

      {loading ? (
        <div className="loading">Carregando compras…</div>
      ) : items.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">🛍️</span>
            <p className="empty-text">Nenhuma compra registrada</p>
            <p className="empty-sub">
              <Link to="/compras/nova" style={{ color: 'var(--orange)', fontWeight: 700 }}>
                Registre sua primeira compra
              </Link>
            </p>
          </div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">🔍</span>
            <p className="empty-text">Nenhum resultado para "{search}"</p>
            <p className="empty-sub">Tente outro fornecedor.</p>
          </div>
        </div>
      ) : (
        <div className="cards-grid">
          {filtered.map(item => (
            <div key={item.id} className="ing-card">
              <div className="ing-card-header">
                <span className="ing-card-name">{fmtDate(item.date)}</span>
                {item.supplier && <span className="badge badge-unit">{item.supplier}</span>}
              </div>
              <div className="ing-card-body">
                {item.location && (
                  <div className="ing-card-row">
                    <span className="ing-card-label">📍 Local</span>
                    <span className="ing-card-value">{item.location}</span>
                  </div>
                )}
                <div className="ing-card-row">
                  <span className="ing-card-label">Itens</span>
                  <span className="ing-card-value">
                    {item.items.length} item{item.items.length !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="ing-card-row">
                  <span className="ing-card-label">Total gasto</span>
                  <span className="ing-card-value highlight">{fmt(item.total)}</span>
                </div>
                {item.notes && (
                  <div className="ing-card-row" style={{ marginTop: '.4rem' }}>
                    <span className="ing-card-label">Obs.</span>
                    <span className="ing-card-value" style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                      {item.notes}
                    </span>
                  </div>
                )}
              </div>
              <div className="ing-card-actions">
                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(item.id)}>
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

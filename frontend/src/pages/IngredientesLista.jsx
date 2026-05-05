import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ingredientesAPI } from '../api'

const fmt = (v, d = 2) => `R$ ${Number(v).toFixed(d).replace('.', ',')}`

function yieldClass(pct) {
  if (pct > 100) return 'boost'
  if (pct >= 90) return 'good'
  if (pct >= 50) return 'ok'
  return 'bad'
}

function calcYieldTotal(item) {
  if (item.reduction_stages && item.reduction_stages.length > 0) {
    return item.reduction_stages.reduce((a, s) => a * s.yield_percentage / 100, 1) * 100
  }
  return item.yield_percentage ?? 100
}

export default function IngredientesLista() {
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState('')
  const [search, setSearch]   = useState('')

  async function load() {
    try {
      setLoading(true)
      const { data } = await ingredientesAPI.listar()
      setItems(data)
    } catch {
      setError('Erro ao carregar ingredientes.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id, name) {
    if (!window.confirm(`Excluir "${name}"? Esta ação não pode ser desfeita.`)) return
    try {
      await ingredientesAPI.excluir(id)
      setItems(prev => prev.filter(i => i.id !== id))
      setSuccess(`"${name}" excluído com sucesso.`)
      setTimeout(() => setSuccess(''), 3500)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao excluir ingrediente.')
      setTimeout(() => setError(''), 4000)
    }
  }

  const filtered = useMemo(() =>
    items.filter(i => i.name.toLowerCase().includes(search.toLowerCase())),
    [items, search]
  )

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🥬 Ingredientes</h1>
          <p className="page-subtitle">
            {items.length} ingrediente{items.length !== 1 ? 's' : ''} cadastrado{items.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Link to="/ingredientes/novo" className="btn btn-primary">+ Novo Ingrediente</Link>
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
              placeholder="Buscar ingrediente..."
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
        <div className="loading">Carregando ingredientes…</div>
      ) : items.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">🥦</span>
            <p className="empty-text">Nenhum ingrediente cadastrado</p>
            <p className="empty-sub">
              <Link to="/ingredientes/novo" style={{ color: 'var(--orange)', fontWeight: 700 }}>
                Cadastre seu primeiro ingrediente
              </Link>
            </p>
          </div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">🔍</span>
            <p className="empty-text">Nenhum resultado para "{search}"</p>
            <p className="empty-sub">Tente outro termo de busca.</p>
          </div>
        </div>
      ) : (
        <div className="cards-grid">
          {filtered.map(item => {
            const yieldTotal       = calcYieldTotal(item)
            const hasYieldFactor   = Math.abs(yieldTotal - 100) > 0.1
            const hasProcessingCost = item.processing_cost_per_unit != null || (item.processing_cost_per_batch != null && item.processing_batch_size != null)
            const cls              = yieldClass(yieldTotal)
            const isCalc           = (hasYieldFactor || hasProcessingCost) && item.real_unit_cost != null

            return (
              <div key={item.id} className="ing-card">
                <div className="ing-card-header">
                  <span className="ing-card-name">{item.name}</span>
                  <span className="badge badge-unit">{item.unit}</span>
                </div>

                <div className="ing-card-body">
                  <div className="ing-card-row">
                    <span className="ing-card-label">Custo unitário</span>
                    <span className="ing-card-value">{fmt(item.unit_cost, 4)}/{item.unit}</span>
                  </div>

                  {isCalc && (
                    <div className="ing-card-row">
                      <span className="ing-card-label">Custo real</span>
                      <span className="ing-card-value highlight">{fmt(item.real_unit_cost, 4)}/{item.unit}</span>
                    </div>
                  )}

                  {(item.processing_cost_per_unit != null || item.processing_cost_per_batch != null) && (
                    <div className="ing-card-row">
                      <span className="ing-card-label">Processamento</span>
                      <span className="ing-card-value" style={{ color: 'var(--muted)', fontSize: '.8rem' }}>
                        {item.processing_cost_per_unit != null
                          ? `+${fmt(item.processing_cost_per_unit, 2)}/${item.unit}`
                          : `+${fmt(item.processing_cost_per_batch, 2)}/lote`}
                      </span>
                    </div>
                  )}

                  <div className="ing-card-row">
                    <span className="ing-card-label">Estoque mín.</span>
                    <span className="ing-card-value">{item.min_stock} {item.unit}</span>
                  </div>

                  <div className="ing-card-yield">
                    <div className="yield-label-row">
                      <span className="yield-label-text">
                        Aproveitamento
                        {item.reduction_stages?.length > 0 && ' (multi-etapa)'}
                      </span>
                      <span className={`yield-pct ${cls}`}>{yieldTotal.toFixed(1)}%</span>
                    </div>
                    <div className="yield-track">
                      <div
                        className={`yield-fill ${cls}`}
                        style={{ width: `${Math.min(yieldTotal, 100)}%` }}
                      />
                    </div>
                  </div>
                </div>

                <div className="ing-card-actions">
                  <Link to={`/ingredientes/${item.id}/historico`} className="btn btn-sm btn-outline">
                    📈 Histórico
                  </Link>
                  <Link to={`/ingredientes/${item.id}/editar`} className="btn btn-sm btn-outline">
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
            )
          })}
        </div>
      )}
    </div>
  )
}

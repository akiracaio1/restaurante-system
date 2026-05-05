import { useState, useEffect, useMemo } from 'react'
import { estoqueAPI } from '../api'

const fmtQty = (v) => Number(v).toFixed(3).replace('.', ',')

function statusInfo(qty, min) {
  if (min <= 0) return { label: '🟢 OK', cls: 'badge-green' }
  if (qty < min) return { label: '🔴 Crítico', cls: 'badge-red' }
  if (qty < min * 1.5) return { label: '🟡 Baixo', cls: 'badge-warning' }
  return { label: '🟢 OK', cls: 'badge-green' }
}

export default function EstoqueLista() {
  const [items, setItems]         = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState('')
  const [success, setSuccess]     = useState('')
  const [search, setSearch]       = useState('')
  const [adjustId, setAdjustId]   = useState(null)
  const [adjQty, setAdjQty]       = useState('')
  const [adjNotes, setAdjNotes]   = useState('')
  const [adjusting, setAdjusting] = useState(false)

  async function load() {
    try {
      setLoading(true)
      const { data } = await estoqueAPI.listar()
      setItems(data)
    } catch {
      setError('Erro ao carregar estoque.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function openAdjust(item) {
    setAdjustId(item.ingredient_id)
    setAdjQty(String(item.quantity))
    setAdjNotes('')
    setError('')
  }

  async function handleAdjust(e) {
    e.preventDefault()
    const qty = Number(adjQty)
    if (isNaN(qty) || qty < 0) return setError('Quantidade inválida.')
    try {
      setAdjusting(true)
      await estoqueAPI.ajustar(adjustId, { quantity: qty, notes: adjNotes || null })
      setSuccess('Estoque ajustado com sucesso.')
      setTimeout(() => setSuccess(''), 3500)
      setAdjustId(null)
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao ajustar estoque.')
      setTimeout(() => setError(''), 4000)
    } finally {
      setAdjusting(false)
    }
  }

  const filtered = useMemo(() =>
    items.filter(i =>
      !search || i.ingredient_name.toLowerCase().includes(search.toLowerCase())
    ),
    [items, search]
  )

  const adjustItem = items.find(i => i.ingredient_id === adjustId)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">📦 Estoque</h1>
          <p className="page-subtitle">
            {items.length} ingrediente{items.length !== 1 ? 's' : ''} no estoque
          </p>
        </div>
      </div>

      {error   && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {adjustId && adjustItem && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div className="form-card" style={{ maxWidth: '420px', width: '100%', margin: '1rem' }}>
            <h2 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>
              Ajustar Estoque — {adjustItem.ingredient_name}
            </h2>
            <form onSubmit={handleAdjust}>
              <div className="form-group">
                <label>Nova quantidade ({adjustItem.unit})</label>
                <input
                  type="number"
                  step="0.001"
                  min="0"
                  value={adjQty}
                  onChange={e => setAdjQty(e.target.value)}
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label>Observação</label>
                <input
                  type="text"
                  value={adjNotes}
                  onChange={e => setAdjNotes(e.target.value)}
                  placeholder="Motivo do ajuste…"
                />
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={adjusting}>
                  {adjusting ? '⏳ Salvando…' : '✓ Salvar'}
                </button>
                <button type="button" className="btn btn-ghost" onClick={() => setAdjustId(null)}>
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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
        <div className="loading">Carregando estoque…</div>
      ) : items.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">📦</span>
            <p className="empty-text">Nenhum item em estoque</p>
            <p className="empty-sub">Registre uma compra para inicializar o estoque.</p>
          </div>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'auto' }}>
          <table className="ing-table" style={{ margin: 0 }}>
            <thead>
              <tr>
                <th>Ingrediente</th>
                <th>Unidade</th>
                <th>Estoque Atual</th>
                <th>Estoque Mín.</th>
                <th>Status</th>
                <th>Ação</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(item => {
                const { label, cls } = statusInfo(item.quantity, item.min_stock)
                return (
                  <tr key={item.ingredient_id}>
                    <td style={{ fontWeight: 600 }}>{item.ingredient_name}</td>
                    <td>{item.unit}</td>
                    <td style={{ fontWeight: 700 }}>{fmtQty(item.quantity)}</td>
                    <td style={{ color: 'var(--muted)' }}>{fmtQty(item.min_stock)}</td>
                    <td><span className={`badge ${cls}`}>{label}</span></td>
                    <td>
                      <button className="btn btn-sm btn-outline" onClick={() => openAdjust(item)}>
                        Ajustar
                      </button>
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

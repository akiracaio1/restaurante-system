import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ingredientesAPI } from '../api'
import { useAuth } from '../context/AuthContext'

const fmt = (v, d = 2) => `R$ ${Number(v).toFixed(d).replace('.', ',')}`
const fmtQty = (v) => Number(v).toFixed(3).replace('.', ',')

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
  const { isMaster } = useAuth()
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState('')
  const [merge, setMerge]     = useState(null) // { source, targetId, preview, busy, error }
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

  const sameUnit = (a, b) => (a.unit || '').trim().toLowerCase() === (b.unit || '').trim().toLowerCase()
  const mergeCandidates = merge
    ? items.filter(i => i.id !== merge.source.id && sameUnit(i, merge.source))
    : []
  const mergeTarget = merge ? items.find(i => String(i.id) === merge.targetId) : null

  async function previewMerge() {
    setMerge(m => ({ ...m, busy: true, error: '', preview: null }))
    try {
      const { data } = await ingredientesAPI.mesclar(merge.targetId, { source_id: merge.source.id, dry_run: true })
      setMerge(m => ({ ...m, busy: false, preview: data }))
    } catch (err) {
      setMerge(m => ({ ...m, busy: false, error: err.response?.data?.detail || 'Erro ao calcular a mesclagem.' }))
    }
  }

  async function confirmMerge() {
    setMerge(m => ({ ...m, busy: true, error: '' }))
    try {
      const { data } = await ingredientesAPI.mesclar(merge.targetId, { source_id: merge.source.id })
      setMerge(null)
      setSuccess(`"${data.source_name}" foi mesclado em "${data.target_name}". Nada foi perdido nas receitas, compras e estoque.`)
      setTimeout(() => setSuccess(''), 8000)
      await load()
    } catch (err) {
      setMerge(m => ({ ...m, busy: false, error: (err.response?.data?.detail || 'Erro ao mesclar.') + ' Nada foi alterado.' }))
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
        {isMaster && <Link to="/ingredientes/novo" className="btn btn-primary">+ Novo Ingrediente</Link>}
      </div>

      {error   && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {merge && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', overflow: 'auto',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }}>
          <div className="form-card" style={{ maxWidth: '560px', width: '100%', margin: '1rem' }}>
            <h2 style={{ marginBottom: '.75rem', fontSize: '1.1rem' }}>🔀 Mesclar ingredientes</h2>
            <p style={{ marginBottom: '1rem', fontSize: '.9rem' }}>
              <strong>{merge.source.name}</strong> será <strong>removido</strong>. Tudo que usa ele
              (receitas, custos extras, compras e estoque) passa para o ingrediente que você escolher abaixo.
            </p>

            {merge.error && <div className="alert alert-error">{merge.error}</div>}

            {mergeCandidates.length === 0 ? (
              <div className="alert alert-error">
                Não há outro ingrediente com a unidade "{merge.source.unit}". Só dá para mesclar ingredientes com a mesma unidade.
              </div>
            ) : (
              <div className="form-group">
                <label>Manter este ingrediente</label>
                <select
                  value={merge.targetId}
                  disabled={merge.busy}
                  onChange={e => setMerge(m => ({ ...m, targetId: e.target.value, preview: null, error: '' }))}
                >
                  <option value="">Selecione…</option>
                  {mergeCandidates.map(i => (
                    <option key={i.id} value={i.id}>{i.name} ({i.unit})</option>
                  ))}
                </select>
              </div>
            )}

            {merge.preview && (
              <div className="add-box" style={{ fontSize: '.88rem', lineHeight: 1.5 }}>
                <p className="add-box-label">O que vai acontecer</p>
                <ul style={{ margin: 0, paddingLeft: '1.2rem' }}>
                  <li>
                    Receitas que passam a usar <strong>{merge.preview.target_name}</strong>:{' '}
                    {merge.preview.recipes_moved.length ? merge.preview.recipes_moved.join(', ') : 'nenhuma'}
                  </li>
                  {merge.preview.recipes_combined.length > 0 && (
                    <li>
                      Receitas que usavam os dois (as quantidades serão somadas):{' '}
                      {merge.preview.recipes_combined.join(', ')}
                    </li>
                  )}
                  {merge.preview.base_recipes.length > 0 && (
                    <li>Calculadora de proporção: {merge.preview.base_recipes.join(', ')}</li>
                  )}
                  <li>Custos extras de modalidades de venda ajustados: {merge.preview.channel_prices_updated}</li>
                  <li>Compras do histórico que passam para ele: {merge.preview.purchase_items_moved}</li>
                  <li>
                    Estoque: {fmtQty(merge.preview.stock_target_before)} + {fmtQty(merge.preview.stock_source_before)}
                    {' = '}<strong>{fmtQty(merge.preview.stock_after)} {merge.preview.unit}</strong>
                  </li>
                  {mergeTarget && (
                    <li>
                      O custo unitário que vale é o de <strong>{mergeTarget.name}</strong>:{' '}
                      {fmt(mergeTarget.unit_cost, 4)}/{mergeTarget.unit}
                    </li>
                  )}
                </ul>
                <p style={{ margin: '.6rem 0 0', fontWeight: 700, color: '#e74c3c' }}>
                  Esta ação não pode ser desfeita.
                </p>
              </div>
            )}

            <div className="form-actions">
              {merge.preview ? (
                <button type="button" className="btn btn-danger" onClick={confirmMerge} disabled={merge.busy}>
                  {merge.busy ? '⏳ Mesclando…' : '✓ Confirmar mesclagem'}
                </button>
              ) : (
                <button type="button" className="btn btn-primary" onClick={previewMerge} disabled={!merge.targetId || merge.busy}>
                  {merge.busy ? '⏳ Calculando…' : 'Ver o que vai mudar'}
                </button>
              )}
              <button type="button" className="btn btn-ghost" onClick={() => setMerge(null)} disabled={merge.busy}>
                Cancelar
              </button>
            </div>
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
        <div className="loading">Carregando ingredientes…</div>
      ) : items.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">🥦</span>
            <p className="empty-text">Nenhum ingrediente cadastrado</p>
            {isMaster && (
              <p className="empty-sub">
                <Link to="/ingredientes/novo" style={{ color: 'var(--orange)', fontWeight: 700 }}>
                  Cadastre seu primeiro ingrediente
                </Link>
              </p>
            )}
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
                  {isMaster && (
                    <>
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
                    </>
                  )}

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

                {isMaster && (
                  <div className="ing-card-actions">
                    <Link to={`/ingredientes/${item.id}/historico`} className="btn btn-sm btn-outline">
                      📈 Histórico
                    </Link>
                    <Link to={`/ingredientes/${item.id}/editar`} className="btn btn-sm btn-outline">
                      Editar
                    </Link>
                    <button
                      className="btn btn-sm btn-outline"
                      onClick={() => setMerge({ source: item, targetId: '', preview: null, busy: false, error: '' })}
                    >
                      🔀 Mesclar
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleDelete(item.id, item.name)}
                    >
                      Excluir
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

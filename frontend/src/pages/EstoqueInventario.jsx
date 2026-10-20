import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { estoqueAPI } from '../api'

const DRAFT_KEY = 'inventario-rascunho'
const fmtQty = (v) => Number(v).toFixed(3).replace('.', ',')

function parseCount(text) {
  const t = String(text ?? '').trim().replace(',', '.')
  if (t === '') return { empty: true }
  const n = Number(t)
  if (!Number.isFinite(n) || n < 0) return { invalid: true }
  return { value: n }
}

function loadDraft() {
  try { return JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}') } catch { return {} }
}

function Diff({ value, current }) {
  const d = Math.round((value - current) * 1000) / 1000
  if (d === 0) return <span style={{ color: 'var(--muted)' }}>=</span>
  return (
    <span style={{ color: d > 0 ? '#27ae60' : '#e74c3c', fontWeight: 700 }}>
      {d > 0 ? '+' : '−'}{fmtQty(Math.abs(d))}
    </span>
  )
}

export default function EstoqueInventario() {
  const [ingredientes, setIngredientes] = useState([])
  const [receitas, setReceitas]         = useState([])
  const [values, setValues]             = useState({})
  const [restored, setRestored]         = useState(0)
  const [loaded, setLoaded]             = useState(false)
  const [loading, setLoading]           = useState(true)
  const [search, setSearch]             = useState('')
  const [error, setError]               = useState('')
  const [saving, setSaving]             = useState(false)
  const [result, setResult]             = useState(null)

  async function load() {
    try {
      setLoading(true)
      const [{ data: ings }, { data: recs }] = await Promise.all([estoqueAPI.listar(), estoqueAPI.listarReceitas()])
      setIngredientes(ings)
      setReceitas(recs)
      const known = new Set([...ings.map(i => `i-${i.ingredient_id}`), ...recs.map(r => `r-${r.recipe_id}`)])
      const draft = Object.fromEntries(Object.entries(loadDraft()).filter(([k, v]) => known.has(k) && String(v).trim() !== ''))
      setValues(draft)
      setRestored(Object.keys(draft).length)
      setLoaded(true)
    } catch {
      setError('Erro ao carregar o estoque.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  // Rascunho automático: se a página fechar no meio da contagem, nada se perde.
  useEffect(() => {
    if (!loaded) return
    try {
      const filled = Object.fromEntries(Object.entries(values).filter(([, v]) => String(v).trim() !== ''))
      if (Object.keys(filled).length) localStorage.setItem(DRAFT_KEY, JSON.stringify(filled))
      else localStorage.removeItem(DRAFT_KEY)
    } catch { /* sem armazenamento local: segue sem rascunho */ }
  }, [values, loaded])

  const rows = useMemo(() => [
    ...ingredientes.map(i => ({ key: `i-${i.ingredient_id}`, type: 'ingrediente', id: i.ingredient_id, name: i.ingredient_name, unit: i.unit, current: i.quantity })),
    ...receitas.map(r => ({ key: `r-${r.recipe_id}`, type: 'receita', id: r.recipe_id, name: r.recipe_name, unit: r.unit, current: r.quantity })),
  ], [ingredientes, receitas])

  const parsed = useMemo(() => Object.fromEntries(rows.map(r => [r.key, parseCount(values[r.key])])), [rows, values])
  const filled   = rows.filter(r => parsed[r.key].value !== undefined)
  const invalid  = rows.filter(r => parsed[r.key].invalid)
  const changed  = filled.filter(r => Math.abs(parsed[r.key].value - r.current) > 1e-9)

  const visible = (type) => rows.filter(r => r.type === type && (!search || r.name.toLowerCase().includes(search.toLowerCase())))

  function setCount(key, text) {
    setValues(prev => ({ ...prev, [key]: text }))
    setError('')
  }

  // Enter vai para o próximo campo, como numa planilha.
  function onKeyDown(e) {
    if (e.key !== 'Enter') return
    e.preventDefault()
    const inputs = [...document.querySelectorAll('input[data-count="1"]')]
    const next = inputs[inputs.indexOf(e.target) + 1]
    if (next) { next.focus(); next.select() }
  }

  function clearAll() {
    if (!window.confirm('Limpar todas as contagens digitadas?')) return
    setValues({})
    setRestored(0)
  }

  async function save() {
    if (invalid.length) return setError('Corrija os valores marcados em vermelho (use números, sem negativos).')
    if (!filled.length) return
    const msg = `Salvar o inventário?\n\n${changed.length} item(ns) serão alterados e ${filled.length - changed.length} já estavam corretos.\nItens em branco não serão alterados.`
    if (!window.confirm(msg)) return
    try {
      setSaving(true)
      const { data } = await estoqueAPI.inventario({
        items: filled.map(r => ({ type: r.type, id: r.id, quantity: parsed[r.key].value })),
      })
      try { localStorage.removeItem(DRAFT_KEY) } catch { /* ignora */ }
      setValues({})
      setRestored(0)
      setResult(data)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? `${detail}. Nada foi salvo.` : 'Erro ao salvar o inventário. Nada foi salvo.')
    } finally {
      setSaving(false)
    }
  }

  async function startNew() {
    setResult(null)
    setSearch('')
    await load()
  }

  const header = (
    <div className="page-header">
      <div>
        <h1 className="page-title">📋 Inventário de estoque</h1>
        <p className="page-subtitle">
          Digite a quantidade contada de cada item e salve tudo de uma vez. Itens em branco não são alterados.
        </p>
      </div>
      <Link to="/estoque" className="btn btn-ghost">← Voltar ao Estoque</Link>
    </div>
  )

  if (result) {
    return (
      <div>
        {header}
        <div className="alert alert-success">
          ✓ Inventário salvo: <strong>{result.updated}</strong> item(ns) atualizado(s)
          {result.unchanged > 0 && <>, {result.unchanged} já estava(m) correto(s)</>}.
        </div>
        {result.changes.length > 0 && (
          <div className="card" style={{ padding: 0, overflow: 'auto', marginBottom: '1rem' }}>
            <table className="ing-table" style={{ margin: 0 }}>
              <thead>
                <tr><th>Item</th><th>Antes</th><th>Contado</th><th>Diferença</th></tr>
              </thead>
              <tbody>
                {result.changes.map(c => (
                  <tr key={`${c.type}-${c.id}`}>
                    <td style={{ fontWeight: 600 }}>{c.type === 'receita' ? '🍳' : '🥬'} {c.name}</td>
                    <td style={{ color: 'var(--muted)' }}>{fmtQty(c.before)} {c.unit}</td>
                    <td style={{ fontWeight: 700 }}>{fmtQty(c.after)} {c.unit}</td>
                    <td><Diff value={c.after} current={c.before} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div style={{ display: 'flex', gap: '.6rem' }}>
          <Link to="/estoque" className="btn btn-primary">Voltar ao Estoque</Link>
          <button type="button" className="btn btn-outline" onClick={startNew}>Novo inventário</button>
        </div>
      </div>
    )
  }

  function section(title, type) {
    const list = visible(type)
    if (list.length === 0) return null
    return (
      <div className="card" style={{ padding: 0, overflow: 'auto', marginBottom: '1rem' }}>
        <table className="ing-table" style={{ margin: 0 }}>
          <thead>
            <tr>
              <th>{title}</th>
              <th>Unidade</th>
              <th>No sistema</th>
              <th style={{ width: '160px' }}>Contagem</th>
              <th>Diferença</th>
            </tr>
          </thead>
          <tbody>
            {list.map(r => {
              const p = parsed[r.key]
              return (
                <tr key={r.key}>
                  <td style={{ fontWeight: 600 }}>{r.name}</td>
                  <td>{r.unit}</td>
                  <td style={{ color: 'var(--muted)' }}>{fmtQty(r.current)}</td>
                  <td>
                    <input
                      data-count="1"
                      type="number"
                      inputMode="decimal"
                      step="0.001"
                      min="0"
                      value={values[r.key] ?? ''}
                      onChange={e => setCount(r.key, e.target.value)}
                      onKeyDown={onKeyDown}
                      placeholder="—"
                      aria-label={`Contagem de ${r.name}`}
                      style={{ width: '130px', borderColor: p.invalid ? '#e74c3c' : undefined }}
                    />
                  </td>
                  <td>{p.value !== undefined ? <Diff value={p.value} current={r.current} /> : ''}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div>
      {header}

      {error && <div className="alert alert-error">{error}</div>}
      {restored > 0 && (
        <div className="alert alert-success">
          Recuperei {restored} contagem(ns) que você tinha digitado e não tinha salvo.
        </div>
      )}

      {loading ? (
        <div className="loading">Carregando estoque…</div>
      ) : rows.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">📦</span>
            <p className="empty-text">Nada para contar ainda</p>
            <p className="empty-sub">Cadastre ingredientes e receitas primeiro.</p>
          </div>
        </div>
      ) : (
        <>
          <div className="toolbar">
            <div className="search-wrapper">
              <span className="search-icon">🔍</span>
              <input
                className="search-input"
                type="search"
                placeholder="Buscar item..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
          </div>

          {section('🥬 Ingredientes', 'ingrediente')}
          {section('🍳 Receitas', 'receita')}
          {rows.length > 0 && visible('ingrediente').length + visible('receita').length === 0 && (
            <div className="card"><div className="empty-state"><p className="empty-text">Nenhum item encontrado</p></div></div>
          )}

          <div style={{
            position: 'sticky', bottom: 0, background: 'var(--surface, #fff)', borderTop: '1px solid var(--border, #ddd)',
            padding: '.75rem 1rem', display: 'flex', flexWrap: 'wrap', gap: '.75rem', alignItems: 'center',
            justifyContent: 'space-between', boxShadow: '0 -4px 12px rgba(0,0,0,.06)',
          }}>
            <span style={{ fontSize: '.9rem' }}>
              <strong>{filled.length}</strong> de {rows.length} contado(s)
              {' · '}<strong>{changed.length}</strong> com diferença
              {invalid.length > 0 && <span style={{ color: '#e74c3c', fontWeight: 700 }}> · {invalid.length} inválido(s)</span>}
            </span>
            <span style={{ display: 'flex', gap: '.5rem' }}>
              <button type="button" className="btn btn-ghost" onClick={clearAll} disabled={saving || (!filled.length && !invalid.length)}>
                Limpar tudo
              </button>
              <button type="button" className="btn btn-primary" onClick={save} disabled={saving || filled.length === 0}>
                {saving ? '⏳ Salvando…' : `✓ Salvar inventário (${filled.length})`}
              </button>
            </span>
          </div>
        </>
      )}
    </div>
  )
}

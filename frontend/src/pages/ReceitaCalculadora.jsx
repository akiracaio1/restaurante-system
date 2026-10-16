import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { receitasAPI } from '../api'

function fmtQty(v) {
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toFixed(3).replace(/0+$/, '').replace(/\.$/, '')
}

export default function ReceitaCalculadora() {
  const { id } = useParams()
  const [recipe, setRecipe]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  const [baseQty, setBaseQty] = useState('')
  const [result, setResult]   = useState(null)
  const [calculating, setCalculating] = useState(false)
  const [calcError, setCalcError]     = useState('')

  useEffect(() => {
    async function load() {
      try {
        const { data } = await receitasAPI.buscar(id)
        setRecipe(data)
      } catch {
        setError('Erro ao carregar receita.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  async function calcular(e) {
    e.preventDefault()
    setCalcError('')
    setResult(null)
    const qty = Number(baseQty)
    if (!baseQty || isNaN(qty) || qty <= 0) {
      setCalcError('Informe uma quantidade maior que zero.')
      return
    }
    try {
      setCalculating(true)
      const { data } = await receitasAPI.calcularProporcao(id, qty)
      setResult(data)
    } catch (err) {
      setCalcError(err.response?.data?.detail || 'Erro ao calcular proporção.')
    } finally {
      setCalculating(false)
    }
  }

  if (loading) return <div className="loading">Carregando…</div>

  if (!recipe?.is_proportional) {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">🧮 Calculadora</h1>
          <Link to="/receitas" className="btn btn-ghost">← Voltar</Link>
        </div>
        <div className="alert alert-error">
          Esta receita não tem a calculadora de proporção habilitada.{' '}
          <Link to={`/receitas/${id}/editar`} style={{ color: 'inherit', fontWeight: 700 }}>
            Habilite em Editar Receita
          </Link>.
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🧮 Calculadora — {recipe.name}</h1>
          <p className="page-subtitle">
            Informe quanto você tem de {recipe.proportion_base_ingredient_name} e veja a quantidade dos demais ingredientes
          </p>
        </div>
        <Link to="/receitas" className="btn btn-ghost">← Voltar</Link>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="form-card" style={{ maxWidth: '520px' }}>
        <form onSubmit={calcular}>
          <div className="form-group">
            <label htmlFor="baseQty">
              Quantidade de {recipe.proportion_base_ingredient_name} disponível
            </label>
            <input
              id="baseQty"
              type="number"
              step="0.001"
              min="0.001"
              value={baseQty}
              onChange={e => setBaseQty(e.target.value)}
              placeholder={`Ex: 1.35`}
              autoFocus
            />
          </div>
          {calcError && <div className="alert alert-error">{calcError}</div>}
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={calculating}>
              {calculating ? '⏳ Calculando…' : '✓ Calcular'}
            </button>
          </div>
        </form>
      </div>

      {result && (
        <div className="card" style={{ marginTop: '1.5rem', display: 'flex', flexWrap: 'wrap', gap: '.5rem 2rem' }}>
          <div>
            <div className="recipe-card-label">Rendimento estimado</div>
            <div style={{ fontWeight: 800, fontSize: '1.25rem' }}>
              {fmtQty(result.calculated_yield)} {result.yield_unit}
            </div>
          </div>
          <div>
            <div className="recipe-card-label">Receita base rende</div>
            <div style={{ fontWeight: 600 }}>
              {fmtQty(result.base_yield)} {result.yield_unit}
            </div>
          </div>
        </div>
      )}

      {result && (
        <div className="card" style={{ marginTop: '1rem', padding: 0, overflow: 'auto' }}>
          <table className="ing-table" style={{ margin: 0 }}>
            <thead>
              <tr>
                <th>Ingrediente</th>
                <th>Proporção cadastrada</th>
                <th>Quantidade a usar</th>
              </tr>
            </thead>
            <tbody>
              {result.ingredients.map(ing => (
                <tr key={ing.ingredient_id}>
                  <td style={{ fontWeight: 600 }}>
                    {ing.ingredient_id === result.base_ingredient_id ? '⭐ ' : ''}
                    {ing.ingredient_name}
                  </td>
                  <td>{fmtQty(ing.base_quantity)} {ing.unit}</td>
                  <td style={{ fontWeight: 700, fontSize: '1.05rem' }}>
                    {fmtQty(ing.calculated_quantity)} {ing.unit}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { receitasAPI } from '../api'
import { useAuth } from '../context/AuthContext'

function fmtQty(v) {
  const n = Number(v)
  return Number.isInteger(n) ? String(n) : n.toFixed(3).replace(/0+$/, '').replace(/\.$/, '')
}

// Consulta de receita para quem produz: ingredientes, quantidades, rendimento e
// descrição. O servidor não envia nenhum valor financeiro ao perfil Operação.
export default function ReceitaDetalhe() {
  const { id } = useParams()
  const { isMaster } = useAuth()
  const [recipe, setRecipe]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  useEffect(() => {
    receitasAPI.buscar(id)
      .then(({ data }) => setRecipe(data))
      .catch(() => setError('Receita não encontrada.'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="loading">Carregando…</div>

  if (error || !recipe) {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">Receita</h1>
          <Link to="/receitas" className="btn btn-ghost">← Voltar</Link>
        </div>
        <div className="alert alert-error">{error || 'Receita não encontrada.'}</div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🍳 {recipe.name}</h1>
          <p className="page-subtitle">
            {recipe.category} · rende {recipe.yield_portions} {recipe.stock_unit || 'porção'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '.6rem' }}>
          {recipe.is_proportional && (
            <Link to={`/receitas/${recipe.id}/calculadora`} className="btn btn-secondary">🧮 Calculadora</Link>
          )}
          {isMaster && (
            <Link to={`/receitas/${recipe.id}/editar`} className="btn btn-outline">Editar</Link>
          )}
          <Link to="/receitas" className="btn btn-ghost">← Voltar</Link>
        </div>
      </div>

      {recipe.description && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <p className="section-title">Descrição / modo de preparo</p>
          <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{recipe.description}</p>
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: 'auto', marginBottom: '1rem' }}>
        <table className="ing-table" style={{ margin: 0 }}>
          <thead>
            <tr>
              <th>Ingrediente</th>
              <th>Quantidade</th>
            </tr>
          </thead>
          <tbody>
            {recipe.ingredients.map(ri => (
              <tr key={ri.ingredient_id}>
                <td style={{ fontWeight: 600 }}>
                  {ri.ingredient_id === recipe.proportion_base_ingredient_id ? '⭐ ' : ''}
                  {ri.ingredient_name}
                </td>
                <td>{fmtQty(ri.quantity)} {ri.ingredient_unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {recipe.sub_recipes?.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'auto' }}>
          <table className="ing-table" style={{ margin: 0 }}>
            <thead>
              <tr>
                <th>Sub-receita</th>
                <th>Porções</th>
              </tr>
            </thead>
            <tbody>
              {recipe.sub_recipes.map(sr => (
                <tr key={sr.id}>
                  <td style={{ fontWeight: 600 }}>🔗 {sr.sub_recipe_name}</td>
                  <td>{fmtQty(sr.portions)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

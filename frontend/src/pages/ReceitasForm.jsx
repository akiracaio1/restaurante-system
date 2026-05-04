import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { receitasAPI, ingredientesAPI } from '../api'

const CATEGORIES = [
  'prato principal',
  'sobremesa',
  'bebida',
  'entrada',
  'petisco',
  'outro',
]

const EMPTY_FORM = {
  name: '', description: '', category: 'prato principal',
  sale_price: '', yield_portions: '1',
}

const fmt    = (v) => `R$ ${Number(v).toFixed(2).replace('.', ',')}`
const fmtPct = (v) => `${Number(v).toFixed(1)}%`

function cmvClass(v) {
  if (v <= 30) return 'cmv-good'
  if (v <= 35) return 'cmv-ok'
  if (v <= 40) return 'cmv-warning'
  return 'cmv-bad'
}

function cmvLabel(v) {
  if (v <= 30) return '🟢 Excelente'
  if (v <= 35) return '🟡 Aceitável'
  if (v <= 40) return '🟠 Atenção'
  return '🔴 Alto — revise'
}

export default function ReceitasForm() {
  const { id }   = useParams()
  const navigate = useNavigate()
  const isEdit   = Boolean(id)

  const [form, setForm]                   = useState(EMPTY_FORM)
  const [selectedIngs, setSelectedIngs]   = useState([])
  const [availableIngs, setAvailableIngs] = useState([])
  const [addIngId, setAddIngId]           = useState('')
  const [addQty, setAddQty]               = useState('')

  const [subRecipesList, setSubRecipesList]     = useState([])
  const [removedEntryIds, setRemovedEntryIds]   = useState([])
  const [availableRecipes, setAvailableRecipes] = useState([])
  const [addSubRecipeId, setAddSubRecipeId]     = useState('')
  const [addSubPortions, setAddSubPortions]     = useState('')

  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [error, setError]     = useState('')

  useEffect(() => {
    async function init() {
      try {
        const [{ data: ings }, { data: recipes }] = await Promise.all([
          ingredientesAPI.listar(),
          receitasAPI.listar(),
        ])
        setAvailableIngs(ings)
        if (ings.length > 0) setAddIngId(String(ings[0].id))

        const selectable = isEdit ? recipes.filter(r => r.id !== Number(id)) : recipes
        setAvailableRecipes(selectable)
        if (selectable.length > 0) setAddSubRecipeId(String(selectable[0].id))

        if (isEdit) {
          const { data: recipe } = await receitasAPI.buscar(id)
          setForm({
            name:           recipe.name,
            description:    recipe.description || '',
            category:       recipe.category,
            sale_price:     String(recipe.sale_price),
            yield_portions: String(recipe.yield_portions),
          })
          setSelectedIngs(
            recipe.ingredients.map(ri => ({
              ingredient_id: ri.ingredient_id,
              quantity:      ri.quantity,
              ing:           ings.find(i => i.id === ri.ingredient_id),
            }))
          )
          setSubRecipesList(
            (recipe.sub_recipes || []).map(sr => ({
              entryId:         sr.id,
              sub_recipe_id:   sr.sub_recipe_id,
              sub_recipe_name: sr.sub_recipe_name,
              portions:        sr.portions,
              cost_per_portion: sr.cost_per_portion,
            }))
          )
        }
      } catch {
        setError('Erro ao carregar dados.')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [id])

  const handle = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  function addIngredient() {
    const ingId = Number(addIngId)
    const qty   = Number(addQty)
    if (!ingId || !addQty || isNaN(qty) || qty <= 0) return
    const ing = availableIngs.find(i => i.id === ingId)
    if (!ing) return
    setSelectedIngs(prev => {
      const exists = prev.find(i => i.ingredient_id === ingId)
      if (exists) return prev.map(i => i.ingredient_id === ingId ? { ...i, quantity: qty } : i)
      return [...prev, { ingredient_id: ingId, quantity: qty, ing }]
    })
    setAddQty('')
  }

  function removeIngredient(ingId) {
    setSelectedIngs(prev => prev.filter(i => i.ingredient_id !== ingId))
  }

  function addSubRecipe() {
    const recipeId = Number(addSubRecipeId)
    const pts      = Number(addSubPortions)
    if (!recipeId || !addSubPortions || isNaN(pts) || pts <= 0) return
    if (subRecipesList.find(s => s.sub_recipe_id === recipeId)) return
    const recipe = availableRecipes.find(r => r.id === recipeId)
    if (!recipe) return
    const cpp = recipe.yield_portions > 0 ? recipe.total_cost / recipe.yield_portions : 0
    setSubRecipesList(prev => [
      ...prev,
      { entryId: null, sub_recipe_id: recipeId, sub_recipe_name: recipe.name, portions: pts, cost_per_portion: cpp },
    ])
    setAddSubPortions('')
  }

  function removeSubRecipe(subRecipeId) {
    const entry = subRecipesList.find(s => s.sub_recipe_id === subRecipeId)
    if (entry?.entryId) setRemovedEntryIds(prev => [...prev, entry.entryId])
    setSubRecipesList(prev => prev.filter(s => s.sub_recipe_id !== subRecipeId))
  }

  const ingredientsCost = selectedIngs.reduce(
    (sum, si) => sum + (si.ing?.real_unit_cost ?? si.ing?.unit_cost ?? 0) * si.quantity, 0
  )
  const subRecipesCost = subRecipesList.reduce(
    (sum, sr) => sum + sr.cost_per_portion * sr.portions, 0
  )
  const totalCost      = ingredientsCost + subRecipesCost
  const salePrice      = Number(form.sale_price) || 0
  const portions       = Number(form.yield_portions) || 1
  const cmvPercent     = salePrice > 0 ? (totalCost / portions / salePrice) * 100 : 0
  const costPerPortion = totalCost / portions

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!form.name.trim())
      return setError('Nome da receita é obrigatório.')
    if (!form.sale_price || isNaN(form.sale_price) || salePrice <= 0)
      return setError('Preço de venda deve ser maior que zero.')
    if (selectedIngs.length === 0)
      return setError('Adicione pelo menos um ingrediente à receita.')

    const payload = {
      name:           form.name.trim(),
      description:    form.description.trim() || null,
      category:       form.category,
      sale_price:     salePrice,
      yield_portions: portions,
      ingredients:    selectedIngs.map(si => ({
        ingredient_id: si.ingredient_id,
        quantity:      si.quantity,
      })),
    }

    try {
      setSaving(true)
      let savedId = id
      if (isEdit) {
        await receitasAPI.atualizar(id, payload)
      } else {
        const { data: created } = await receitasAPI.criar(payload)
        savedId = created.id
      }

      for (const entryId of removedEntryIds) {
        await receitasAPI.removerSubReceita(savedId, entryId)
      }
      for (const sr of subRecipesList.filter(s => s.entryId === null)) {
        await receitasAPI.adicionarSubReceita(savedId, { sub_recipe_id: sr.sub_recipe_id, portions: sr.portions })
      }

      navigate('/receitas')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar receita.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="loading">Carregando…</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">{isEdit ? 'Editar Receita' : 'Nova Receita'}</h1>
          <p className="page-subtitle">
            {isEdit ? 'Atualize as informações da receita' : 'Preencha os dados da nova receita'}
          </p>
        </div>
        <Link to="/receitas" className="btn btn-ghost">← Voltar</Link>
      </div>

      <div className="form-card" style={{ maxWidth: '860px' }}>
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={submit}>
          {/* ── Info geral ─────────────────────────────────── */}
          <p className="section-title">Informações Gerais</p>

          <div className="form-grid" style={{ marginBottom: '1rem' }}>
            <div className="form-group full">
              <label htmlFor="name">Nome da Receita *</label>
              <input
                id="name"
                name="name"
                value={form.name}
                onChange={handle}
                placeholder="Ex: Strogonoff de frango"
                autoFocus
                className={form.name.trim() ? 'valid' : ''}
              />
            </div>

            <div className="form-group full">
              <label htmlFor="description">Descrição</label>
              <textarea
                id="description"
                name="description"
                value={form.description}
                onChange={handle}
                placeholder="Descrição opcional da receita..."
                rows={2}
              />
            </div>

            <div className="form-group">
              <label htmlFor="category">Categoria *</label>
              <select id="category" name="category" value={form.category} onChange={handle}>
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="sale_price">Preço de Venda (R$) *</label>
              <input
                id="sale_price"
                name="sale_price"
                type="number"
                step="0.01"
                min="0.01"
                value={form.sale_price}
                onChange={handle}
                placeholder="0,00"
                className={salePrice > 0 ? 'valid' : ''}
              />
            </div>

            <div className="form-group">
              <label htmlFor="yield_portions">Rendimento (porções) *</label>
              <input
                id="yield_portions"
                name="yield_portions"
                type="number"
                step="1"
                min="1"
                value={form.yield_portions}
                onChange={handle}
              />
            </div>
          </div>

          {/* ── Ingredientes ───────────────────────────────── */}
          <p className="section-title">Ingredientes da Receita</p>

          {availableIngs.length === 0 ? (
            <div className="alert alert-error">
              Nenhum ingrediente cadastrado.{' '}
              <Link to="/ingredientes/novo" style={{ color: 'inherit', fontWeight: 700 }}>
                Cadastre ingredientes
              </Link>{' '}
              antes de criar uma receita.
            </div>
          ) : (
            <>
              <div className="add-box">
                <p className="add-box-label">Adicionar ingrediente</p>
                <div className="add-row">
                  <div className="form-group" style={{ margin: 0 }}>
                    <select value={addIngId} onChange={e => setAddIngId(e.target.value)}>
                      {availableIngs.map(i => (
                        <option key={i.id} value={i.id}>
                          {i.name} ({i.unit})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ margin: 0 }}>
                    <input
                      type="number"
                      step="0.001"
                      min="0.001"
                      value={addQty}
                      onChange={e => setAddQty(e.target.value)}
                      placeholder="Quantidade"
                      onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addIngredient())}
                    />
                  </div>
                  <button type="button" className="btn btn-secondary" onClick={addIngredient}>
                    + Adicionar
                  </button>
                </div>
              </div>

              {selectedIngs.length > 0 && (
                <table className="ing-table">
                  <thead>
                    <tr>
                      <th>Ingrediente</th>
                      <th>Quantidade</th>
                      <th>Custo Unit.</th>
                      <th>Subtotal</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedIngs.map(si => {
                      const realCost = si.ing?.real_unit_cost ?? si.ing?.unit_cost ?? 0
                      const subtotal = realCost * si.quantity
                      return (
                        <tr key={si.ingredient_id}>
                          <td style={{ fontWeight: 600 }}>{si.ing?.name}</td>
                          <td>{si.quantity} {si.ing?.unit}</td>
                          <td>{fmt(realCost)} / {si.ing?.unit}</td>
                          <td style={{ fontWeight: 700 }}>{fmt(subtotal)}</td>
                          <td>
                            <button
                              type="button"
                              className="btn btn-sm btn-danger btn-icon-only"
                              onClick={() => removeIngredient(si.ingredient_id)}
                            >
                              ✕
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}
            </>
          )}

          {/* ── Sub-receitas ────────────────────────────────── */}
          <p className="section-title">Sub-receitas</p>

          {availableRecipes.length === 0 ? (
            <div className="alert" style={{ background: 'var(--surface)', color: 'var(--muted)', border: '1px solid var(--border)', marginBottom: '1rem' }}>
              {isEdit
                ? 'Nenhuma outra receita disponível para usar como sub-receita.'
                : 'Nenhuma receita disponível para usar como sub-receita.'}
            </div>
          ) : (
            <>
              <div className="add-box">
                <p className="add-box-label">Adicionar sub-receita</p>
                <div className="add-row">
                  <div className="form-group" style={{ margin: 0 }}>
                    <select value={addSubRecipeId} onChange={e => setAddSubRecipeId(e.target.value)}>
                      {availableRecipes.map(r => (
                        <option key={r.id} value={r.id}>{r.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ margin: 0 }}>
                    <input
                      type="number"
                      step="0.5"
                      min="0.5"
                      value={addSubPortions}
                      onChange={e => setAddSubPortions(e.target.value)}
                      placeholder="Porções"
                      onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addSubRecipe())}
                    />
                  </div>
                  <button type="button" className="btn btn-secondary" onClick={addSubRecipe}>
                    + Adicionar
                  </button>
                </div>
              </div>

              {subRecipesList.length > 0 && (
                <table className="ing-table">
                  <thead>
                    <tr>
                      <th>Receita</th>
                      <th>Porções</th>
                      <th>Custo/Porção</th>
                      <th>Subtotal</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {subRecipesList.map(sr => (
                      <tr key={sr.sub_recipe_id}>
                        <td style={{ fontWeight: 600 }}>🔗 {sr.sub_recipe_name}</td>
                        <td>{sr.portions}</td>
                        <td>{fmt(sr.cost_per_portion)}</td>
                        <td style={{ fontWeight: 700 }}>{fmt(sr.cost_per_portion * sr.portions)}</td>
                        <td>
                          <button
                            type="button"
                            className="btn btn-sm btn-danger btn-icon-only"
                            onClick={() => removeSubRecipe(sr.sub_recipe_id)}
                          >
                            ✕
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}

          {/* ── Resumo de Custos ─────────────────────────────── */}
          {(selectedIngs.length > 0 || subRecipesList.length > 0) && (
            <div className="cost-box">
              <p className="cost-box-title">Resumo de Custos</p>
              <div className="cost-grid">
                <div className="cost-item">
                  <span className="cost-label">Custo Total</span>
                  <span className="cost-value">{fmt(totalCost)}</span>
                </div>
                <div className="cost-item">
                  <span className="cost-label">Custo por Porção</span>
                  <span className="cost-value">{fmt(costPerPortion)}</span>
                </div>
                <div className="cost-item">
                  <span className="cost-label">CMV %</span>
                  <span className={`cost-value ${salePrice > 0 ? cmvClass(cmvPercent) : ''}`}>
                    {salePrice > 0 ? fmtPct(cmvPercent) : '—'}
                  </span>
                </div>
              </div>
              {salePrice > 0 && (
                <div style={{
                  marginTop: '.85rem',
                  padding: '.5rem .75rem',
                  background: 'rgba(0,0,0,.04)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '.82rem',
                  fontWeight: 700,
                }}>
                  {cmvLabel(cmvPercent)}
                </div>
              )}
              <p className="cost-hint">
                Referência: &lt;30% excelente · 30–35% aceitável · 35–40% atenção · &gt;40% alto
              </p>
            </div>
          )}

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? '⏳ Salvando…' : isEdit ? '✓ Salvar Alterações' : '✓ Cadastrar Receita'}
            </button>
            <Link to="/receitas" className="btn btn-ghost">Cancelar</Link>
          </div>
        </form>
      </div>
    </div>
  )
}

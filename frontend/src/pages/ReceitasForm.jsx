import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { receitasAPI, ingredientesAPI, canaisAPI, categoriasAPI } from '../api'

const EMPTY_FORM = {
  name: '', description: '', category: '',
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

  const [availableChannels, setAvailableChannels] = useState([])
  const [channelEntries, setChannelEntries]       = useState([])
  const [originalChannelIds, setOriginalChannelIds] = useState(new Set())
  const [removedChannelIds, setRemovedChannelIds] = useState([])
  const [addChannelId, setAddChannelId]           = useState('')

  const [categoryOptions, setCategoryOptions] = useState([])

  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [error, setError]     = useState('')

  useEffect(() => {
    async function init() {
      try {
        const [{ data: ings }, { data: recipes }, { data: channels }, { data: categories }] = await Promise.all([
          ingredientesAPI.listar(),
          receitasAPI.listar(),
          canaisAPI.listar(),
          categoriasAPI.listar(),
        ])
        setAvailableIngs(ings)
        if (ings.length > 0) setAddIngId(String(ings[0].id))

        const selectable = isEdit ? recipes.filter(r => r.id !== Number(id)) : recipes
        setAvailableRecipes(selectable)
        if (selectable.length > 0) setAddSubRecipeId(String(selectable[0].id))

        setAvailableChannels(channels)

        const usedCategoryNames = new Set(recipes.map(r => r.category).filter(Boolean))
        for (const c of categories) usedCategoryNames.add(c.name)
        const categoryList = [...usedCategoryNames].sort((a, b) => a.localeCompare(b))
        setCategoryOptions(categoryList)

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
          setChannelEntries(
            (recipe.channel_prices || []).map(cp => ({
              channel_id:   cp.channel_id,
              channel_name: cp.channel_name,
              fee_percent:  cp.fee_percent,
              fixed_cost:   cp.fixed_cost,
              sale_price:   String(cp.sale_price),
              extraIngredients: cp.extra_ingredients.map(ei => ({
                ingredient_id: ei.ingredient_id,
                quantity:      ei.quantity,
                ing:           ings.find(i => i.id === ei.ingredient_id),
              })),
              pendingIngId: ings.length > 0 ? String(ings[0].id) : '',
              pendingQty:   '',
            }))
          )
          setOriginalChannelIds(new Set((recipe.channel_prices || []).map(cp => cp.channel_id)))
          setRemovedChannelIds([])
        } else if (categoryList.length > 0) {
          setForm(prev => ({ ...prev, category: categoryList[0] }))
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

  function addChannelEntry() {
    const channelId = Number(addChannelId)
    if (!channelId) return
    if (channelEntries.find(e => e.channel_id === channelId)) return
    const channel = availableChannels.find(c => c.id === channelId)
    if (!channel) return
    setChannelEntries(prev => [...prev, {
      channel_id: channelId,
      channel_name: channel.name,
      fee_percent: channel.fee_percent,
      fixed_cost: channel.fixed_cost,
      sale_price: '',
      extraIngredients: [],
      pendingIngId: availableIngs.length > 0 ? String(availableIngs[0].id) : '',
      pendingQty: '',
    }])
  }

  function removeChannelEntry(channelId) {
    if (originalChannelIds.has(channelId)) setRemovedChannelIds(prev => [...prev, channelId])
    setChannelEntries(prev => prev.filter(e => e.channel_id !== channelId))
  }

  function updateChannelEntry(channelId, patch) {
    setChannelEntries(prev => prev.map(e => e.channel_id === channelId ? { ...e, ...patch } : e))
  }

  function addExtraIngredient(channelId) {
    setChannelEntries(prev => prev.map(e => {
      if (e.channel_id !== channelId) return e
      const ingId = Number(e.pendingIngId)
      const qty   = Number(e.pendingQty)
      if (!ingId || !e.pendingQty || isNaN(qty) || qty <= 0) return e
      const ing = availableIngs.find(i => i.id === ingId)
      if (!ing) return e
      const exists = e.extraIngredients.find(x => x.ingredient_id === ingId)
      const extraIngredients = exists
        ? e.extraIngredients.map(x => x.ingredient_id === ingId ? { ...x, quantity: qty } : x)
        : [...e.extraIngredients, { ingredient_id: ingId, quantity: qty, ing }]
      return { ...e, extraIngredients, pendingQty: '' }
    }))
  }

  function removeExtraIngredient(channelId, ingredientId) {
    setChannelEntries(prev => prev.map(e =>
      e.channel_id === channelId
        ? { ...e, extraIngredients: e.extraIngredients.filter(x => x.ingredient_id !== ingredientId) }
        : e
    ))
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

  const usedChannelIds     = new Set(channelEntries.map(e => e.channel_id))
  const selectableChannels = availableChannels.filter(c => !usedChannelIds.has(c.id))

  useEffect(() => {
    if (selectableChannels.length === 0) {
      if (addChannelId !== '') setAddChannelId('')
    } else if (!selectableChannels.find(c => String(c.id) === addChannelId)) {
      setAddChannelId(String(selectableChannels[0].id))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availableChannels, channelEntries])

  function channelTotals(entry) {
    const extraCost = entry.extraIngredients.reduce(
      (sum, x) => sum + (x.ing?.real_unit_cost ?? x.ing?.unit_cost ?? 0) * x.quantity, 0
    )
    const entrySalePrice = Number(entry.sale_price) || 0
    const fee   = entry.fee_percent ? (entry.fee_percent / 100) * entrySalePrice : 0
    const fixed = entry.fixed_cost || 0
    const channelTotalCost = costPerPortion + extraCost + fee + fixed
    const channelCmv = entrySalePrice > 0 ? (channelTotalCost / entrySalePrice) * 100 : 0
    return { extraCost, fee, fixed, totalCost: channelTotalCost, cmv: channelCmv }
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!form.name.trim())
      return setError('Nome da receita é obrigatório.')
    if (!form.category)
      return setError('Categoria é obrigatória.')
    if (!form.sale_price || isNaN(form.sale_price) || salePrice <= 0)
      return setError('Preço de venda deve ser maior que zero.')
    if (selectedIngs.length === 0)
      return setError('Adicione pelo menos um ingrediente à receita.')
    if (channelEntries.some(e => !e.sale_price || isNaN(e.sale_price) || Number(e.sale_price) <= 0))
      return setError('Preencha o preço de venda de todas as modalidades adicionadas, ou remova a que não for usar.')

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

      for (const channelId of removedChannelIds) {
        await receitasAPI.removerPrecoCanal(savedId, channelId)
      }
      for (const entry of channelEntries) {
        await receitasAPI.definirPrecoCanal(savedId, entry.channel_id, {
          sale_price: Number(entry.sale_price),
          extra_ingredients: entry.extraIngredients.map(x => ({
            ingredient_id: x.ingredient_id,
            quantity: x.quantity,
          })),
        })
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
              <label htmlFor="category">
                Categoria *{' '}
                <Link to="/categorias" style={{ fontSize: '.75rem', fontWeight: 600, color: 'var(--muted)' }}>
                  ⚙️ gerenciar
                </Link>
              </label>
              {categoryOptions.length === 0 ? (
                <div className="alert alert-error" style={{ margin: 0 }}>
                  Nenhuma categoria cadastrada.{' '}
                  <Link to="/categorias" style={{ color: 'inherit', fontWeight: 700 }}>
                    Cadastre uma categoria
                  </Link>{' '}
                  antes de criar a receita.
                </div>
              ) : (
                <select id="category" name="category" value={form.category} onChange={handle}>
                  {categoryOptions.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              )}
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

          {/* ── Modalidades de Venda ─────────────────────────── */}
          <p className="section-title">
            Modalidades de Venda{' '}
            <Link to="/canais" style={{ fontSize: '.75rem', fontWeight: 600, color: 'var(--muted)', textTransform: 'none', letterSpacing: 'normal' }}>
              ⚙️ gerenciar canais
            </Link>
          </p>

          {availableChannels.length === 0 ? (
            <div className="alert" style={{ background: 'var(--surface)', color: 'var(--muted)', border: '1px solid var(--border)', marginBottom: '1rem' }}>
              Nenhum canal de venda cadastrado.{' '}
              <Link to="/canais" style={{ color: 'inherit', fontWeight: 700 }}>
                Cadastre canais
              </Link>{' '}
              (iFood, 99Food, Revenda...) para calcular o custo e o CMV por modalidade.
            </div>
          ) : (
            <>
              {selectableChannels.length > 0 && (
                <div className="add-box">
                  <p className="add-box-label">Adicionar modalidade</p>
                  <div className="add-row">
                    <div className="form-group" style={{ margin: 0 }}>
                      <select value={addChannelId} onChange={e => setAddChannelId(e.target.value)}>
                        {selectableChannels.map(c => (
                          <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                      </select>
                    </div>
                    <button type="button" className="btn btn-secondary" onClick={addChannelEntry}>
                      + Adicionar
                    </button>
                  </div>
                </div>
              )}

              {channelEntries.map(entry => {
                const t = channelTotals(entry)
                const entrySalePrice = Number(entry.sale_price) || 0
                return (
                  <div key={entry.channel_id} className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '.75rem' }}>
                      <div>
                        <strong>{entry.channel_name}</strong>
                        <div style={{ fontSize: '.78rem', color: 'var(--muted)' }}>
                          {entry.fee_percent ? `Taxa: ${entry.fee_percent}%` : ''}
                          {entry.fee_percent && entry.fixed_cost ? ' · ' : ''}
                          {entry.fixed_cost ? `Custo fixo: ${fmt(entry.fixed_cost)}` : ''}
                          {!entry.fee_percent && !entry.fixed_cost ? 'Sem taxas configuradas' : ''}
                        </div>
                      </div>
                      <button
                        type="button"
                        className="btn btn-sm btn-danger btn-icon-only"
                        onClick={() => removeChannelEntry(entry.channel_id)}
                      >
                        ✕
                      </button>
                    </div>

                    <div className="form-group" style={{ maxWidth: '220px' }}>
                      <label>Preço de venda nesta modalidade (R$) *</label>
                      <input
                        type="number"
                        step="0.01"
                        min="0.01"
                        value={entry.sale_price}
                        onChange={e => updateChannelEntry(entry.channel_id, { sale_price: e.target.value })}
                        placeholder="0,00"
                        className={entrySalePrice > 0 ? 'valid' : ''}
                      />
                    </div>

                    <p className="add-box-label" style={{ marginTop: '.75rem' }}>Custos extras desta modalidade (ex: embalagem)</p>
                    <div className="add-row">
                      <div className="form-group" style={{ margin: 0 }}>
                        <select
                          value={entry.pendingIngId}
                          onChange={e => updateChannelEntry(entry.channel_id, { pendingIngId: e.target.value })}
                        >
                          {availableIngs.map(i => (
                            <option key={i.id} value={i.id}>{i.name} ({i.unit})</option>
                          ))}
                        </select>
                      </div>
                      <div className="form-group" style={{ margin: 0 }}>
                        <input
                          type="number"
                          step="0.001"
                          min="0.001"
                          value={entry.pendingQty}
                          onChange={e => updateChannelEntry(entry.channel_id, { pendingQty: e.target.value })}
                          placeholder="Quantidade"
                          onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addExtraIngredient(entry.channel_id))}
                        />
                      </div>
                      <button type="button" className="btn btn-secondary" onClick={() => addExtraIngredient(entry.channel_id)}>
                        + Adicionar
                      </button>
                    </div>

                    {entry.extraIngredients.length > 0 && (
                      <table className="ing-table">
                        <thead>
                          <tr>
                            <th>Ingrediente</th>
                            <th>Quantidade</th>
                            <th>Subtotal</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {entry.extraIngredients.map(x => {
                            const realCost = x.ing?.real_unit_cost ?? x.ing?.unit_cost ?? 0
                            return (
                              <tr key={x.ingredient_id}>
                                <td style={{ fontWeight: 600 }}>{x.ing?.name}</td>
                                <td>{x.quantity} {x.ing?.unit}</td>
                                <td style={{ fontWeight: 700 }}>{fmt(realCost * x.quantity)}</td>
                                <td>
                                  <button
                                    type="button"
                                    className="btn btn-sm btn-danger btn-icon-only"
                                    onClick={() => removeExtraIngredient(entry.channel_id, x.ingredient_id)}
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

                    <div style={{
                      marginTop: '.85rem',
                      padding: '.6rem .8rem',
                      background: 'rgba(0,0,0,.03)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '.82rem',
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '.4rem 1rem',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}>
                      <span style={{ color: 'var(--muted)' }}>
                        Custo base {fmt(costPerPortion)} + extras {fmt(t.extraCost)} + taxa {fmt(t.fee)} + fixo {fmt(t.fixed)} = <strong>{fmt(t.totalCost)}</strong>
                      </span>
                      <span className={entrySalePrice > 0 ? cmvClass(t.cmv) : ''} style={{ fontWeight: 800 }}>
                        {entrySalePrice > 0 ? `CMV ${fmtPct(t.cmv)}` : 'Defina o preço de venda'}
                      </span>
                    </div>
                  </div>
                )
              })}
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

import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { comprasAPI, ingredientesAPI, fornecedoresAPI } from '../api'

const fmt = (v, d = 4) => `R$ ${Number(v).toFixed(d).replace('.', ',')}`

const CONVERSIONS = { 'kg→g': 1000, 'g→kg': 0.001, 'L→ml': 1000, 'ml→L': 0.001 }

function convertToBase(qty, fromUnit, toUnit) {
  if (fromUnit === toUnit) return { qty, factor: null }
  const key = `${fromUnit}→${toUnit}`
  const factor = CONVERSIONS[key]
  if (factor != null) return { qty: qty * factor, factor }
  return { qty, factor: null }
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

export default function ComprasForm() {
  const navigate = useNavigate()

  const [form, setForm]           = useState({ date: today(), supplier_id: '', notes: '', tax: '', freight: '' })
  const [suppliers, setSuppliers] = useState([])
  const [ingredients, setIngredients] = useState([])
  const [items, setItems]         = useState([])
  const [addIngId, setAddIngId]   = useState('')
  const [addQty, setAddQty]       = useState('')
  const [addUnit, setAddUnit]     = useState('')
  const [addTotal, setAddTotal]   = useState('')
  const [loading, setLoading]     = useState(true)
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')

  useEffect(() => {
    async function init() {
      try {
        const [{ data: ings }, { data: sups }] = await Promise.all([
          ingredientesAPI.listar(),
          fornecedoresAPI.listar(),
        ])
        setIngredients(ings)
        setSuppliers(sups)
        if (ings.length > 0) {
          setAddIngId(String(ings[0].id))
          setAddUnit(ings[0].purchase_unit || ings[0].unit)
        }
      } catch {
        setError('Erro ao carregar dados.')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const handle = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  function handleIngChange(e) {
    const id = e.target.value
    setAddIngId(id)
    const ing = ingredients.find(i => String(i.id) === id)
    if (ing) setAddUnit(ing.purchase_unit || ing.unit)
  }

  function addItem() {
    const qty   = Number(addQty)
    const total = Number(addTotal)
    const ingId = Number(addIngId)
    if (!ingId || qty <= 0 || total <= 0) return
    const ing = ingredients.find(i => i.id === ingId)
    if (!ing) return

    const { qty: qtyBase, factor } = convertToBase(qty, addUnit, ing.unit)
    const unitCost = total / qtyBase

    setItems(prev => {
      const exists = prev.find(i => i.ingredient_id === ingId)
      if (exists) {
        return prev.map(i => i.ingredient_id === ingId
          ? { ...i, quantity: qty, unit: addUnit, total_price: total, unit_cost: unitCost, qtyBase, convFactor: factor }
          : i
        )
      }
      return [...prev, { ingredient_id: ingId, quantity: qty, unit: addUnit, total_price: total, unit_cost: unitCost, qtyBase, convFactor: factor, ing }]
    })
    setAddQty('')
    setAddTotal('')
  }

  function removeItem(ingId) {
    setItems(prev => prev.filter(i => i.ingredient_id !== ingId))
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!form.date) return setError('Data é obrigatória.')
    if (items.length === 0) return setError('Adicione pelo menos um item à compra.')

    const payload = {
      date: form.date,
      supplier_id: form.supplier_id ? Number(form.supplier_id) : null,
      notes: form.notes.trim() || null,
      tax: Number(form.tax) || 0,
      freight: Number(form.freight) || 0,
      items: items.map(i => ({
        ingredient_id: i.ingredient_id,
        quantity: i.quantity,
        unit: i.unit,
        total_price: i.total_price,
        notes: null,
      })),
    }
    try {
      setSaving(true)
      await comprasAPI.criar(payload)
      navigate('/compras')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar compra.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="loading">Carregando…</div>

  const selectedIng = ingredients.find(i => String(i.id) === addIngId)
  let newUnitCost = null
  let conversionNote = null
  if (selectedIng && Number(addQty) > 0 && Number(addTotal) > 0) {
    const qty = Number(addQty)
    const total = Number(addTotal)
    const { qty: qtyBase, factor } = convertToBase(qty, addUnit, selectedIng.unit)
    newUnitCost = total / qtyBase
    if (factor !== null) {
      conversionNote = `${qty} ${addUnit} = ${qtyBase}${selectedIng.unit}`
    }
  }
  const subtotal    = items.reduce((s, i) => s + i.total_price, 0)
  const taxVal      = Number(form.tax) || 0
  const freightVal  = Number(form.freight) || 0
  const extraPool   = taxVal + freightVal
  const grandTotal  = subtotal + extraPool

  function dilutedUnitCost(item) {
    const ratio = subtotal > 0 ? item.total_price / subtotal : 1 / items.length
    const allocated = ratio * extraPool
    return (item.total_price + allocated) / item.qtyBase
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🛒 Nova Compra</h1>
          <p className="page-subtitle">Registre uma nota de compra e atualize o estoque</p>
        </div>
        <Link to="/compras" className="btn btn-ghost">← Voltar</Link>
      </div>

      <div className="form-card" style={{ maxWidth: '860px' }}>
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={submit}>
          <p className="section-title">Informações da Nota</p>

          <div className="form-grid" style={{ marginBottom: '1rem' }}>
            <div className="form-group">
              <label htmlFor="date">Data *</label>
              <input id="date" name="date" type="date" value={form.date} onChange={handle} />
            </div>
            <div className="form-group">
              <label htmlFor="supplier_id">
                Fornecedor{' '}
                <Link to="/fornecedores" style={{ fontSize: '.75rem', fontWeight: 600, color: 'var(--muted)' }}>
                  ⚙️ gerenciar
                </Link>
              </label>
              <select id="supplier_id" name="supplier_id" value={form.supplier_id} onChange={handle}>
                <option value="">— Nenhum —</option>
                {suppliers.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="tax">Imposto (R$)</label>
              <input
                id="tax" name="tax" type="number" step="0.01" min="0"
                value={form.tax} onChange={handle} placeholder="0,00"
              />
            </div>
            <div className="form-group">
              <label htmlFor="freight">Frete (R$)</label>
              <input
                id="freight" name="freight" type="number" step="0.01" min="0"
                value={form.freight} onChange={handle} placeholder="0,00"
              />
            </div>
            <div className="form-group full">
              <label htmlFor="notes">Observações</label>
              <textarea id="notes" name="notes" value={form.notes} onChange={handle} rows={2} placeholder="Observações opcionais…" />
            </div>
          </div>
          {(Number(form.tax) > 0 || Number(form.freight) > 0) && (
            <div className="alert" style={{ background: 'var(--surface)', color: 'var(--muted)', border: '1px solid var(--border)', marginBottom: '1rem', fontSize: '.84rem' }}>
              Imposto e frete são diluídos no custo de cada item, proporcionalmente ao valor de cada um dentro da compra.
            </div>
          )}

          <p className="section-title">Itens da Compra</p>

          {ingredients.length === 0 ? (
            <div className="alert alert-error">
              Nenhum ingrediente cadastrado.{' '}
              <Link to="/ingredientes/novo" style={{ color: 'inherit', fontWeight: 700 }}>
                Cadastre ingredientes
              </Link>{' '}
              antes de registrar uma compra.
            </div>
          ) : (
            <>
              <div className="add-box">
                <p className="add-box-label">Adicionar item</p>
                <div className="add-row" style={{ flexWrap: 'wrap', gap: '.5rem' }}>
                  <div className="form-group" style={{ margin: 0, minWidth: '180px' }}>
                    <select value={addIngId} onChange={handleIngChange}>
                      {ingredients.map(i => (
                        <option key={i.id} value={i.id}>{i.name} ({i.unit})</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ margin: 0, maxWidth: '110px' }}>
                    <input
                      type="number"
                      step="0.001"
                      min="0.001"
                      value={addQty}
                      onChange={e => setAddQty(e.target.value)}
                      placeholder="Quantidade"
                    />
                  </div>
                  <div className="form-group" style={{ margin: 0, maxWidth: '90px' }}>
                    <input
                      type="text"
                      value={addUnit}
                      onChange={e => setAddUnit(e.target.value)}
                      placeholder="Unidade"
                    />
                  </div>
                  <div className="form-group" style={{ margin: 0, maxWidth: '130px' }}>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={addTotal}
                      onChange={e => setAddTotal(e.target.value)}
                      placeholder="Total R$"
                    />
                  </div>
                  <button type="button" className="btn btn-secondary" onClick={addItem}>
                    + Adicionar
                  </button>
                </div>

                {selectedIng && newUnitCost !== null && (
                  <div style={{ marginTop: '.6rem', fontSize: '.84rem', display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                    {conversionNote && (
                      <span style={{ color: 'var(--muted)' }}>{conversionNote} →</span>
                    )}
                    <span>
                      Custo novo: <strong style={{ color: 'var(--orange)' }}>{fmt(newUnitCost)}/{selectedIng.unit}</strong>
                    </span>
                    <span>
                      Custo atual: <strong>{fmt(selectedIng.unit_cost)}/{selectedIng.unit}</strong>
                    </span>
                    {Math.abs(newUnitCost - selectedIng.unit_cost) > 0.0001 && (
                      <span style={{ color: newUnitCost > selectedIng.unit_cost ? '#e74c3c' : '#27ae60', fontWeight: 700 }}>
                        {newUnitCost > selectedIng.unit_cost ? '▲' : '▼'}{' '}
                        {(Math.abs(newUnitCost - selectedIng.unit_cost) / selectedIng.unit_cost * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                )}
              </div>

              {items.length > 0 && (
                <table className="ing-table">
                  <thead>
                    <tr>
                      <th>Ingrediente</th>
                      <th>Qtd</th>
                      <th>Unidade</th>
                      <th>Total</th>
                      {extraPool > 0 && <th>+ Imposto/Frete</th>}
                      <th>Custo Novo</th>
                      <th>Custo Anterior</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map(item => {
                      const ratio = subtotal > 0 ? item.total_price / subtotal : 1 / items.length
                      const allocated = ratio * extraPool
                      const diluted = dilutedUnitCost(item)
                      return (
                        <tr key={item.ingredient_id}>
                          <td style={{ fontWeight: 600 }}>{item.ing.name}</td>
                          <td>{item.quantity}</td>
                          <td>{item.unit}</td>
                          <td>{fmt(item.total_price, 2)}</td>
                          {extraPool > 0 && (
                            <td style={{ color: 'var(--muted)' }}>+ {fmt(allocated, 2)}</td>
                          )}
                          <td style={{ color: 'var(--orange)', fontWeight: 600 }}>{fmt(diluted)}/{item.ing.unit}</td>
                          <td style={{ color: 'var(--muted)' }}>{fmt(item.ing.unit_cost)}/{item.ing.unit}</td>
                          <td>
                            <button
                              type="button"
                              className="btn btn-sm btn-danger btn-icon-only"
                              onClick={() => removeItem(item.ingredient_id)}
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

              {items.length > 0 && (
                <div className="cost-box" style={{ marginTop: '1rem' }}>
                  <p className="cost-box-title">Resumo da Compra</p>
                  <div className="cost-grid">
                    <div className="cost-item">
                      <span className="cost-label">Itens</span>
                      <span className="cost-value">{items.length}</span>
                    </div>
                    <div className="cost-item">
                      <span className="cost-label">Subtotal</span>
                      <span className="cost-value">{fmt(subtotal, 2)}</span>
                    </div>
                    {taxVal > 0 && (
                      <div className="cost-item">
                        <span className="cost-label">Imposto</span>
                        <span className="cost-value">{fmt(taxVal, 2)}</span>
                      </div>
                    )}
                    {freightVal > 0 && (
                      <div className="cost-item">
                        <span className="cost-label">Frete</span>
                        <span className="cost-value">{fmt(freightVal, 2)}</span>
                      </div>
                    )}
                    <div className="cost-item">
                      <span className="cost-label">Total Gasto</span>
                      <span className="cost-value">{fmt(grandTotal, 2)}</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? '⏳ Salvando…' : '✓ Registrar Compra'}
            </button>
            <Link to="/compras" className="btn btn-ghost">Cancelar</Link>
          </div>
        </form>
      </div>
    </div>
  )
}

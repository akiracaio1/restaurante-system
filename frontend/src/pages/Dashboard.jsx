import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ingredientesAPI, receitasAPI, estoqueAPI } from '../api'
import { useAuth } from '../context/AuthContext'

const fmt    = (v) => `R$ ${Number(v).toFixed(2).replace('.', ',')}`
const fmtPct = (v) => `${Number(v).toFixed(1)}%`

const CAT_ICON = {
  'prato principal': '🍽️',
  'sobremesa':       '🍰',
  'bebida':          '🥤',
  'entrada':         '🥗',
  'petisco':         '🍟',
  'outro':           '📦',
}

function cmvBadgeClass(v) {
  if (v <= 30) return 'badge-green'
  if (v <= 35) return 'badge-orange'
  if (v <= 40) return 'badge-warning'
  return 'badge-red'
}

function cmvTextClass(v) {
  if (v <= 30) return 'cmv-good-text'
  if (v <= 35) return 'cmv-ok-text'
  if (v <= 40) return 'cmv-warn-text'
  return 'cmv-bad-text'
}

function cmvLabel(v) {
  if (v <= 30) return 'Excelente'
  if (v <= 35) return 'Aceitável'
  if (v <= 40) return 'Atenção'
  return 'Alto'
}

export default function Dashboard() {
  const { email } = useAuth()
  const [ingredientes, setIngredientes] = useState([])
  const [receitas, setReceitas] = useState([])
  const [lowStock, setLowStock] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // O aviso de estoque é opcional: se falhar, o resto do dashboard continua funcionando.
    const emptyList = () => ({ data: [] })
    Promise.all([
      ingredientesAPI.listar(),
      receitasAPI.listar(),
      estoqueAPI.listarReceitas().catch(emptyList),
      estoqueAPI.listar().catch(emptyList),
    ])
      .then(([{ data: ings }, { data: recs }, { data: recStock }, { data: ingStock }]) => {
        setIngredientes(ings)
        setReceitas(recs)
        const low = (qty, min) => (min ?? 0) > 0 && qty < min
        setLowStock([
          ...recStock.filter(r => low(r.quantity, r.min_stock))
            .map(r => ({ key: `r${r.recipe_id}`, name: r.recipe_name, qty: r.quantity, min: r.min_stock, unit: r.unit })),
          ...ingStock.filter(i => low(i.quantity, i.min_stock))
            .map(i => ({ key: `i${i.ingredient_id}`, name: i.ingredient_name, qty: i.quantity, min: i.min_stock, unit: i.unit })),
        ])
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading">Carregando dashboard…</div>

  const comCMV  = receitas.filter(r => r.cmv_percent != null)
  const avgCMV  = comCMV.length > 0
    ? comCMV.reduce((s, r) => s + r.cmv_percent, 0) / comCMV.length
    : null
  const melhor  = comCMV.length > 0 ? comCMV.reduce((a, b) => b.cmv_percent < a.cmv_percent ? b : a) : null
  const pior    = comCMV.length > 0 ? comCMV.reduce((a, b) => b.cmv_percent > a.cmv_percent ? b : a) : null
  const ultimas = [...receitas].slice(-5).reverse()

  const firstName = email ? email.split('@')[0] : 'Chef'

  return (
    <div className="dashboard">
      {/* Welcome + quick actions */}
      <div className="dashboard-welcome">
        <div>
          <h1 className="dashboard-title">Olá, {firstName}! 👋</h1>
          <p className="dashboard-subtitle">Aqui está um resumo do seu restaurante</p>
        </div>
        <div className="dashboard-quick-actions">
          <Link to="/ingredientes/novo" className="btn btn-ghost btn-sm">+ Ingrediente</Link>
          <Link to="/receitas/nova" className="btn btn-primary">+ Nova Receita</Link>
        </div>
      </div>

      {/* Stat cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">🥬</div>
          <div className="stat-body">
            <div className="stat-value">{ingredientes.length}</div>
            <div className="stat-label">Ingredientes cadastrados</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🍳</div>
          <div className="stat-body">
            <div className="stat-value">{receitas.length}</div>
            <div className="stat-label">Receitas no cardápio</div>
          </div>
        </div>

        <div className={`stat-card ${avgCMV == null ? '' : avgCMV <= 30 ? '' : avgCMV <= 35 ? 'accent' : 'danger'}`}>
          <div className="stat-icon">📊</div>
          <div className="stat-body">
            {avgCMV != null ? (
              <>
                <div className={`stat-value ${cmvTextClass(avgCMV)}`}>{fmtPct(avgCMV)}</div>
                <div className="stat-label">CMV médio — <strong>{cmvLabel(avgCMV)}</strong></div>
              </>
            ) : (
              <>
                <div className="stat-value" style={{ color: 'var(--muted)' }}>—</div>
                <div className="stat-label">CMV médio</div>
              </>
            )}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🏆</div>
          <div className="stat-body">
            {melhor ? (
              <>
                <div className="stat-value stat-value-sm">{melhor.name}</div>
                <div className="stat-label">
                  Menor CMV:&nbsp;
                  <span className={`badge ${cmvBadgeClass(melhor.cmv_percent)}`}>
                    {fmtPct(melhor.cmv_percent)}
                  </span>
                </div>
              </>
            ) : (
              <>
                <div className="stat-value" style={{ color: 'var(--muted)', fontSize: '1.4rem' }}>—</div>
                <div className="stat-label">Melhor CMV</div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Alerta de CMV alto */}
      {pior && pior.cmv_percent > 40 && (
        <div className="alert alert-error" style={{ marginBottom: 0 }}>
          ⚠️ <strong>{pior.name}</strong> tem CMV de{' '}
          <strong>{fmtPct(pior.cmv_percent)}</strong> — revise a precificação!
        </div>
      )}

      {/* Alerta de estoque abaixo do mínimo */}
      {lowStock.length > 0 && (
        <div className="alert alert-error" style={{ marginBottom: 0 }}>
          ⚠️ <strong>Estoque abaixo do mínimo:</strong>{' '}
          {lowStock.slice(0, 6).map(s => `${s.name} (${Number(s.qty).toFixed(1).replace('.', ',')} de ${Number(s.min).toFixed(1).replace('.', ',')} ${s.unit})`).join(' · ')}
          {lowStock.length > 6 && ` · e mais ${lowStock.length - 6}`}{' '}
          <Link to="/estoque" style={{ color: 'inherit', fontWeight: 700 }}>Ver estoque →</Link>
        </div>
      )}

      {/* Últimas receitas */}
      <div className="dashboard-section">
        <div className="dashboard-section-header">
          <h2 className="section-heading">Últimas Receitas</h2>
          <Link to="/receitas" className="link-ver-todas">Ver todas →</Link>
        </div>

        {ultimas.length === 0 ? (
          <div className="empty-state" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}>
            <span className="empty-icon">📋</span>
            <p className="empty-text">Nenhuma receita cadastrada</p>
            <p className="empty-sub">
              <Link to="/receitas/nova" style={{ color: 'var(--orange)', fontWeight: 700 }}>
                Crie sua primeira receita
              </Link>
            </p>
          </div>
        ) : (
          <div className="recent-recipes-list">
            {ultimas.map(r => (
              <div key={r.id} className="recent-recipe-card">
                <div className="recent-recipe-info">
                  <div className="recent-recipe-emoji">{CAT_ICON[r.category] || '📦'}</div>
                  <div>
                    <div className="recent-recipe-name">{r.name}</div>
                    <div className="recent-recipe-cat">{r.category}</div>
                  </div>
                </div>
                <div className="recent-recipe-meta">
                  <span className="recent-recipe-price">{fmt(r.sale_price)}</span>
                  {r.cmv_percent != null && (
                    <span className={`badge ${cmvBadgeClass(r.cmv_percent)}`}>
                      {fmtPct(r.cmv_percent)}
                    </span>
                  )}
                  <Link to={`/receitas/${r.id}/editar`} className="btn btn-sm btn-ghost">
                    Editar
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ingredientesAPI, receitasAPI } from '../api'
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
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([ingredientesAPI.listar(), receitasAPI.listar()])
      .then(([{ data: ings }, { data: recs }]) => {
        setIngredientes(ings)
        setReceitas(recs)
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

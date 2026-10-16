import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function PrivateRoute({ children }) {
  const { isAuthenticated, ready } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!ready) return <div className="loading">Carregando…</div>
  return children
}

// Telas financeiras e administrativas. O servidor já recusa o acesso (403) e
// não envia os dados; aqui só evitamos mostrar uma tela vazia ao perfil Operação.
export function MasterRoute({ children }) {
  const { isMaster } = useAuth()
  return isMaster ? children : <Navigate to="/receitas" replace />
}

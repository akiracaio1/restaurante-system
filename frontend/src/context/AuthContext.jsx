import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { authAPI } from '../api'

const AuthContext = createContext(null)

// O perfil é só para ajustar a interface. Quem protege os dados é o servidor:
// ele lê o perfil do banco a cada requisição e nunca confia no que vem daqui.
export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [email, setEmail] = useState(() => localStorage.getItem('userEmail') || '')
  const [role, setRole]   = useState(null)
  const [ready, setReady] = useState(() => !localStorage.getItem('token'))

  useEffect(() => {
    if (!token) {
      setRole(null)
      setReady(true)
      return
    }
    let cancelled = false
    authAPI.me()
      .then(({ data }) => {
        if (cancelled) return
        setRole(data.role)
        setEmail(data.email)
      })
      .catch(() => {
        if (cancelled) return
        setRole(null)
      })
      .finally(() => { if (!cancelled) setReady(true) })
    return () => { cancelled = true }
  }, [token])

  const login = useCallback(async (emailVal, password) => {
    const { data } = await authAPI.login({ email: emailVal, password })
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('userEmail', emailVal)
    setReady(false)
    setRole(data.role || null)
    setToken(data.access_token)
    setEmail(emailVal)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('userEmail')
    setToken(null)
    setRole(null)
    setEmail('')
  }, [])

  return (
    <AuthContext.Provider
      value={{
        token, email, role, ready, login, logout,
        isAuthenticated: !!token,
        isMaster: role === 'master',
        isOperacao: role === 'operacao',
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

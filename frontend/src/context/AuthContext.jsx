import { createContext, useContext, useState, useCallback } from 'react'
import { authAPI } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [email, setEmail] = useState(() => localStorage.getItem('userEmail') || '')

  const login = useCallback(async (emailVal, password) => {
    const { data } = await authAPI.login({ email: emailVal, password })
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('userEmail', emailVal)
    setToken(data.access_token)
    setEmail(emailVal)
  }, [])

  const register = useCallback(async (emailVal, password) => {
    const { data } = await authAPI.register({ email: emailVal, password })
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('userEmail', emailVal)
    setToken(data.access_token)
    setEmail(emailVal)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('userEmail')
    setToken(null)
    setEmail('')
  }, [])

  return (
    <AuthContext.Provider value={{ token, email, login, register, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

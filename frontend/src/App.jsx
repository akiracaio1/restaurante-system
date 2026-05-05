import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import PrivateRoute from './components/PrivateRoute'
import Navbar from './components/Navbar'
import Login from './pages/Login'
import Cadastro from './pages/Cadastro'
import Dashboard from './pages/Dashboard'
import IngredientesLista from './pages/IngredientesLista'
import IngredientesForm from './pages/IngredientesForm'
import ReceitasLista from './pages/ReceitasLista'
import ReceitasForm from './pages/ReceitasForm'
import ComprasLista from './pages/ComprasLista'
import ComprasForm from './pages/ComprasForm'
import EstoqueLista from './pages/EstoqueLista'
import IngredienteHistorico from './pages/IngredienteHistorico'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login"   element={<Login />} />
          <Route path="/cadastro" element={<Cadastro />} />

          <Route
            path="/*"
            element={
              <PrivateRoute>
                <div className="app">
                  <Navbar />
                  <main className="main-content">
                    <Routes>
                      <Route path="/"                                element={<Dashboard />} />
                      <Route path="/ingredientes"                    element={<IngredientesLista />} />
                      <Route path="/ingredientes/novo"               element={<IngredientesForm />} />
                      <Route path="/ingredientes/:id/editar"        element={<IngredientesForm />} />
                      <Route path="/ingredientes/:id/historico"     element={<IngredienteHistorico />} />
                      <Route path="/receitas"                        element={<ReceitasLista />} />
                      <Route path="/receitas/nova"                   element={<ReceitasForm />} />
                      <Route path="/receitas/:id/editar"            element={<ReceitasForm />} />
                      <Route path="/compras"                         element={<ComprasLista />} />
                      <Route path="/compras/nova"                    element={<ComprasForm />} />
                      <Route path="/estoque"                         element={<EstoqueLista />} />
                      <Route path="*"                                element={<Navigate to="/" replace />} />
                    </Routes>
                  </main>
                </div>
              </PrivateRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

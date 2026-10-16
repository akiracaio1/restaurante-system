import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import PrivateRoute, { MasterRoute } from './components/PrivateRoute'
import Navbar from './components/Navbar'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import IngredientesLista from './pages/IngredientesLista'
import IngredientesForm from './pages/IngredientesForm'
import ReceitasLista from './pages/ReceitasLista'
import SubReceitasLista from './pages/SubReceitasLista'
import ReceitasForm from './pages/ReceitasForm'
import ReceitaCalculadora from './pages/ReceitaCalculadora'
import ReceitaDetalhe from './pages/ReceitaDetalhe'
import CanaisLista from './pages/CanaisLista'
import CategoriasLista from './pages/CategoriasLista'
import ComprasLista from './pages/ComprasLista'
import ComprasForm from './pages/ComprasForm'
import FornecedoresLista from './pages/FornecedoresLista'
import FornecedorDetalhe from './pages/FornecedorDetalhe'
import EstoqueLista from './pages/EstoqueLista'
import IngredienteHistorico from './pages/IngredienteHistorico'
import UsuariosLista from './pages/UsuariosLista'

const master = (el) => <MasterRoute>{el}</MasterRoute>

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login"   element={<Login />} />

          <Route
            path="/*"
            element={
              <PrivateRoute>
                <div className="app">
                  <Navbar />
                  <main className="main-content">
                    <Routes>
                      {/* Master e Operação */}
                      <Route path="/ingredientes"              element={<IngredientesLista />} />
                      <Route path="/receitas"                  element={<ReceitasLista />} />
                      <Route path="/receitas/sub-receitas"     element={<SubReceitasLista />} />
                      <Route path="/receitas/:id/calculadora"  element={<ReceitaCalculadora />} />

                      {/* Somente Master */}
                      <Route path="/"                          element={master(<Dashboard />)} />
                      <Route path="/ingredientes/novo"         element={master(<IngredientesForm />)} />
                      <Route path="/ingredientes/:id/editar"   element={master(<IngredientesForm />)} />
                      <Route path="/ingredientes/:id/historico" element={master(<IngredienteHistorico />)} />
                      <Route path="/receitas/nova"             element={master(<ReceitasForm />)} />
                      <Route path="/receitas/:id/editar"       element={master(<ReceitasForm />)} />
                      <Route path="/canais"                    element={master(<CanaisLista />)} />
                      <Route path="/categorias"                element={master(<CategoriasLista />)} />
                      <Route path="/compras"                   element={master(<ComprasLista />)} />
                      <Route path="/compras/nova"              element={master(<ComprasForm />)} />
                      <Route path="/fornecedores"              element={master(<FornecedoresLista />)} />
                      <Route path="/fornecedores/:id"          element={master(<FornecedorDetalhe />)} />
                      <Route path="/estoque"                   element={master(<EstoqueLista />)} />
                      <Route path="/usuarios"                  element={master(<UsuariosLista />)} />

                      {/* Consulta de receita (somente leitura) */}
                      <Route path="/receitas/:id"              element={<ReceitaDetalhe />} />
                      <Route path="*"                          element={<Navigate to="/" replace />} />
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

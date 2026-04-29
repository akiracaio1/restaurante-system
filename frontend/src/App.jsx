import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import PrivateRoute from './components/PrivateRoute'
import Navbar from './components/Navbar'
import Login from './pages/Login'
import Cadastro from './pages/Cadastro'
import IngredientesLista from './pages/IngredientesLista'
import IngredientesForm from './pages/IngredientesForm'
import ReceitasLista from './pages/ReceitasLista'
import ReceitasForm from './pages/ReceitasForm'

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
                      <Route path="/" element={<Navigate to="/ingredientes" replace />} />
                      <Route path="/ingredientes" element={<IngredientesLista />} />
                      <Route path="/ingredientes/novo" element={<IngredientesForm />} />
                      <Route path="/ingredientes/:id/editar" element={<IngredientesForm />} />
                      <Route path="/receitas" element={<ReceitasLista />} />
                      <Route path="/receitas/nova" element={<ReceitasForm />} />
                      <Route path="/receitas/:id/editar" element={<ReceitasForm />} />
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

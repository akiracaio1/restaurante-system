import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import IngredientesLista from './pages/IngredientesLista'
import IngredientesForm from './pages/IngredientesForm'
import ReceitasLista from './pages/ReceitasLista'
import ReceitasForm from './pages/ReceitasForm'

export default function App() {
  return (
    <BrowserRouter>
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
    </BrowserRouter>
  )
}

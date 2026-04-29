import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000/api' })

export const ingredientesAPI = {
  listar: () => api.get('/ingredientes/'),
  buscar: (id) => api.get(`/ingredientes/${id}`),
  criar: (data) => api.post('/ingredientes/', data),
  atualizar: (id, data) => api.put(`/ingredientes/${id}`, data),
  excluir: (id) => api.delete(`/ingredientes/${id}`),
}

export const receitasAPI = {
  listar: () => api.get('/receitas/'),
  buscar: (id) => api.get(`/receitas/${id}`),
  criar: (data) => api.post('/receitas/', data),
  atualizar: (id, data) => api.put(`/receitas/${id}`, data),
  excluir: (id) => api.delete(`/receitas/${id}`),
}

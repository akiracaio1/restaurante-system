import axios from 'axios'

const api = axios.create({ baseURL: 'https://restaurante-system-production-7b07.up.railway.app/api' })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  login:    (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
}

export const ingredientesAPI = {
  listar:    ()         => api.get('/ingredientes/'),
  buscar:    (id)       => api.get(`/ingredientes/${id}`),
  criar:     (data)     => api.post('/ingredientes/', data),
  atualizar: (id, data) => api.put(`/ingredientes/${id}`, data),
  excluir:   (id)       => api.delete(`/ingredientes/${id}`),
}

export const receitasAPI = {
  listar:             ()              => api.get('/receitas/'),
  buscar:             (id)            => api.get(`/receitas/${id}`),
  criar:              (data)          => api.post('/receitas/', data),
  atualizar:          (id, data)      => api.put(`/receitas/${id}`, data),
  excluir:            (id)            => api.delete(`/receitas/${id}`),
  adicionarSubReceita:(id, data)      => api.post(`/receitas/${id}/sub-receitas`, data),
  removerSubReceita:  (id, entryId)   => api.delete(`/receitas/${id}/sub-receitas/${entryId}`),
  definirPrecoCanal:  (id, channelId, data) => api.put(`/receitas/${id}/canais/${channelId}`, data),
  removerPrecoCanal:  (id, channelId)       => api.delete(`/receitas/${id}/canais/${channelId}`),
}

export const canaisAPI = {
  listar:    ()         => api.get('/canais/'),
  criar:     (data)     => api.post('/canais/', data),
  atualizar: (id, data) => api.put(`/canais/${id}`, data),
  excluir:   (id)       => api.delete(`/canais/${id}`),
}

export const comprasAPI = {
  listar:    ()              => api.get('/compras/'),
  buscar:    (id)            => api.get(`/compras/${id}`),
  criar:     (data)          => api.post('/compras/', data),
  excluir:   (id)            => api.delete(`/compras/${id}`),
  historico: (ingredientId)  => api.get(`/compras/historico/${ingredientId}`),
}

export const estoqueAPI = {
  listar:        ()                   => api.get('/estoque/'),
  ajustar:       (ingredientId, data) => api.put(`/estoque/${ingredientId}`, data),
  movimentacoes: (ingredientId)       => api.get(`/estoque/movimentacoes/${ingredientId}`),
}

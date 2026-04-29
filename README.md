# RestaurantePro — Sistema de Gestão de Restaurante

Sistema web de gestão com **FastAPI + SQLite** no backend e **React + Vite** no frontend.

## Estrutura

```
restaurante-system/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── requirements.txt
│   └── routers/
│       ├── ingredients.py
│       └── recipes.py
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── index.css
        ├── api/index.js
        ├── components/Navbar.jsx
        └── pages/
            ├── IngredientesLista.jsx
            ├── IngredientesForm.jsx
            ├── ReceitasLista.jsx
            └── ReceitasForm.jsx
```

---

## Como iniciar

### 1 — Backend (Terminal A)

```bash
cd backend

# Criar e ativar virtualenv
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor
uvicorn main:app --reload
```

A API sobe em **http://localhost:8000**  
Documentação interativa: **http://localhost:8000/docs**

---

### 2 — Frontend (Terminal B)

```bash
cd frontend

npm install
npm run dev
```

A interface sobe em **http://localhost:5173**

---

## Funcionalidades — Fase 1

### Ingredientes
| Campo           | Tipo    | Descrição                                |
|-----------------|---------|------------------------------------------|
| Nome            | texto   | Nome do ingrediente (único)              |
| Unidade         | seleção | kg · g · L · ml · unidade               |
| Custo unitário  | decimal | Custo por unidade de medida (R$)         |
| Estoque mínimo  | decimal | Quantidade mínima em estoque             |

### Receitas
| Campo           | Tipo    | Descrição                                |
|-----------------|---------|------------------------------------------|
| Nome            | texto   | Nome da receita (único)                  |
| Descrição       | texto   | Descrição opcional                       |
| Categoria       | seleção | prato principal · sobremesa · bebida · entrada · petisco · outro |
| Preço de venda  | decimal | Valor cobrado ao cliente (R$)            |
| Rendimento      | inteiro | Número de porções que a receita produz   |
| Ingredientes    | lista   | Ingrediente + quantidade utilizada       |

**Calculado automaticamente:**
- **Custo Total** = Σ (custo_unitário × quantidade) de cada ingrediente
- **Custo por Porção** = Custo Total ÷ Rendimento
- **CMV %** = (Custo Total ÷ Preço de Venda) × 100

**Referência CMV:**
- 🟢 < 30% — Excelente
- 🟡 30–35% — Aceitável
- 🟠 35–40% — Atenção
- 🔴 > 40% — Revise precificação

---

## Endpoints da API

| Método | Rota                       | Descrição               |
|--------|----------------------------|-------------------------|
| GET    | /api/ingredientes/         | Listar ingredientes      |
| POST   | /api/ingredientes/         | Criar ingrediente        |
| GET    | /api/ingredientes/{id}     | Buscar ingrediente       |
| PUT    | /api/ingredientes/{id}     | Atualizar ingrediente    |
| DELETE | /api/ingredientes/{id}     | Excluir ingrediente      |
| GET    | /api/receitas/             | Listar receitas          |
| POST   | /api/receitas/             | Criar receita            |
| GET    | /api/receitas/{id}         | Buscar receita           |
| PUT    | /api/receitas/{id}         | Atualizar receita        |
| DELETE | /api/receitas/{id}         | Excluir receita          |

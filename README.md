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

## Hospedagem

| Parte | Onde | Observação |
|---|---|---|
| Frontend (React/Vite) | Vercel | o endereço do backend fica fixo em `frontend/src/api/index.js` |
| Backend (FastAPI) | Render (plano gratuito), definido em `render.yaml` | variáveis `DATABASE_URL` e `JWT_SECRET_KEY` configuradas no painel do Render |
| Banco (Postgres) | Supabase (plano gratuito) | pausa após 7 dias sem uso |

O plano gratuito do Render dorme após 15 min parado e o Supabase pausa após 7 dias sem uso. O workflow `.github/workflows/keep-alive.yml` chama `/api/saude/banco` a cada 5 minutos para evitar os dois; ele só roda depois de definir a variável do repositório `KEEPALIVE_URL` (Settings > Secrets and variables > Actions > Variables) com o endereço do backend.

## Perfis de acesso

| Perfil | Acessa |
|---|---|
| **Master** | Tudo: custos, preços, CMV, compras, fornecedores, estoque, canais de venda, relatórios e administração de usuários. |
| **Operação** | Somente leitura de receitas (ingredientes, quantidades, descrição, rendimento), lista de ingredientes (nome, unidade, aproveitamento) e **calculadora de proporção**. Nenhum valor financeiro. |

### Criar e vincular usuários

- **Contas já existentes** viram Master automaticamente e continuam com todos os dados.
- **Master → menu Usuários**: cria usuário (e-mail, senha inicial, perfil), troca o perfil, redefine a senha ou desativa. Todo usuário criado ali entra **no mesmo restaurante** (mesmos dados) de quem o criou.
- **Sócio**: crie como Master. **Funcionárias**: crie como Operação.
- O cadastro público foi fechado: só o primeiro usuário de um banco vazio se cadastra sozinho (`POST /api/auth/register`) e já nasce Master. Um Master não consegue remover o próprio acesso.
- Defina `JWT_SECRET_KEY` no servidor. Sem ela, o app usa uma chave aleatória por processo e os logins caem a cada reinício.

### Como a restrição é garantida

1. **Servidor:** o perfil é lido do banco a cada requisição (nunca do token). Toda rota é *somente Master* por padrão (`get_current_user`); só ficam abertas à Operação as rotas que declaram `get_operational_context`. A Operação recebe modelos de resposta que nem possuem campos financeiros.
2. **Banco:** as requisições da Operação rodam sob o papel `operacao_ro` (`SET LOCAL ROLE`), com `SELECT` apenas nas colunas não financeiras de ingredientes e receitas e política RLS por restaurante. O Postgres recusa o resto mesmo que o código erre. A inicialização verifica isso e, se falhar, bloqueia a Operação (503) em vez de liberar. RLS também fica ativo em todas as tabelas, fechando a API de dados do Supabase.

### Testes

```bash
cd backend
pip install -r requirements-dev.txt
# banco descartável: o nome precisa conter "test" (os testes apagam as tabelas) e o
# usuário precisa poder criar papéis, como o `postgres` do Supabase
set TEST_DATABASE_URL=postgresql+asyncpg://usuario:senha@127.0.0.1:5432/restaurante_test
pytest
```

### Backup e restauração

```bash
cd backend
# DATABASE_URL vem do ambiente ou de backend/.env (arquivo ignorado pelo git)
python scripts/db_backup.py backup                              # grava em backups/restaurante-AAAAMMDD-HHMMSS
python scripts/db_backup.py restore backups/restaurante-...     # só em tabelas vazias; --force sobrescreve
```

O backup é uma foto consistente (um CSV por tabela, com contagens e checksums), conferida ao final. A restauração valida os checksums e as contagens. A pasta `backups/` é ignorada pelo git: ela contém dados reais, então guarde uma cópia fora do computador (ex.: nuvem). O plano gratuito do Supabase não faz backup automático.

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

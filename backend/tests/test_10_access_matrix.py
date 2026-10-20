"""Master mantém acesso completo; Operação só consulta e calcula, sem nenhum dado financeiro."""
import re

import asyncpg
import pytest

from conftest import CANARIES, FINANCIAL_KEY, all_keys, asyncpg_dsn

# Única superfície que o perfil Operação pode usar. Qualquer outra rota deve dar 403.
ALLOWED_FOR_OPERACAO = {
    ("GET", "/"),
    ("GET", "/api/saude"),
    ("GET", "/api/saude/banco"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/register"),
    ("GET", "/api/auth/me"),
    ("GET", "/api/ingredientes/"),
    ("GET", "/api/ingredientes/{ingredient_id}"),
    ("GET", "/api/receitas/"),
    ("GET", "/api/receitas/{recipe_id}"),
    ("POST", "/api/receitas/{recipe_id}/calcular-proporcao"),
}

MASTER_ONLY_GETS = [
    "/api/compras/", "/api/fornecedores/", "/api/canais/", "/api/categorias/",
    "/api/estoque/", "/api/estoque/receitas/", "/api/usuarios/",
    "/api/fornecedores/1", "/api/fornecedores/1/compras", "/api/compras/1", "/api/compras/historico/1",
    "/api/estoque/movimentacoes/1", "/api/estoque/receitas/movimentacoes/1",
]

OPERACAO_INGREDIENT_KEYS = {"id", "name", "unit", "yield_percentage", "reduction_stages"}
OPERACAO_RECIPE_KEYS = {
    "id", "name", "description", "category", "yield_portions", "stock_unit", "is_proportional",
    "proportion_base_ingredient_id", "proportion_base_ingredient_name", "ingredients", "sub_recipes",
}


def assert_no_financial_data(response):
    body = response.text
    for label, canary in CANARIES.items():
        assert canary not in body, f"valor financeiro '{label}' vazou: {response.request.method} {response.request.url}"
    leaked = {k for k in all_keys(response.json()) if FINANCIAL_KEY.search(k)}
    assert not leaked, f"campos financeiros no JSON: {leaked}"


# ── Migração: contas existentes viram Master e nada se perde ─────────────────

async def test_legacy_accounts_became_master_and_data_is_intact(world):
    conn = await asyncpg.connect(asyncpg_dsn())
    try:
        users = await conn.fetch("SELECT id, email, role, account_id, is_active FROM users WHERE id IN (1, 2) ORDER BY id")
        assert [(u["role"], u["account_id"], u["is_active"]) for u in users] == [("master", 1, True), ("master", 2, True)]
        counts = {
            t: await conn.fetchval(f"SELECT count(*) FROM {t}")
            for t in ("ingredients", "recipes", "recipe_ingredients", "recipe_sub_recipes", "recipe_channel_prices",
                      "purchases", "purchase_items", "suppliers", "stock")
        }
        assert counts == {
            "ingredients": 4, "recipes": 3, "recipe_ingredients": 5, "recipe_sub_recipes": 1,
            "recipe_channel_prices": 1, "purchases": 1, "purchase_items": 1, "suppliers": 1, "stock": 1,
        }
    finally:
        await conn.close()


# ── Master ───────────────────────────────────────────────────────────────────

async def test_master_keeps_full_access_to_financial_data(world):
    c, h = world.client, world.auth("owner")

    me = (await c.get("/api/auth/me", headers=h)).json()
    assert me["role"] == "master"

    ings = (await c.get("/api/ingredientes/", headers=h)).json()
    salmao = next(i for i in ings if i["name"] == "Salmão")
    assert salmao["unit_cost"] == 7.7123
    assert salmao["purchase_cost"] == 123.4567
    assert salmao["processing_cost_per_unit"] == 1.2345
    assert salmao["real_unit_cost"] > 0

    recs = (await c.get("/api/receitas/", headers=h)).json()
    rec = next(r for r in recs if r["name"] == "Recheio de Salmão")
    assert rec["sale_price"] == 49.9123
    assert rec["total_cost"] > 0 and "cmv_percent" in rec
    assert rec["channel_prices"][0]["sale_price"] == 59.9876
    assert rec["ingredients"][0]["ingredient_unit_cost"] > 0

    one = await c.get(f"/api/receitas/{rec['id']}", headers=h)
    assert one.status_code == 200 and one.json()["sale_price"] == 49.9123

    for path in MASTER_ONLY_GETS:
        r = await c.get(path, headers=h)
        assert r.status_code in (200, 404), f"{path} -> {r.status_code}"
        assert r.status_code != 403, path


async def test_master_responses_keep_the_exact_same_contract(world):
    import schemas

    c, h = world.client, world.auth("owner")
    for item in (await c.get("/api/ingredientes/", headers=h)).json():
        assert set(item) == set(schemas.IngredientResponse.model_fields)
        schemas.IngredientResponse.model_validate(item)
    for item in (await c.get("/api/receitas/", headers=h)).json():
        assert set(item) == set(schemas.RecipeResponse.model_fields)
        schemas.RecipeResponse.model_validate(item)
    one = (await c.get("/api/ingredientes/1", headers=h)).json()
    assert set(one) == set(schemas.IngredientResponse.model_fields)


async def test_master_can_still_write(world):
    c, h = world.client, world.auth("owner")
    r = await c.post("/api/categorias/", headers=h, json={"name": "categoria-de-teste"})
    assert r.status_code == 201, r.text
    assert (await c.delete(f"/api/categorias/{r.json()['id']}", headers=h)).status_code == 204


async def test_master_calculator_returns_quantities_and_yield(world):
    r = await world.client.post("/api/receitas/1/calcular-proporcao", headers=world.auth("owner"), json={"base_quantity": 1.35})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["scale_factor"] == 1.35
    assert data["base_yield"] == 10 and data["calculated_yield"] == 13.5 and data["yield_unit"] == "porção"
    by_name = {i["ingredient_name"]: i for i in data["ingredients"]}
    assert by_name["Salmão"]["calculated_quantity"] == 1.35
    assert by_name["Cream Cheese"]["calculated_quantity"] == 0.54


# ── Operação: o que ela PRECISA conseguir fazer ──────────────────────────────

async def test_operacao_can_consult_ingredients_without_financial_data(world):
    c, h = world.client, world.auth("operacao")
    r = await c.get("/api/ingredientes/", headers=h)
    assert r.status_code == 200
    items = r.json()
    assert {"Salmão", "Cream Cheese", "Sal"} <= {i["name"] for i in items}
    assert "Camarão" not in {i["name"] for i in items}  # ingrediente de outro restaurante
    assert all(set(i) == OPERACAO_INGREDIENT_KEYS for i in items)
    assert next(i for i in items if i["name"] == "Salmão")["yield_percentage"] == 80
    assert_no_financial_data(r)

    one = await c.get(f"/api/ingredientes/{items[0]['id']}", headers=h)
    assert one.status_code == 200 and set(one.json()) == OPERACAO_INGREDIENT_KEYS
    assert_no_financial_data(one)


async def test_operacao_can_consult_recipes_without_financial_data(world):
    c, h = world.client, world.auth("operacao")
    r = await c.get("/api/receitas/", headers=h)
    assert r.status_code == 200
    items = r.json()
    names = {i["name"] for i in items}
    assert {"Recheio de Salmão", "Molho"} <= names and "Bobó" not in names
    assert all(set(i) == OPERACAO_RECIPE_KEYS for i in items)
    assert_no_financial_data(r)

    detail = await c.get("/api/receitas/1", headers=h)
    assert detail.status_code == 200
    d = detail.json()
    assert set(d) == OPERACAO_RECIPE_KEYS
    assert d["description"].startswith("Grelhe o salmão")
    assert d["yield_portions"] == 10 and d["is_proportional"] is True
    assert d["proportion_base_ingredient_name"] == "Salmão"
    quantities = {i["ingredient_name"]: i["quantity"] for i in d["ingredients"]}
    assert quantities == {"Salmão": 1.0, "Cream Cheese": 0.4, "Sal": 0.01}
    assert d["sub_recipes"] == [{"id": 1, "sub_recipe_id": 2, "sub_recipe_name": "Molho", "portions": 2}]
    assert_no_financial_data(detail)


async def test_operacao_calculator_shows_only_quantities_and_yield(world):
    r = await world.client.post(
        "/api/receitas/1/calcular-proporcao", headers=world.auth("operacao"), json={"base_quantity": 1.35}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["calculated_yield"] == 13.5
    by_name = {i["ingredient_name"]: i for i in data["ingredients"]}
    assert by_name["Salmão"]["calculated_quantity"] == 1.35
    assert by_name["Cream Cheese"]["calculated_quantity"] == 0.54
    assert_no_financial_data(r)

    bad = await world.client.post(
        "/api/receitas/1/calcular-proporcao", headers=world.auth("operacao"), json={"base_quantity": 0}
    )
    assert bad.status_code == 400
    not_proportional = await world.client.post(
        "/api/receitas/2/calcular-proporcao", headers=world.auth("operacao"), json={"base_quantity": 1}
    )
    assert not_proportional.status_code == 400


# ── Operação: tudo o que NÃO pode ────────────────────────────────────────────

async def test_operacao_is_denied_on_every_other_route(world):
    c = world.client
    spec = (await c.get("/openapi.json")).json()

    async def snapshot():
        h = world.auth("owner")
        return (
            len((await c.get("/api/ingredientes/", headers=h)).json()),
            len((await c.get("/api/receitas/", headers=h)).json()),
            len((await c.get("/api/usuarios/", headers=h)).json()),
            len((await c.get("/api/categorias/", headers=h)).json()),
        )

    before = await snapshot()
    checked = 0
    for path, methods in spec["paths"].items():
        for method in methods:
            m = method.upper()
            if (m, path) in ALLOWED_FOR_OPERACAO:
                continue
            url = re.sub(r"\{[^}]+\}", "1", path)
            kwargs = {"json": {}} if m in ("POST", "PUT", "PATCH") else {}
            r = await c.request(m, url, headers=world.auth("operacao"), **kwargs)
            assert r.status_code == 403, f"Operação em {m} {path} -> {r.status_code}: {r.text[:120]}"
            anon = await c.request(m, url, **kwargs)
            assert anon.status_code == 401, f"sem login em {m} {path} -> {anon.status_code}"
            checked += 1
    assert checked >= 35, f"só {checked} rotas verificadas; o inventário de rotas mudou?"
    assert await snapshot() == before  # nenhuma tentativa alterou dados


async def test_every_declared_route_is_classified(world):
    # Se alguém criar uma rota nova, ela cai no padrão "somente Master" automaticamente;
    # este teste só garante que a lista liberada à Operação continua existindo na API.
    spec = (await world.client.get("/openapi.json")).json()
    declared = {(m.upper(), p) for p, methods in spec["paths"].items() for m in methods}
    assert ALLOWED_FOR_OPERACAO <= declared


# ── Isolamento entre restaurantes ────────────────────────────────────────────

@pytest.mark.parametrize("who", ["operacao", "owner", "partner"])
async def test_other_restaurant_data_is_invisible(world, who):
    c, h = world.client, world.auth(who)
    assert (await c.get("/api/receitas/3", headers=h)).status_code == 404
    assert (await c.get("/api/ingredientes/4", headers=h)).status_code == 404
    assert (await c.post("/api/receitas/3/calcular-proporcao", headers=h, json={"base_quantity": 1})).status_code == 404
    names = {r["name"] for r in (await c.get("/api/receitas/", headers=h)).json()}
    assert "Bobó" not in names


async def test_other_restaurant_master_sees_only_its_own_data(world):
    c, h = world.client, world.auth("other")
    names = {r["name"] for r in (await c.get("/api/receitas/", headers=h)).json()}
    assert names == {"Bobó"}
    assert (await c.get("/api/receitas/1", headers=h)).status_code == 404

"""Estoque mínimo para receitas prontas e sub-receitas."""


def form_payload(recipe: dict, **changes) -> dict:
    """Corpo que o formulário de receita envia no PUT."""
    body = {
        "name": recipe["name"],
        "description": recipe["description"],
        "category": recipe["category"],
        "sale_price": recipe["sale_price"],
        "yield_portions": recipe["yield_portions"],
        "stock_unit": recipe["stock_unit"],
        "is_proportional": recipe["is_proportional"],
        "proportion_base_ingredient_id": recipe["proportion_base_ingredient_id"],
        "ingredients": [{"ingredient_id": i["ingredient_id"], "quantity": i["quantity"]} for i in recipe["ingredients"]],
    }
    body.update(changes)
    return body


async def stock_row(world, recipe_id):
    rows = (await world.client.get("/api/estoque/receitas/", headers=world.auth("owner"))).json()
    return next(r for r in rows if r["recipe_id"] == recipe_id)


async def test_existing_recipes_start_with_zero_minimum_after_migration(world):
    recs = (await world.client.get("/api/receitas/", headers=world.auth("owner"))).json()
    assert {r["name"]: r["min_stock"] for r in recs if r["name"] in ("Recheio de Salmão", "Molho")} == {
        "Recheio de Salmão": 0,
        "Molho": 0,
    }


async def test_minimum_is_set_in_the_recipe_form_and_shows_in_stock(world):
    c, h = world.client, world.auth("owner")
    recipe = (await c.get("/api/receitas/1", headers=h)).json()

    r = await c.put("/api/receitas/1", headers=h, json=form_payload(recipe, min_stock=5))
    assert r.status_code == 200, r.text
    assert r.json()["min_stock"] == 5
    assert (await c.get("/api/receitas/1", headers=h)).json()["min_stock"] == 5

    row = await stock_row(world, 1)
    assert row["min_stock"] == 5 and row["recipe_name"] == "Recheio de Salmão"

    # a tela decide "acabando" comparando quantidade com mínimo
    adj = await c.put("/api/estoque/receitas/1", headers=h, json={"quantity": 2})
    assert adj.status_code == 200 and adj.json()["min_stock"] == 5
    row = await stock_row(world, 1)
    assert row["quantity"] == 2 and row["quantity"] < row["min_stock"]


async def test_old_client_that_omits_the_field_does_not_reset_the_minimum(world):
    c, h = world.client, world.auth("owner")
    recipe = (await c.get("/api/receitas/1", headers=h)).json()
    body = form_payload(recipe)
    body.pop("min_stock", None)
    assert (await c.put("/api/receitas/1", headers=h, json=body)).status_code == 200
    assert (await c.get("/api/receitas/1", headers=h)).json()["min_stock"] == 5


async def test_minimum_can_be_set_for_sub_recipes_straight_from_stock(world):
    c, h = world.client, world.auth("owner")
    r = await c.put("/api/receitas/2/estoque-minimo", headers=h, json={"min_stock": 3.5})
    assert r.status_code == 200 and r.json()["min_stock"] == 3.5
    row = await stock_row(world, 2)
    assert row["recipe_name"] == "Molho" and row["min_stock"] == 3.5
    # editar o mínimo não mexe no resto da receita
    assert r.json()["name"] == "Molho" and r.json()["sale_price"] == 5.5


async def test_new_recipe_can_be_created_with_minimum(world):
    c, h = world.client, world.auth("owner")
    body = {
        "name": "Recheio com mínimo", "description": None, "category": "entrada", "sale_price": 10,
        "yield_portions": 2, "stock_unit": "bandeja", "min_stock": 2.5,
        "ingredients": [{"ingredient_id": 3, "quantity": 0.1}],
    }
    r = await c.post("/api/receitas/", headers=h, json=body)
    assert r.status_code == 201, r.text
    assert r.json()["min_stock"] == 2.5
    assert (await stock_row(world, r.json()["id"]))["min_stock"] == 2.5


async def test_invalid_minimum_is_rejected(world):
    c, h = world.client, world.auth("owner")
    assert (await c.put("/api/receitas/2/estoque-minimo", headers=h, json={"min_stock": -1})).status_code == 422
    assert (await c.put("/api/receitas/2/estoque-minimo", headers=h, json={})).status_code == 422
    recipe = (await c.get("/api/receitas/2", headers=h)).json()
    assert (await c.put("/api/receitas/2", headers=h, json=form_payload(recipe, min_stock=-5))).status_code == 422
    assert (await c.get("/api/receitas/2", headers=h)).json()["min_stock"] == 3.5


async def test_minimum_respects_restaurant_boundaries_and_profiles(world):
    c = world.client
    # receita de outro restaurante
    other = await c.put("/api/receitas/3/estoque-minimo", headers=world.auth("owner"), json={"min_stock": 9})
    assert other.status_code == 404
    # a Operação não vê nem altera o estoque mínimo
    op = world.auth("operacao")
    assert (await c.put("/api/receitas/1/estoque-minimo", headers=op, json={"min_stock": 0})).status_code == 403
    assert (await c.get("/api/estoque/receitas/", headers=op)).status_code == 403
    for item in (await c.get("/api/receitas/", headers=op)).json():
        assert "min_stock" not in item
    assert "min_stock" not in (await c.get("/api/receitas/1", headers=op)).json()
    assert (await c.get("/api/receitas/1", headers=world.auth("owner"))).json()["min_stock"] == 5

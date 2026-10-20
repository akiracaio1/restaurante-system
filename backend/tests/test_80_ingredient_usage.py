"""Em quais receitas cada ingrediente é usado."""


async def usage(world, who, ingredient_id):
    return await world.client.get(f"/api/ingredientes/{ingredient_id}/receitas", headers=world.auth(who))


async def test_lists_every_recipe_that_uses_the_ingredient(world):
    r = await usage(world, "owner", 3)  # Sal: Recheio de Salmão (0,01) e Molho (0,2)
    assert r.status_code == 200, r.text
    data = r.json()
    assert (data["ingredient_name"], data["unit"]) == ("Sal", "kg")
    names = [x["recipe_name"] for x in data["recipes"]]
    assert names == sorted(names)  # em ordem alfabética
    by_name = {x["recipe_name"]: x for x in data["recipes"]}
    assert {n: by_name[n]["quantity"] for n in ("Molho", "Recheio de Salmão", "Recheio com mínimo")} == {
        "Molho": 0.2, "Recheio de Salmão": 0.01, "Recheio com mínimo": 0.1,  # a última vem de um teste anterior
    }
    assert "Bobó" not in names  # receita de outro restaurante
    assert by_name["Molho"]["is_sub_recipe"] is True          # Molho é usada dentro do Recheio
    assert by_name["Recheio de Salmão"]["is_sub_recipe"] is False
    assert by_name["Recheio de Salmão"]["category"] == "prato principal"
    assert data["channel_extras"] == []


async def test_ingredient_with_no_recipe_returns_empty_lists(world):
    c, h = world.client, world.auth("owner")
    created = await c.post("/api/ingredientes/", headers=h, json={"name": "Sem uso nenhum", "unit": "kg", "unit_cost": 1})
    assert created.status_code == 201
    data = (await usage(world, "owner", created.json()["id"])).json()
    assert data["recipes"] == [] and data["channel_extras"] == []


async def test_includes_channel_extras_such_as_packaging(world):
    c, h = world.client, world.auth("owner")
    pack = (await c.post("/api/ingredientes/", headers=h, json={"name": "Embalagem teste", "unit": "un", "unit_cost": 0.5})).json()
    recipe = await c.post("/api/receitas/", headers=h, json={
        "name": "Combo com embalagem", "category": "entrada", "sale_price": 10, "yield_portions": 1,
        "ingredients": [{"ingredient_id": 3, "quantity": 0.1}],
    })
    assert recipe.status_code == 201
    channel = await c.put(f"/api/receitas/{recipe.json()['id']}/canais/1", headers=h, json={
        "sale_price": 12, "extra_ingredients": [{"ingredient_id": pack["id"], "quantity": 2}],
    })
    assert channel.status_code == 200, channel.text

    data = (await usage(world, "owner", pack["id"])).json()
    assert data["recipes"] == []
    assert [(e["recipe_name"], e["channel_name"], e["quantity"]) for e in data["channel_extras"]] == [
        ("Combo com embalagem", "iFood", 2)
    ]
    # e o Sal agora também aparece na receita nova
    assert "Combo com embalagem" in [x["recipe_name"] for x in (await usage(world, "owner", 3)).json()["recipes"]]


async def test_usage_is_limited_to_the_own_restaurant_and_to_masters(world):
    # outro restaurante: vê só as próprias receitas e não alcança ingredientes deste
    other = await usage(world, "other", 4)  # Camarão
    assert other.status_code == 200
    assert [x["recipe_name"] for x in other.json()["recipes"]] == ["Bobó"]
    assert (await usage(world, "other", 3)).status_code == 404
    assert (await usage(world, "owner", 4)).status_code == 404
    assert (await usage(world, "owner", 999999)).status_code == 404
    # sócio (Master do mesmo restaurante) vê; Operação e anônimo não
    assert (await usage(world, "partner", 3)).status_code == 200
    assert (await usage(world, "operacao", 3)).status_code == 403
    assert (await world.client.get("/api/ingredientes/3/receitas")).status_code == 401

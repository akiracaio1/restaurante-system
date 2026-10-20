"""Mesclar ingredientes duplicados sem perder nada que dependa deles."""
import pytest
import pytest_asyncio


@pytest_asyncio.fixture(scope="module")
async def mayo(world):
    c, h = world.client, world.auth("owner")

    async def create(path, body):
        r = await c.post(path, headers=h, json=body)
        assert r.status_code == 201, r.text
        return r.json()

    a = await create("/api/ingredientes/", {"name": "Maionese sache", "unit": "un", "unit_cost": 0.5, "min_stock": 0})
    b = await create("/api/ingredientes/", {"name": "Maionese sachê", "unit": "un", "unit_cost": 0.6, "min_stock": 10})
    kg = await create("/api/ingredientes/", {"name": "Item em kg", "unit": "kg", "unit_cost": 1, "min_stock": 0})
    base = {"category": "entrada", "sale_price": 10, "yield_portions": 1}
    only_a = await create("/api/receitas/", {**base, "name": "Receita só com A", "is_proportional": True,
                           "proportion_base_ingredient_id": a["id"], "ingredients": [{"ingredient_id": a["id"], "quantity": 2}]})
    both = await create("/api/receitas/", {**base, "name": "Receita com os dois", "ingredients": [
        {"ingredient_id": a["id"], "quantity": 1}, {"ingredient_id": b["id"], "quantity": 3}]})
    only_b = await create("/api/receitas/", {**base, "name": "Receita só com B", "ingredients": [{"ingredient_id": b["id"], "quantity": 1}]})

    for recipe, extras in (
        (only_a, [{"ingredient_id": a["id"], "quantity": 1}]),
        (both, [{"ingredient_id": a["id"], "quantity": 1}, {"ingredient_id": b["id"], "quantity": 2}]),
    ):
        r = await c.put(f"/api/receitas/{recipe['id']}/canais/1", headers=h, json={"sale_price": 12, "extra_ingredients": extras})
        assert r.status_code == 200, r.text

    await create("/api/compras/", {"date": "2026-10-01", "items": [
        {"ingredient_id": a["id"], "quantity": 20, "unit": "un", "total_price": 10}]})   # estoque de A = 20
    inv = await c.post("/api/estoque/inventario", headers=h, json={"items": [{"type": "ingrediente", "id": b["id"], "quantity": 5}]})
    assert inv.status_code == 200, inv.text                                               # estoque de B = 5
    return {"a": a["id"], "b": b["id"], "kg": kg["id"], "only_a": only_a["id"], "both": both["id"], "only_b": only_b["id"]}


async def stock_of(world, ingredient_id):
    rows = (await world.client.get("/api/estoque/", headers=world.auth("owner"))).json()
    return next((r["quantity"] for r in rows if r["ingredient_id"] == ingredient_id), None)


async def recipe_items(world, recipe_id):
    r = (await world.client.get(f"/api/receitas/{recipe_id}", headers=world.auth("owner"))).json()
    return {i["ingredient_name"]: i["quantity"] for i in r["ingredients"]}, r


async def test_dry_run_reports_everything_and_changes_nothing(world, mayo):
    c, h = world.client, world.auth("owner")
    r = await c.post(f"/api/ingredientes/{mayo['b']}/mesclar", headers=h, json={"source_id": mayo["a"], "dry_run": True})
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["dry_run"] is True and s["target_name"] == "Maionese sachê" and s["source_name"] == "Maionese sache"
    assert s["recipes_moved"] == ["Receita só com A"] and s["recipes_combined"] == ["Receita com os dois"]
    assert s["channel_prices_updated"] == 2 and s["purchase_items_moved"] == 1
    assert (s["stock_target_before"], s["stock_source_before"], s["stock_after"]) == (5, 20, 25)
    assert s["base_recipes"] == ["Receita só com A"]

    # nada mudou
    assert (await c.get(f"/api/ingredientes/{mayo['a']}", headers=h)).status_code == 200
    items, _ = await recipe_items(world, mayo["only_a"])
    assert items == {"Maionese sache": 2}
    assert await stock_of(world, mayo["a"]) == 20 and await stock_of(world, mayo["b"]) == 5


async def test_invalid_merges_are_refused(world, mayo):
    c, h = world.client, world.auth("owner")
    url = f"/api/ingredientes/{mayo['b']}/mesclar"
    assert (await c.post(url, headers=h, json={"source_id": mayo["b"]})).status_code == 400      # com ele mesmo
    kg = await c.post(url, headers=h, json={"source_id": mayo["kg"]})
    assert kg.status_code == 400 and "Unidades diferentes" in kg.json()["detail"]                 # unidades diferentes
    assert (await c.post(url, headers=h, json={"source_id": 999999})).status_code == 404
    assert (await c.post(f"/api/ingredientes/{mayo['b']}/mesclar", headers=world.auth("other"),
                         json={"source_id": mayo["a"]})).status_code == 404                        # outro restaurante
    assert (await c.post(url, headers=world.auth("operacao"), json={"source_id": mayo["a"]})).status_code == 403
    assert (await c.post(url, json={"source_id": mayo["a"]})).status_code == 401
    assert (await c.get(f"/api/ingredientes/{mayo['a']}", headers=h)).status_code == 200          # nada foi mexido


async def test_merge_moves_everything_to_the_ingredient_that_stays(world, mayo):
    c, h = world.client, world.auth("owner")
    r = await c.post(f"/api/ingredientes/{mayo['b']}/mesclar", headers=h, json={"source_id": mayo["a"]})
    assert r.status_code == 200, r.text
    assert r.json()["dry_run"] is False and r.json()["stock_after"] == 25

    # o duplicado sumiu e o que ficou continua
    assert (await c.get(f"/api/ingredientes/{mayo['a']}", headers=h)).status_code == 404
    names = {i["name"] for i in (await c.get("/api/ingredientes/", headers=h)).json()}
    assert "Maionese sache" not in names and "Maionese sachê" in names

    # receitas: ninguém perdeu o ingrediente; quem tinha os dois soma as quantidades
    items, recipe = await recipe_items(world, mayo["only_a"])
    assert items == {"Maionese sachê": 2}
    assert recipe["proportion_base_ingredient_name"] == "Maionese sachê"
    assert recipe["total_cost"] == 1.2  # 2 x custo do que ficou (0,6): custos seguem corretos
    items, recipe = await recipe_items(world, mayo["both"])
    assert items == {"Maionese sachê": 4} and len(recipe["ingredients"]) == 1
    assert (await recipe_items(world, mayo["only_b"]))[0] == {"Maionese sachê": 1}

    # custos extras das modalidades de venda
    only_a_channels = (await c.get(f"/api/receitas/{mayo['only_a']}", headers=h)).json()["channel_prices"]
    assert [(e["ingredient_name"], e["quantity"]) for e in only_a_channels[0]["extra_ingredients"]] == [("Maionese sachê", 1)]
    both_channels = (await c.get(f"/api/receitas/{mayo['both']}", headers=h)).json()["channel_prices"]
    assert [(e["ingredient_name"], e["quantity"]) for e in both_channels[0]["extra_ingredients"]] == [("Maionese sachê", 3)]

    # histórico de compras e estoque
    history = (await c.get(f"/api/compras/historico/{mayo['b']}", headers=h)).json()
    assert len(history) == 1 and history[0]["quantity"] == 20
    assert await stock_of(world, mayo["b"]) == 25
    moves = (await c.get(f"/api/estoque/movimentacoes/{mayo['b']}", headers=h)).json()
    assert any(m["reason"] == "mescla" and "5 + 20 = 25" in m["notes"] for m in moves)
    assert any(m["reason"] == "compra" for m in moves)  # o histórico do duplicado veio junto

    # o que ficou mantém o próprio estoque mínimo
    assert (await c.get(f"/api/ingredientes/{mayo['b']}", headers=h)).json()["min_stock"] == 10
    # repetir não faz nada: o duplicado já não existe
    assert (await c.post(f"/api/ingredientes/{mayo['b']}/mesclar", headers=h, json={"source_id": mayo["a"]})).status_code == 404


async def test_minimum_stock_is_inherited_when_the_kept_one_has_none(world):
    c, h = world.client, world.auth("owner")
    keep = (await c.post("/api/ingredientes/", headers=h, json={"name": "Pimenta X", "unit": "kg", "unit_cost": 1, "min_stock": 0})).json()
    dup = (await c.post("/api/ingredientes/", headers=h, json={"name": "Pimenta Y", "unit": "kg", "unit_cost": 1, "min_stock": 3})).json()
    r = await c.post(f"/api/ingredientes/{keep['id']}/mesclar", headers=h, json={"source_id": dup["id"]})
    assert r.status_code == 200
    assert (await c.get(f"/api/ingredientes/{keep['id']}", headers=h)).json()["min_stock"] == 3

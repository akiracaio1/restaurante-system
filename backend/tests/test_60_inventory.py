"""Inventário: contagem de vários itens salva de uma vez, tudo ou nada."""


async def snapshot(world):
    c, h = world.client, world.auth("owner")
    ing = {r["ingredient_id"]: r["quantity"] for r in (await c.get("/api/estoque/", headers=h)).json()}
    rec = {r["recipe_id"]: r["quantity"] for r in (await c.get("/api/estoque/receitas/", headers=h)).json()}
    return ing, rec


async def movements(world, kind, item_id):
    path = f"/api/estoque/movimentacoes/{item_id}" if kind == "ingrediente" else f"/api/estoque/receitas/movimentacoes/{item_id}"
    return (await world.client.get(path, headers=world.auth("owner"))).json()


BATCH = {
    "notes": "contagem semanal",
    "items": [
        {"type": "ingrediente", "id": 1, "quantity": 7.5},   # tinha 3
        {"type": "ingrediente", "id": 2, "quantity": 4},     # sem registro de estoque ainda
        {"type": "ingrediente", "id": 3, "quantity": 0},     # sem registro e contou zero: nada a mudar
        {"type": "receita", "id": 1, "quantity": 9},
        {"type": "receita", "id": 2, "quantity": 6},         # sub-receita sem registro ainda
    ],
}


async def test_saves_ingredients_and_recipes_in_one_request(world):
    c, h = world.client, world.auth("owner")
    r = await c.post("/api/estoque/inventario", headers=h, json=BATCH)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["updated"], body["unchanged"]) == (4, 1)
    by_key = {(x["type"], x["id"]): x for x in body["changes"]}
    assert by_key[("ingrediente", 1)]["before"] == 3 and by_key[("ingrediente", 1)]["after"] == 7.5
    assert by_key[("ingrediente", 1)]["name"] == "Salmão" and by_key[("ingrediente", 1)]["unit"] == "kg"
    assert by_key[("receita", 2)]["name"] == "Molho" and by_key[("receita", 2)]["before"] == 0

    ing, rec = await snapshot(world)
    assert ing[1] == 7.5 and ing[2] == 4 and ing[3] == 0
    assert rec[1] == 9 and rec[2] == 6


async def test_each_change_is_recorded_in_the_stock_history(world):
    ing_moves = await movements(world, "ingrediente", 1)
    last = ing_moves[0]
    assert (last["type"], last["reason"], last["quantity"]) == ("ajuste", "inventario", 7.5)
    assert "3 → 7,5" in last["notes"] and "contagem semanal" in last["notes"]

    rec_moves = await movements(world, "receita", 2)
    assert rec_moves[0]["reason"] == "inventario" and "0 → 6" in rec_moves[0]["notes"]
    # item sem diferença não gera movimentação
    assert await movements(world, "ingrediente", 3) == []


async def test_repeating_the_same_count_changes_nothing(world):
    before_moves = len(await movements(world, "ingrediente", 1))
    r = await world.client.post("/api/estoque/inventario", headers=world.auth("owner"), json=BATCH)
    assert r.status_code == 200
    assert (r.json()["updated"], r.json()["unchanged"]) == (0, 5)
    assert len(await movements(world, "ingrediente", 1)) == before_moves


async def test_all_or_nothing_when_one_item_is_invalid(world):
    c, h = world.client, world.auth("owner")
    before = await snapshot(world)
    moves = len(await movements(world, "ingrediente", 1))
    bad = {"items": [
        {"type": "ingrediente", "id": 1, "quantity": 100},   # válido
        {"type": "ingrediente", "id": 4, "quantity": 5},     # ingrediente de outro restaurante
    ]}
    r = await c.post("/api/estoque/inventario", headers=h, json=bad)
    assert r.status_code == 404
    assert await snapshot(world) == before
    assert len(await movements(world, "ingrediente", 1)) == moves

    missing = {"items": [{"type": "receita", "id": 999999, "quantity": 1}]}
    assert (await c.post("/api/estoque/inventario", headers=h, json=missing)).status_code == 404


async def test_invalid_payloads_are_rejected(world):
    c, h = world.client, world.auth("owner")
    ok = {"type": "ingrediente", "id": 1, "quantity": 1}
    assert (await c.post("/api/estoque/inventario", headers=h, json={"items": [ok, ok]})).status_code == 400
    assert (await c.post("/api/estoque/inventario", headers=h, json={"items": []})).status_code == 422
    assert (await c.post("/api/estoque/inventario", headers=h, json={"items": [{**ok, "quantity": -1}]})).status_code == 422
    assert (await c.post("/api/estoque/inventario", headers=h, json={"items": [{**ok, "type": "produto"}]})).status_code == 422
    assert (await c.post("/api/estoque/inventario", headers=h, json={})).status_code == 422
    too_many = [{"type": "ingrediente", "id": i, "quantity": 1} for i in range(1, 2002)]
    assert (await c.post("/api/estoque/inventario", headers=h, json={"items": too_many})).status_code == 422


async def test_inventory_respects_restaurants_and_profiles(world):
    c = world.client
    same_account = {"items": [{"type": "ingrediente", "id": 3, "quantity": 1.25}]}
    # sócio (Master do mesmo restaurante) pode
    assert (await c.post("/api/estoque/inventario", headers=world.auth("partner"), json=same_account)).status_code == 200
    # Operação não
    assert (await c.post("/api/estoque/inventario", headers=world.auth("operacao"), json=same_account)).status_code == 403
    assert (await c.post("/api/estoque/inventario", json=same_account)).status_code == 401
    # outro restaurante não alcança os itens deste, e conta só os dele
    assert (await c.post("/api/estoque/inventario", headers=world.auth("other"), json=same_account)).status_code == 404
    own = {"items": [{"type": "ingrediente", "id": 4, "quantity": 2}, {"type": "receita", "id": 3, "quantity": 1}]}
    r = await c.post("/api/estoque/inventario", headers=world.auth("other"), json=own)
    assert r.status_code == 200 and r.json()["updated"] == 2
    ing, _ = await snapshot(world)
    assert ing[3] == 1.25 and 4 not in ing

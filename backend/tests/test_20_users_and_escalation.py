"""Só Master concede ou altera permissões; ninguém eleva o próprio acesso."""
import base64
import json
import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt

from conftest import TEST_SECRET


def forge(sub, secret=TEST_SECRET, **claims) -> str:
    payload = {"sub": str(sub), "exp": datetime.now(timezone.utc) + timedelta(hours=1), **claims}
    return jwt.encode(payload, secret, algorithm="HS256")


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def new_user(world, role="operacao"):
    email = f"tmp-{uuid.uuid4().hex[:8]}@restaurante-a.com"
    r = await world.client.post(
        "/api/usuarios/", headers=world.auth("owner"), json={"email": email, "password": "senha-temp-1", "role": role}
    )
    assert r.status_code == 201, r.text
    login = await world.client.post("/api/auth/login", json={"email": email, "password": "senha-temp-1"})
    return r.json()["id"], email, login.json()["access_token"]


# ── Operação não consegue se promover ────────────────────────────────────────

async def test_operacao_cannot_manage_users_or_promote_self(world):
    c, h, op_id = world.client, world.auth("operacao"), world.ids["operacao"]

    assert (await c.get("/api/usuarios/", headers=h)).status_code == 403
    assert (await c.put(f"/api/usuarios/{op_id}", headers=h, json={"role": "master"})).status_code == 403
    assert (
        await c.post("/api/usuarios/", headers=h, json={"email": "novo@x.com", "password": "senha-123", "role": "master"})
    ).status_code == 403
    assert (await c.put(f"/api/usuarios/{op_id}", headers=h, json={"password": "outra-senha"})).status_code == 403

    me = (await c.get("/api/auth/me", headers=h)).json()
    assert me["role"] == "operacao"
    assert (await c.get("/api/compras/", headers=h)).status_code == 403


async def test_operacao_cannot_register_or_pick_role_on_login(world):
    c = world.client
    reg = await c.post(
        "/api/auth/register", json={"email": "nova-master@x.com", "password": "senha-123", "role": "master"}
    )
    assert reg.status_code == 403

    login = await c.post(
        "/api/auth/login",
        json={"email": "funcionaria@restaurante-a.com", "password": "operacao-pass-1", "role": "master"},
    )
    assert login.status_code == 200 and login.json()["role"] == "operacao"


async def test_role_claim_in_token_is_ignored(world):
    c, op_id = world.client, world.ids["operacao"]
    token = forge(op_id, role="master", is_admin=True)
    assert (await c.get("/api/auth/me", headers=bearer(token))).json()["role"] == "operacao"
    assert (await c.get("/api/compras/", headers=bearer(token))).status_code == 403
    assert (await c.get("/api/usuarios/", headers=bearer(token))).status_code == 403


async def test_forged_tokens_are_rejected(world):
    c, owner_id = world.client, world.ids["owner"]
    for secret in ("outra-chave", "fallback-insecure-key", ""):
        r = await c.get("/api/auth/me", headers=bearer(forge(owner_id, secret=secret or "x")))
        assert r.status_code == 401, secret

    def b64(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    none_token = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': str(owner_id)})}."
    assert (await c.get("/api/auth/me", headers=bearer(none_token))).status_code == 401
    assert (await c.get("/api/auth/me", headers=bearer("lixo"))).status_code == 401
    assert (await c.get("/api/auth/me", headers=bearer(forge("abc")))).status_code == 401
    assert (await c.get("/api/auth/me", headers=bearer(forge(987654)))).status_code == 401


# ── Regras da administração de usuários (Master) ─────────────────────────────

async def test_user_creation_validation(world):
    c, h = world.client, world.auth("owner")
    base = {"email": "valido@restaurante-a.com", "password": "senha-boa-1", "role": "operacao"}
    assert (await c.post("/api/usuarios/", headers=h, json={**base, "role": "admin"})).status_code == 400
    assert (await c.post("/api/usuarios/", headers=h, json={**base, "password": "123"})).status_code == 400
    assert (await c.post("/api/usuarios/", headers=h, json={**base, "email": "funcionaria@restaurante-a.com"})).status_code == 400
    assert (await c.post("/api/usuarios/", headers=h, json={**base, "email": "nao-e-email"})).status_code == 422


async def test_master_cannot_remove_own_access(world):
    c, h, owner_id = world.client, world.auth("owner"), world.ids["owner"]
    assert (await c.put(f"/api/usuarios/{owner_id}", headers=h, json={"role": "operacao"})).status_code == 400
    assert (await c.put(f"/api/usuarios/{owner_id}", headers=h, json={"is_active": False})).status_code == 400
    assert (await c.put(f"/api/usuarios/{owner_id}", headers=h, json={"role": "bogus"})).status_code == 400
    assert (await c.get("/api/compras/", headers=h)).status_code == 200


async def test_role_changes_apply_immediately_with_the_same_token(world):
    c = world.client
    uid, _email, token = await new_user(world, role="master")
    assert (await c.get("/api/compras/", headers=bearer(token))).status_code == 200

    r = await c.put(f"/api/usuarios/{uid}", headers=world.auth("owner"), json={"role": "operacao"})
    assert r.status_code == 200 and r.json()["role"] == "operacao"
    assert (await c.get("/api/compras/", headers=bearer(token))).status_code == 403
    assert (await c.get("/api/ingredientes/", headers=bearer(token))).status_code == 200

    await c.put(f"/api/usuarios/{uid}", headers=world.auth("owner"), json={"role": "master"})
    assert (await c.get("/api/compras/", headers=bearer(token))).status_code == 200


async def test_deactivated_user_loses_access_immediately(world):
    c = world.client
    uid, email, token = await new_user(world)
    assert (await c.get("/api/auth/me", headers=bearer(token))).status_code == 200

    await c.put(f"/api/usuarios/{uid}", headers=world.auth("owner"), json={"is_active": False})
    assert (await c.get("/api/auth/me", headers=bearer(token))).status_code == 401
    assert (await c.get("/api/ingredientes/", headers=bearer(token))).status_code == 401
    blocked = await c.post("/api/auth/login", json={"email": email, "password": "senha-temp-1"})
    assert blocked.status_code == 403

    await c.put(f"/api/usuarios/{uid}", headers=world.auth("owner"), json={"is_active": True})
    again = await c.post("/api/auth/login", json={"email": email, "password": "senha-temp-1"})
    assert again.status_code == 200


async def test_password_reset_by_master(world):
    c = world.client
    uid, email, _token = await new_user(world)
    assert (await c.put(f"/api/usuarios/{uid}", headers=world.auth("owner"), json={"password": "123"})).status_code == 400
    ok = await c.put(f"/api/usuarios/{uid}", headers=world.auth("owner"), json={"password": "nova-senha-9"})
    assert ok.status_code == 200
    assert (await c.post("/api/auth/login", json={"email": email, "password": "senha-temp-1"})).status_code == 401
    assert (await c.post("/api/auth/login", json={"email": email, "password": "nova-senha-9"})).status_code == 200


async def test_users_are_scoped_to_the_restaurant(world):
    c = world.client
    mine = {u["email"] for u in (await c.get("/api/usuarios/", headers=world.auth("owner"))).json()}
    assert {"owner@restaurante-a.com", "funcionaria@restaurante-a.com", "socio@restaurante-a.com"} <= mine
    assert "dono@restaurante-b.com" not in mine

    theirs = {u["email"] for u in (await c.get("/api/usuarios/", headers=world.auth("other"))).json()}
    assert theirs == {"dono@restaurante-b.com"}

    # um Master não enxerga nem altera usuários de outro restaurante
    other_id = world.ids["other"]
    assert (await c.put(f"/api/usuarios/{other_id}", headers=world.auth("owner"), json={"role": "operacao"})).status_code == 404
    assert (await c.put(f"/api/usuarios/{world.ids['owner']}", headers=world.auth("other"), json={"role": "operacao"})).status_code == 404


async def test_partner_master_shares_the_same_data_and_admin_powers(world):
    c = world.client
    r = await c.post(
        "/api/ingredientes/",
        headers=world.auth("partner"),
        json={"name": "Pimenta do sócio", "unit": "kg", "unit_cost": 9.99},
    )
    assert r.status_code == 201, r.text
    owner_view = {i["name"] for i in (await c.get("/api/ingredientes/", headers=world.auth("owner"))).json()}
    assert "Pimenta do sócio" in owner_view
    operacao_view = {i["name"] for i in (await c.get("/api/ingredientes/", headers=world.auth("operacao"))).json()}
    assert "Pimenta do sócio" in operacao_view

    uid, _email, _token = await new_user(world)
    promoted = await c.put(f"/api/usuarios/{uid}", headers=world.auth("partner"), json={"role": "master"})
    assert promoted.status_code == 200

"""Banco vazio: só o primeiro usuário pode se cadastrar, e ele nasce Master."""
import httpx
import asyncpg

from conftest import reset_database, asyncpg_dsn


async def test_first_user_is_master_and_public_signup_closes_after():
    await reset_database()
    import main
    import rbac_db

    async with main.app.router.lifespan_context(main.app):
        assert rbac_db.operacao_role_ready()
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # tentar se cadastrar já como "operacao" ou escolher perfil não muda nada: perfil não vem do cliente
            r = await client.post(
                "/api/auth/register",
                json={"email": "primeiro@x.com", "password": "primeira-senha", "role": "operacao"},
            )
            assert r.status_code == 201, r.text
            assert r.json()["role"] == "master"
            headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

            me = (await client.get("/api/auth/me", headers=headers)).json()
            assert me["role"] == "master"

            users = (await client.get("/api/usuarios/", headers=headers)).json()
            assert [u["email"] for u in users] == ["primeiro@x.com"]

            # cadastro público fechado depois do primeiro usuário (inclusive tentando virar Master)
            for body in (
                {"email": "intruso@x.com", "password": "senha-intruso"},
                {"email": "intruso@x.com", "password": "senha-intruso", "role": "master"},
            ):
                blocked = await client.post("/api/auth/register", json=body)
                assert blocked.status_code == 403, blocked.text

    await main.engine.dispose()

    conn = await asyncpg.connect(asyncpg_dsn())
    try:
        row = await conn.fetchrow("SELECT id, role, account_id, is_active FROM users")
        assert (row["role"], row["account_id"], row["is_active"]) == ("master", row["id"], True)
        assert await conn.fetchval("SELECT 1 FROM pg_constraint WHERE conname = 'ck_users_role'") == 1
    finally:
        await conn.close()

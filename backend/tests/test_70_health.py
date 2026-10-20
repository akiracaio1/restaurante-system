"""Rotas de saúde públicas: não podem expor nenhum dado."""


async def test_health_endpoints_are_public_and_expose_nothing(world):
    c = world.client
    r = await c.get("/api/saude")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    r = await c.get("/api/saude/banco")
    assert r.status_code == 200 and r.json() == {"status": "ok", "banco": "ok"}


async def test_database_health_reports_failure_without_leaking_details(world, monkeypatch):
    import main

    class Broken:
        def connect(self):
            raise RuntimeError("senha=segredo host=interno")

    monkeypatch.setattr(main, "engine", Broken())
    r = await world.client.get("/api/saude/banco")
    assert r.status_code == 503
    assert "segredo" not in r.text and "interno" not in r.text
    # a rota que não toca no banco continua respondendo
    assert (await world.client.get("/api/saude")).status_code == 200

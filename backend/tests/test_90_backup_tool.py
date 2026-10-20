"""Backup e restauração: ciclo completo, inclusive com coluna que só existe no backup.

Roda por último: apaga as tabelas e restaura tudo, deixando o banco como estava.
"""
import os
import subprocess
import sys
from pathlib import Path

import asyncpg

from conftest import TEST_DATABASE_URL, asyncpg_dsn

BACKEND = Path(__file__).resolve().parent.parent
SCRIPT = BACKEND / "scripts" / "db_backup.py"


def run_tool(*args):
    # Nunca deixa a ferramenta cair no DATABASE_URL de produção do backend/.env.
    dbname = TEST_DATABASE_URL.rsplit("/", 1)[-1]
    assert "test" in dbname.lower()
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=BACKEND, timeout=180)


async def fingerprint(conn):
    tables = [r["tablename"] for r in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")]
    out = {}
    for t in tables:
        out[t] = (
            await conn.fetchval(f'SELECT count(*) FROM "{t}"'),
            await conn.fetchval(f"SELECT md5(coalesce(string_agg(x::text, '|' ORDER BY x::text), '')) FROM \"{t}\" x"),
        )
    return out


async def test_backup_disaster_and_restore_bring_every_table_back(world, tmp_path):
    conn = await asyncpg.connect(asyncpg_dsn())
    try:
        before = await fingerprint(conn)
        assert before["users"][0] >= 4 and before["recipes"][0] >= 3  # há dados de verdade para proteger

        # produção tem uma coluna antiga (auth_id) que o app não usa; o backup a leva junto
        await conn.execute("ALTER TABLE users ADD COLUMN auth_id uuid")
        await conn.execute("UPDATE users SET auth_id = gen_random_uuid() WHERE id = 1")
        done = run_tool("backup", "--out", str(tmp_path))
        assert done.returncode == 0 and "Backup OK" in done.stdout, done.stdout + done.stderr
        folder = next(tmp_path.iterdir())
        assert "auth_id" in (folder / "users.csv").read_text(encoding="utf-8").splitlines()[0]

        # o destino não tem a coluna e perdeu tudo
        await conn.execute("ALTER TABLE users DROP COLUMN auth_id")
        names = ", ".join(f'"{t}"' for t in before)
        await conn.execute(f"TRUNCATE {names} CASCADE")
        assert (await fingerprint(conn))["ingredients"][0] == 0

        # arquivo adulterado é recusado antes de tocar no banco
        csv_file = folder / "ingredients.csv"
        original = csv_file.read_bytes()
        csv_file.write_bytes(original + b"\n999,1,x,kg,1,0,,,,100,,,,\n")
        refused = run_tool("restore", str(folder))
        assert refused.returncode != 0 and "corrompido" in (refused.stdout + refused.stderr)
        assert (await fingerprint(conn))["ingredients"][0] == 0
        csv_file.write_bytes(original)

        restored = run_tool("restore", str(folder))
        assert restored.returncode == 0 and "Restauração OK" in restored.stdout, restored.stdout + restored.stderr
        assert "users.auth_id" in restored.stdout  # avisa o que ignorou
        assert await fingerprint(conn) == before     # linhas e conteúdo idênticos, tabela por tabela

        # sequências ajustadas: um novo registro não colide com os restaurados
        new_id = await conn.fetchval(
            "INSERT INTO ingredients (user_id, name, unit, unit_cost, min_stock, yield_percentage) "
            "VALUES (1, 'novo-pos-restore', 'kg', 1, 0, 100) RETURNING id"
        )
        assert new_id > await conn.fetchval("SELECT max(id) FROM ingredients WHERE name <> 'novo-pos-restore'")
        await conn.execute("DELETE FROM ingredients WHERE name = 'novo-pos-restore'")

        # não sobrescreve dados existentes sem --force; com --force funciona
        assert run_tool("restore", str(folder)).returncode != 0
        forced = run_tool("restore", str(folder), "--force")
        assert forced.returncode == 0 and "Restauração OK" in forced.stdout
        assert await fingerprint(conn) == before
    finally:
        await conn.close()

"""Backup e restauração lógica do banco (um CSV por tabela + manifest com contagens e checksums).

    python scripts/db_backup.py backup  [--out backups]
    python scripts/db_backup.py restore backups/restaurante-AAAAMMDD-HHMMSS [--force]

A conexão vem de DATABASE_URL (ambiente ou backend/.env). O backup lê tudo numa única
transação somente-leitura (foto consistente) e confere o que gravou. A restauração
recusa tabelas que já têm dados, a menos que use --force, e confere as contagens no fim.
Os arquivos contêm dados reais (inclusive hashes de senha): guarde fora do repositório.
"""
import argparse
import asyncio
import csv
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent


async def connect() -> asyncpg.Connection:
    load_dotenv(BACKEND / ".env")
    url = os.getenv("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL não definida (ambiente ou backend/.env)")
    # statement_cache_size=0: compatível com o pooler (pgbouncer) do Supabase
    return await asyncpg.connect(url.replace("postgresql+asyncpg://", "postgresql://"), statement_cache_size=0)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_records(path: Path) -> int:
    with open(path, newline="", encoding="utf-8") as f:
        return max(sum(1 for _ in csv.reader(f)) - 1, 0)


async def ordered_tables(conn: asyncpg.Connection) -> list[str]:
    """Tabelas do schema public, pais antes dos filhos (para a restauração respeitar as chaves)."""
    tables = [r["tablename"] for r in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")]
    deps = await conn.fetch(
        "SELECT conrelid::regclass::text AS child, confrelid::regclass::text AS parent "
        "FROM pg_constraint WHERE contype = 'f' AND connamespace = 'public'::regnamespace"
    )
    parents = {t: set() for t in tables}
    for d in deps:
        child, parent = d["child"].strip('"'), d["parent"].strip('"')
        if child != parent and child in parents and parent in parents:
            parents[child].add(parent)
    ordered: list[str] = []
    while len(ordered) < len(tables):
        ready = sorted(t for t in tables if t not in ordered and parents[t] <= set(ordered))
        if not ready:
            raise RuntimeError("ciclo de chaves estrangeiras entre tabelas")
        ordered.extend(ready)
    return ordered


async def backup(out_root: str) -> None:
    conn = await connect()
    out = Path(out_root) / f"restaurante-{datetime.now():%Y%m%d-%H%M%S}"
    out.mkdir(parents=True)
    manifest = {"created_at": datetime.now().isoformat(timespec="seconds"), "tables": {}}
    try:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            for table in await ordered_tables(conn):
                path = out / f"{table}.csv"
                with open(path, "wb") as f:
                    await conn.copy_from_query(f'SELECT * FROM "{table}" ORDER BY 1', output=f, format="csv", header=True)
                rows = await conn.fetchval(f'SELECT count(*) FROM "{table}"')
                manifest["tables"][table] = {"rows": rows, "sha256": sha256(path)}
    finally:
        await conn.close()

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    bad = [t for t, m in manifest["tables"].items() if csv_records(out / f"{t}.csv") != m["rows"]]
    if bad:
        sys.exit(f"BACKUP INVÁLIDO: contagem divergente em {bad}")
    total = sum(m["rows"] for m in manifest["tables"].values())
    print(f"Backup OK em {out.resolve()}")
    for t, m in manifest["tables"].items():
        print(f"  {t:<28} {m['rows']:>6} linhas")
    print(f"  {'TOTAL':<28} {total:>6} linhas em {len(manifest['tables'])} tabelas")


async def restore(folder: str, force: bool) -> None:
    src = Path(folder)
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    for t, m in manifest["tables"].items():
        if sha256(src / f"{t}.csv") != m["sha256"]:
            sys.exit(f"Arquivo {t}.csv foi alterado ou está corrompido; restauração cancelada")

    conn = await connect()
    try:
        existing = set(await ordered_tables(conn))
        missing = [t for t in manifest["tables"] if t not in existing]
        if missing:
            sys.exit(f"Tabelas ausentes no destino: {missing}. Suba o app uma vez para criar o schema.")
        filled = {t: await conn.fetchval(f'SELECT count(*) FROM "{t}"') for t in manifest["tables"]}
        if any(filled.values()) and not force:
            sys.exit(f"Destino já tem dados ({ {t: n for t, n in filled.items() if n} }). Use --force para sobrescrever.")
        async with conn.transaction():
            if force:
                names = ", ".join(f'"{t}"' for t in manifest["tables"])
                await conn.execute(f"TRUNCATE {names} CASCADE")
            for table in manifest["tables"]:  # já está em ordem pai -> filho
                path = src / f"{table}.csv"
                with open(path, newline="", encoding="utf-8") as f:
                    columns = next(csv.reader(f))
                if manifest["tables"][table]["rows"] == 0:
                    continue
                with open(path, "rb") as f:
                    await conn.copy_to_table(table, source=f, columns=columns, format="csv", header=True)
            for table in manifest["tables"]:
                seq = await conn.fetchval("SELECT pg_get_serial_sequence($1, 'id')", f'"{table}"')
                if seq:
                    await conn.execute(
                        f"SELECT setval('{seq}', COALESCE((SELECT max(id) FROM \"{table}\"), 1), "
                        f"(SELECT max(id) IS NOT NULL FROM \"{table}\"))"
                    )
            for table, m in manifest["tables"].items():
                got = await conn.fetchval(f'SELECT count(*) FROM "{table}"')
                if got != m["rows"]:
                    raise RuntimeError(f"{table}: restaurou {got} linhas, esperado {m['rows']}")
    finally:
        await conn.close()
    print(f"Restauração OK: {sum(m['rows'] for m in manifest['tables'].values())} linhas em {len(manifest['tables'])} tabelas")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--out", default=str(BACKEND.parent / "backups"))
    r = sub.add_parser("restore")
    r.add_argument("folder")
    r.add_argument("--force", action="store_true")
    args = parser.parse_args()
    asyncio.run(backup(args.out) if args.cmd == "backup" else restore(args.folder, args.force))


if __name__ == "__main__":
    main()

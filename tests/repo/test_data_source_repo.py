import os
import tempfile


def test_data_source_repository_read(monkeypatch):
    db_fd, db_path = tempfile.mkstemp(prefix="dsrepo_", suffix=".db")
    os.close(db_fd)
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")

    from app.infrastructure.repositories.data_source_repository import DataSourceRepository
    import sqlalchemy as sa

    repo = DataSourceRepository()
    # create table for sqlite and seed
    repo._md.create_all(repo._engine, tables=[repo._t])  # type: ignore[attr-defined]
    with repo._engine.begin() as conn:  # type: ignore[attr-defined]
        conn.execute(sa.insert(repo._t).values({  # type: ignore[attr-defined]
            "id": "ds1", "name": "Local", "display_name": "Local DS", "source_type": "sql", "is_active": True
        }))
        conn.execute(sa.insert(repo._t).values({
            "id": "ds2", "name": "Inactive", "display_name": "Inactive DS", "source_type": "sql", "is_active": False
        }))

    active = run(repo.list_active())
    assert any(d["id"] == "ds1" for d in active)
    assert all(d["id"] != "ds2" for d in active)

    got = run(repo.get("ds1"))
    assert got and got["name"] == "Local"


def run(coro):
    import asyncio
    return asyncio.get_event_loop().run_until_complete(coro)


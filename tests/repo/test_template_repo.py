import os
import tempfile

import pytest


def test_template_repository_crud(monkeypatch):
    # use sqlite file to persist across threads
    db_fd, db_path = tempfile.mkstemp(prefix="tmplrepo_", suffix=".db")
    os.close(db_fd)
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")

    from app.infrastructure.repositories.template_repository import TemplateRepository

    repo = TemplateRepository()
    # create table for sqlite (expected to exist in production)
    repo._md.create_all(repo._engine, tables=[repo._t])  # type: ignore[attr-defined]

    tid = "t1"
    # create
    created_id = asyncio_run(repo.create({
        "id": tid,
        "name": "Demo",
        "template_type": "docx",
        "file_path": "templates/demo.docx",
        "is_active": True,
    })))
    assert created_id == tid

    # get
    got = asyncio_run(repo.get(tid))
    assert got is not None and got["name"] == "Demo"

    # list
    lst = asyncio_run(repo.list(limit=10))
    assert isinstance(lst, list) and len(lst) >= 1

    # update
    upd = asyncio_run(repo.update(tid, {"description": "ok"}))
    assert upd == 1

    # delete
    deleted = asyncio_run(repo.delete(tid))
    assert deleted == 1


def asyncio_run(coro):
    import asyncio
    return asyncio.get_event_loop().run_until_complete(coro)

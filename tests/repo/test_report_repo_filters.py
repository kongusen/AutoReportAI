import os
import tempfile
import time


def run(coro):
    import asyncio
    return asyncio.get_event_loop().run_until_complete(coro)


def test_report_repository_filters_and_sort(monkeypatch):
    db_fd, db_path = tempfile.mkstemp(prefix="reportr_", suffix=".db")
    os.close(db_fd)
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")

    from app.infrastructure.repositories.report_repository import ReportRepository
    import sqlalchemy as sa

    repo = ReportRepository()
    # create tables for sqlite
    repo._md.create_all(repo._engine, tables=[repo.t_instances, repo.t_artifacts])  # type: ignore[attr-defined]

    now = time.time()
    # Seed instances
    def seed(job_id, tpl, name, status, created_at):
        with repo._engine.begin() as conn:  # type: ignore[attr-defined]
            conn.execute(sa.insert(repo.t_instances).values(  # type: ignore[attr-defined]
                job_id=job_id,
                template_id=tpl,
                name=name,
                status=status,
                created_at=created_at,
            ))

    seed("job-A", "tpl-1", "Alpha report", "completed", now - 100)
    seed("job-B", "tpl-1", "Beta report", "queued", now - 50)
    seed("job-C", "tpl-2", "Gamma report", "failed", now - 10)

    # q filter by name
    items = run(repo.list(limit=10, offset=0, q="Alpha"))
    assert any(it["job_id"] == "job-A" for it in items) and len(items) >= 1

    # template filter
    items = run(repo.list(limit=10, offset=0, template_id="tpl-1"))
    assert all(it["template_id"] == "tpl-1" for it in items)

    # status filter
    items = run(repo.list(limit=10, offset=0, status="failed"))
    assert len(items) == 1 and items[0]["job_id"] == "job-C"

    # since filter excludes older ones
    since = now - 30
    items = run(repo.list(limit=10, offset=0, since=since))
    ids = {it["job_id"] for it in items}
    assert ids == {"job-B", "job-C"}

    # sort by created_at asc
    items = run(repo.list(limit=10, offset=0, sort_by="created_at", order="asc"))
    assert [it["job_id"] for it in items][:2] == ["job-A", "job-B"]


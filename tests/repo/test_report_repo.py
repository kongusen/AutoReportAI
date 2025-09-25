import os
import tempfile
import time


def test_report_repository_basic(monkeypatch):
    db_fd, db_path = tempfile.mkstemp(prefix="reportr_", suffix=".db")
    os.close(db_fd)
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")

    from app.infrastructure.repositories.report_repository import ReportRepository
    import sqlalchemy as sa

    repo = ReportRepository()
    # create tables for sqlite
    repo._md.create_all(repo._engine, tables=[repo.t_instances, repo.t_artifacts])  # type: ignore[attr-defined]

    # Create instance
    job_id = "job-1"
    run(repo.create_instance(job_id, "tpl-1", "report-tpl-1", status="queued"))
    items = run(repo.list_recent(limit=5))
    assert any(it["job_id"] == job_id for it in items)

    # Complete
    run(repo.set_completed(job_id))
    items = run(repo.list_recent(limit=5))
    one = [it for it in items if it["job_id"] == job_id][0]
    assert one["status"] == "completed"

    # Insert artifact directly
    with repo._engine.begin() as conn:  # type: ignore[attr-defined]
        conn.execute(sa.insert(repo.t_artifacts).values(  # type: ignore[attr-defined]
            id="a1", job_id=job_id, path=f"reports/{job_id}/report.txt", type="text", content_type="text/plain", size=10, created_at=time.time()
        ))
    arts = run(repo.list_artifacts(job_id))
    assert len(arts) == 1 and arts[0]["path"].endswith("report.txt")


def run(coro):
    import asyncio
    return asyncio.get_event_loop().run_until_complete(coro)


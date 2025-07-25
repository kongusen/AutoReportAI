from typing import List

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.report_history import ReportHistory
from app.models.task import Task
from app.schemas.report_history import ReportHistoryCreate


# Note: ReportHistory is not updatable via API, so we don't need a schema for update.
class CRUDReportHistory(CRUDBase[ReportHistory, ReportHistoryCreate, None]):
    def get_by_task_id(self, db: Session, *, task_id: int) -> List[ReportHistory]:
        """Get all report history entries for a specific task."""
        return (
            db.query(self.model)
            .filter(ReportHistory.task_id == task_id)
            .order_by(ReportHistory.generated_at.desc())
            .all()
        )

    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[ReportHistory]:
        """Get report history entries for tasks owned by a specific user."""
        return (
            db.query(self.model)
            .join(Task)
            .filter(Task.owner_id == owner_id)
            .order_by(ReportHistory.generated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count(self, db: Session) -> int:
        """Get total count of report history entries."""
        return db.query(self.model).count()

    def get_recent(self, db: Session, *, limit: int = 10) -> List[ReportHistory]:
        """Get recent report history entries."""
        return (
            db.query(self.model)
            .order_by(ReportHistory.generated_at.desc())
            .limit(limit)
            .all()
        )


report_history = CRUDReportHistory(ReportHistory)

from app.crud.base import CRUDBase
from app.models.report_history import ReportHistory
from app.schemas.report_history import ReportHistoryCreate

# Note: ReportHistory is not updatable via API, so we don't need a schema for update.
class CRUDReportHistory(CRUDBase[ReportHistory, ReportHistoryCreate, None]):
    pass


report_history = CRUDReportHistory(ReportHistory) 
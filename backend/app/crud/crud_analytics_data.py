from app.crud.base import CRUDBase
from app.models.analytics_data import AnalyticsData
from app.schemas.analytics_data import AnalyticsDataCreate, AnalyticsDataUpdate


class CRUDAnalyticsData(CRUDBase[AnalyticsData, AnalyticsDataCreate, AnalyticsDataUpdate]):
    pass


analytics_data = CRUDAnalyticsData(AnalyticsData) 
from app.crud.base import CRUDBase
from app.models.data_source import DataSource
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate

class CRUDDataSource(CRUDBase[DataSource, DataSourceCreate, DataSourceUpdate]):
    pass

data_source = CRUDDataSource(DataSource) 
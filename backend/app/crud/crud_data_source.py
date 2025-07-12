from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.data_source import DataSource
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate


class CRUDDataSource(CRUDBase[DataSource, DataSourceCreate, DataSourceUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> DataSource:
        return db.query(DataSource).filter(DataSource.name == name).first()


data_source = CRUDDataSource(DataSource)

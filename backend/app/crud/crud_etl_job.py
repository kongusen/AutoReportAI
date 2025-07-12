from app.crud.base import CRUDBase
from app.models.etl_job import ETLJob
from app.schemas.etl_job import ETLJobCreate, ETLJobUpdate


class CRUDETLJob(CRUDBase[ETLJob, ETLJobCreate, ETLJobUpdate]):
    pass


etl_job = CRUDETLJob(ETLJob)

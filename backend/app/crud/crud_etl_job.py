from app.crud.base import CRUDBase
from app.models.etl_job import ETLJob
from app.schemas.etl_job import ETLJobCreate, ETLJobUpdate


class CRUDETLJob(CRUDBase[ETLJob, ETLJobCreate, ETLJobUpdate]):
    def create_with_user(self, db, *, obj_in: ETLJobCreate, user_id):
        obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
        obj_data['user_id'] = user_id
        db_obj = ETLJob(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


etl_job = CRUDETLJob(ETLJob)

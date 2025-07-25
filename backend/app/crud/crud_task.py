from typing import List

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):
    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return (
            db.query(self.model)
            .filter(self.model.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_active(self, db: Session) -> int:
        """Get count of active tasks."""
        return db.query(self.model).filter(self.model.status == "active").count()

    def count_completed(self, db: Session) -> int:
        """Get count of completed tasks."""
        return db.query(self.model).filter(self.model.status == "completed").count()

    def create_with_owner(self, db: Session, *, obj_in: TaskCreate, owner_id) -> Task:
        obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
        obj_data['owner_id'] = owner_id
        db_obj = Task(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


task = CRUDTask(Task)

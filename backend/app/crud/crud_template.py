from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateUpdate


class CRUDTemplate:
    def get(self, db: Session, id: str) -> Optional[Template]:
        """根据ID获取模板"""
        return db.query(Template).filter(Template.id == id).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[int] = None,
        include_public: bool = True,
    ) -> List[Template]:
        """获取模板列表"""
        query = db.query(Template)

        if user_id:
            if include_public:
                query = query.filter(
                    and_(Template.user_id == user_id, Template.is_active == True)
                )
            else:
                query = query.filter(
                    and_(
                        Template.user_id == user_id,
                        Template.is_public == False,
                        Template.is_active == True,
                    )
                )
        else:
            query = query.filter(
                and_(Template.is_public == True, Template.is_active == True)
            )

        return query.offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TemplateCreate, user_id: int) -> Template:
        """创建模板"""
        db_obj = Template(
            name=obj_in.name,
            description=obj_in.description,
            template_type=obj_in.template_type,
            content=obj_in.content,
            original_filename=obj_in.original_filename,
            file_size=obj_in.file_size,
            is_public=obj_in.is_public,
            is_active=obj_in.is_active,
            user_id=user_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_with_user(self, db: Session, *, obj_in: TemplateCreate, user_id) -> Template:
        return self.create(db, obj_in=obj_in, user_id=user_id)

    def update(self, db: Session, db_obj: Template, obj_in: TemplateUpdate) -> Template:
        """更新模板"""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: str) -> Template:
        """删除模板（软删除）"""
        db_obj = db.query(Template).filter(Template.id == id).first()
        if db_obj:
            db_obj.is_active = False
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def get_by_user(self, db: Session, user_id: int) -> List[Template]:
        """获取用户的所有模板"""
        return (
            db.query(Template)
            .filter(and_(Template.user_id == user_id, Template.is_active == True))
            .all()
        )


template = CRUDTemplate()

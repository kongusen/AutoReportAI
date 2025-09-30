from typing import List, Optional
from uuid import UUID

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
    
    def create_with_owner(self, db: Session, *, obj_in: TemplateCreate, owner_id) -> Template:
        return self.create(db, obj_in=obj_in, user_id=owner_id)
    
    def get_user_template(self, db: Session, *, template_id: str, user_id) -> Template:
        """获取用户的特定模板"""
        return db.query(Template).filter(
            Template.id == template_id,
            Template.user_id == user_id,
            Template.is_active == True
        ).first()

    def update(self, db: Session, db_obj: Template, obj_in) -> Template:
        """更新模板"""
        if hasattr(obj_in, 'model_dump'):
            # Pydantic model
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            # 字典
            update_data = obj_in
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: str) -> Template:
        """删除模板（硬删除，会级联删除相关占位符）"""
        try:
            db_obj = db.query(Template).filter(Template.id == id).first()
            if db_obj:
                # 检查是否有关联的任务，如果有则不允许删除
                from app.models.task import Task
                related_tasks = db.query(Task).filter(Task.template_id == id).all()
                if related_tasks:
                    task_names = [task.name for task in related_tasks[:3]]  # 最多显示3个任务名
                    if len(related_tasks) > 3:
                        task_names.append(f"等{len(related_tasks)}个任务")
                    raise ValueError(f"无法删除模板：存在关联的任务 ({', '.join(task_names)})。请先删除或重新分配相关任务。")

                # 删除关联的占位符值，避免外键约束问题
                from app.models.template_placeholder import TemplatePlaceholder, PlaceholderValue

                # 获取所有相关的占位符ID
                placeholder_ids = db.query(TemplatePlaceholder.id).filter(
                    TemplatePlaceholder.template_id == id
                ).all()

                # 删除所有占位符值
                for (placeholder_id,) in placeholder_ids:
                    db.query(PlaceholderValue).filter(
                        PlaceholderValue.placeholder_id == placeholder_id
                    ).delete()

                # 删除所有占位符
                db.query(TemplatePlaceholder).filter(
                    TemplatePlaceholder.template_id == id
                ).delete()

                # 最后删除模板
                db.delete(db_obj)
                db.commit()
            return db_obj
        except Exception as e:
            db.rollback()
            raise e
    
    def soft_remove(self, db: Session, id: str) -> Template:
        """软删除模板（仅标记为非活跃）"""
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
    
    def get_count(self, db: Session) -> int:
        """获取所有模板总数"""
        return db.query(Template).count()
    
    def get_count_by_user(self, db: Session, user_id: UUID) -> int:
        """获取用户模板总数"""
        return db.query(Template).filter(Template.user_id == user_id).count()

    def get_templates_with_pagination(
        self, 
        db: Session, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None
    ) -> tuple[List[Template], int]:
        """获取用户模板列表（带分页和搜索）"""
        query = db.query(Template).filter(
            Template.user_id == user_id,
            Template.is_active == True
        )
        
        if search:
            query = query.filter(
                Template.name.contains(search) | 
                Template.description.contains(search)
            )
        
        total = query.count()
        templates = query.offset(skip).limit(limit).all()
        return templates, total

    def get_by_id_and_user(self, db: Session, *, id: str, user_id: UUID) -> Optional[Template]:
        """根据ID和用户ID获取模板"""
        return db.query(Template).filter(
            Template.id == id,
            Template.user_id == user_id,
            Template.is_active == True
        ).first()


crud_template = CRUDTemplate()

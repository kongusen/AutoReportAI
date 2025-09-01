from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Any, List
from uuid import UUID
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app import crud, schemas
from app.core.architecture import ApiResponse

router = APIRouter()

@router.get("/", response_model=ApiResponse)
async def read_report_history(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
) -> ApiResponse:
    """获取报告历史记录"""
    user_id = current_user.id
    
    # 检查是否为超级用户
    from app.crud.crud_user import crud_user
    if crud_user.is_superuser(current_user):
        history = crud.report_history.get_multi(db, skip=skip, limit=limit)
        total = crud.report_history.count(db)
    else:
        history = crud.report_history.get_multi_by_owner(
            db=db, owner_id=user_id, skip=skip, limit=limit
        )
        total = crud.report_history.get_count_by_user(db, user_id)
    
    return ApiResponse(
        success=True,
        data={
            "items": [schemas.ReportHistory.model_validate(h) for h in history],
            "total": total,
            "page": skip // limit + 1 if limit > 0 else 1,
            "size": limit,
            "has_next": skip + limit < total,
            "has_prev": skip > 0
        },
        message="获取报告历史记录成功"
    ) 
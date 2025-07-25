from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.core.config import settings
from app.db.session import get_db_session, get_db
from app.models.user import User
from app.core.security import decode_access_token

security = HTTPBearer()
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v2/auth/login")


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    """获取当前认证用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        if not payload or not isinstance(payload, dict):
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    from app.crud.crud_user import user as crud_user
    user = crud_user.get(db, id=user_id)
    print(f"[DEBUG] get_current_user: user.id={getattr(user, 'id', None)}, type={type(getattr(user, 'id', None))}")
    if user is None:
        raise credentials_exception
    # 强制user.id为UUID类型
    from uuid import UUID
    if not isinstance(user.id, UUID):
        try:
            user.id = UUID(str(user.id))
        except Exception:
            raise HTTPException(status_code=500, detail="user.id类型错误，无法转为UUID")
    assert isinstance(user.id, UUID), f"user.id类型错误: {type(user.id)}"
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    return current_user

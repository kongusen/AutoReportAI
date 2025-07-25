from uuid import UUID

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前认证用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        if not payload or not isinstance(payload, dict):
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        try:
            user_id = UUID(user_id)
        except Exception:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    from app.crud.crud_user import user as crud_user
    user = crud_user.get(db, id=user_id)
    if user is None:
        raise credentials_exception
    return user 